"""Build two independently skinned pursuers inspired by the supplied portrait.

The original Kuchikagura asset stays available. Reference faces and uniform
details are authored as geometry; no source photograph or personal name is used
as a texture. The unseen back and footwear are an original reconstruction.
"""
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_kuchikagura as api
from reference_body import build_body
from reference_head import build_head

ROOT = Path(__file__).resolve().parents[1]
EXPORT, MODELS = ROOT / 'export', ROOT / 'web/assets/models'
PROFILES = [
    dict(id='glasses', display_name='眼鏡の追跡者', shoulder=.275, width=1., height=1.87,finger_rig=True),
    dict(id='cropped', display_name='短髪の追跡者', shoulder=.30, width=1.10, height=1.78,finger_rig=True),
]
TILES = {name:i for i,name in enumerate([
    'cloth','trousers','skin','hair','moss','paper','metal','lips',
    'eye_white','iris','skin_shadow','rope','stitch','red','blue','glass'])}
ALIASES = {'button':'metal', 'black':'hair', 'pupil':'hair'}


def make_atlas(profile):
    colors = [(.86,.85,.78),(.045,.059,.075),(.72,.52,.39),(.025,.024,.022),
              (.065,.32,.17),(.68,.71,.61),(.63,.49,.22),(.48,.24,.20),
              (.86,.84,.77),(.105,.074,.049),(.42,.27,.20),(.36,.28,.19),
              (.57,.56,.50),(.48,.13,.10),(.12,.24,.36),(.52,.58,.58)]
    pixels=np.ones((2048,2048,4),dtype=np.float32)
    yy,xx=np.mgrid[0:512,0:512]
    rng=np.random.default_rng(810 if profile['id']=='glasses' else 811)
    for name,index in TILES.items():
        # Correlated grain compresses efficiently without losing cloth/skin
        # variation; independent noise at every 2K texel wastes mobile bandwidth.
        grain=rng.normal(0,.006 if name in {'skin','lips','eye_white'} else .015,(64,64))
        grain=np.repeat(np.repeat(grain,8,axis=0),8,axis=1)
        noise=sum(np.roll(grain,n,axis=0) for n in range(-3,4))/7
        noise=sum(np.roll(noise,n,axis=1) for n in range(-3,4))/7
        weave=.009*(np.sin(xx*2.6)+np.cos(yy*2.8)) if name in {'cloth','trousers','stitch','moss'} else 0
        grime=.045*np.maximum(0,np.sin(xx*.019+.6)*np.sin(yy*.023)) if name in {'cloth','trousers'} else 0
        pores=-.015*(rng.random((512,512))>.995) if name in {'skin','skin_shadow'} else 0
        variation=np.round((1+noise+weave-grime+pores)*128)/128
        row,col=divmod(index,4)
        pixels[row*512:(row+1)*512,col*512:(col+1)*512,:3]=np.clip(np.array(colors[index])[None,None,:]*variation[:,:,None],.001,1)
    image=bpy.data.images.new('Reference_'+profile['id']+'_Atlas_2K',width=2048,height=2048,alpha=False)
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw=str(EXPORT/'textures'/f"pursuer_{profile['id']}_atlas_2k.png")
    image.file_format='PNG';image.save();image.pack()
    for name in TILES:
        mat=bpy.data.materials.new('Reference_'+name);mat.use_nodes=True
        shader=mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value={'skin':.66,'lips':.48,'eye_white':.24,'iris':.25,'metal':.32,'glass':.28,'hair':.82}.get(name,.86)
        shader.inputs['Metallic'].default_value=.68 if name in {'metal','glass'} else 0
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
        api.MATERIALS[name]=mat
    for alias,name in ALIASES.items():api.MATERIALS[alias]=api.MATERIALS[name]


def finish(obj,material,bone,weights=None):
    tile=TILES[ALIASES.get(material,material)]
    obj.data.materials.clear();obj.data.materials.append(api.MATERIALS[material])
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
    col,row=tile%4,tile//4
    for item in uv.data:
        u,v=item.uv
        item.uv=(col/4+.004+float(u)*.242,row/4+.004+float(v)*.242)
    groups={}
    for vertex in obj.data.vertices:
        distribution=weights(vertex.co) if weights else {bone:1.}
        total=sum(max(0.,w) for w in distribution.values())
        assert total>0, f'Unweighted vertex in {obj.name}'
        for name,value in distribution.items():
            weight=max(0.,value)/total
            if weight>1e-6:
                if name not in groups:groups[name]=obj.vertex_groups.new(name=name)
                groups[name].add([vertex.index],weight,'REPLACE')
    for face in obj.data.polygons:face.use_smooth=True
    api.PARTS.append(obj)
    return obj


def create_rig(profile):
    root=bpy.data.objects.new('PURSUER_'+profile['id'].upper(),None)
    bpy.context.collection.objects.link(root)
    for key,value in {'character_name':profile['display_name'],'character_id':profile['id'],
                      'game_role':'reference_inspired_pursuer','units':'metres',
                      'forward_axis':'+Z in glTF; -Y in Blender',
                      'reaction_states':','.join(api.CLIPS),'reference_style':'portrait-inspired original reconstruction'}.items():root[key]=value
    data=bpy.data.armatures.new('Reference_Skeleton');rig=bpy.data.objects.new('Reference_Rig',data)
    bpy.context.collection.objects.link(rig);rig.parent=root;rig.show_in_front=True
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,head,tail,parent=None):
        b=data.edit_bones.new(name);b.head=head;b.tail=tail
        if parent:b.parent=data.edit_bones[parent]
    bone('ROOT_CTRL',(0,0,0),(0,0,.18))
    bone('HIPS_CTRL',(0,0,.97),(0,0,1.09),'ROOT_CTRL')
    bone('TORSO_CTRL',(0,0,1.05),(0,0,1.48),'HIPS_CTRL')
    bone('NECK_CTRL',(0,0,1.48),(0,0,1.69),'TORSO_CTRL')
    bone('HEAD_CTRL',(0,0,1.69),(0,0,1.93),'NECK_CTRL')
    shoulder=profile['shoulder']
    for side,sign in [('L',-1),('R',1)]:
        bone(f'ARM_{side}_CTRL',(sign*shoulder,0,1.48),(sign*(shoulder+.10),0,1.16),'TORSO_CTRL')
        bone(f'ELBOW_{side}_CTRL',(sign*(shoulder+.10),0,1.16),(sign*(shoulder+.13),0,.85),f'ARM_{side}_CTRL')
        bone(f'HAND_{side}_CTRL',(sign*(shoulder+.13),0,.85),(sign*(shoulder+.14),0,.72),f'ELBOW_{side}_CTRL')
        wx=sign*(shoulder+.13)
        for finger,(offset,length) in enumerate([(-.025,.079),(-.008,.094),(.010,.088),(.027,.070)]):
            fx=wx+sign*(.008+offset);z0=.750-abs(offset)*.12
            proximal=f'FINGER_{side}_{finger}_CTRL';distal=f'FINGER_{side}_{finger}_TIP_CTRL'
            middle=(fx+sign*.003,-.015,z0-length*.40)
            bone(proximal,(fx,-.007,z0),middle,f'HAND_{side}_CTRL')
            bone(distal,middle,(fx+sign*.006,-.041,z0-length-.003),proximal)
        tx=wx-sign*.025;middle=(tx-sign*.024,-.029,.773)
        bone(f'THUMB_{side}_CTRL',(tx,-.012,.810),middle,f'HAND_{side}_CTRL')
        bone(f'THUMB_{side}_TIP_CTRL',middle,(tx-sign*.018,-.047,.741),f'THUMB_{side}_CTRL')
        bone(f'THIGH_{side}_CTRL',(sign*.13,0,.97),(sign*.13,0,.52),'HIPS_CTRL')
        bone(f'SHIN_{side}_CTRL',(sign*.13,0,.52),(sign*.13,0,.13),f'THIGH_{side}_CTRL')
        bone(f'FOOT_{side}_CTRL',(sign*.13,0,.13),(sign*.13,-.16,.075),f'SHIN_{side}_CTRL')
    for name,side,sign in [('MEMORY','R',1),('FOOD','L',-1),('BELL','R',1)]:
        x=sign*(shoulder+.14)
        bone(name+'_PROP_CTRL',(x,-.035,.76),(x,-.035,.91),'HAND_'+side+'_CTRL')
    bpy.ops.object.mode_set(mode='OBJECT')
    for b in rig.pose.bones:b.rotation_mode='XYZ'
    return root,rig


def build_props(profile):
    x=profile['shoulder']+.14
    api.block('Memory_photograph',(x,-.043,.785),(.12,.009,.15),'paper','MEMORY_PROP_CTRL',.002)
    api.block('Anonymous_photo_field',(x,-.050,.794),(.099,.004,.104),'trousers','MEMORY_PROP_CTRL')
    api.ellipsoid('Photo_silhouette',(x,-.054,.805),(.021,.003,.035),'cloth','MEMORY_PROP_CTRL',1)
    verts=[(-x-.06,y,.75) for y in [-.062,.008]]+[(-x+.06,y,.75) for y in [-.062,.008]]+[(-x,y,.87) for y in [-.062,.008]]
    api.mesh('Onigiri',verts,[(0,2,4),(1,5,3),(0,1,3,2),(2,3,5,4),(4,5,1,0)],'eye_white','FOOD_PROP_CTRL',[(0,0),(0,1),(1,0),(1,1),(.5,1),(.5,0)])
    api.block('Nori',(-x,-.065,.778),(.049,.006,.047),'hair','FOOD_PROP_CTRL',.002)
    api.tube('Bell_handle',[(x,-.03,.735),(x,-.03,.915)],[.009,.009],'rope','BELL_PROP_CTRL',8)
    for i in range(3):api.ellipsoid('Kagura_bell',(x+(i-1)*.038,-.035,.905+(i%2)*.025),(.024,.022,.024),'metal','BELL_PROP_CTRL',2)
    api.curve('Bell_ribbon',[(x,-.03,.875),(x+.06,-.034,.815),(x+.03,-.05,.715),(x+.09,-.045,.655)],.008,'red','BELL_PROP_CTRL',12,6)


def set_pose(rig,state,t,duration):
    api.set_pose(rig,state,t,duration)
    adjust_pose(rig,state,t,duration)


def adjust_pose(rig,state,t,duration):
    bones=rig.pose.bones;cycle=t/duration*math.tau
    bones['ROOT_CTRL'].location*=rig.get('height_scale',1.)
    # The forward-leaning pose echoes the portrait without affecting navigation.
    if state in {'idle','walk','search'}:
        bones['TORSO_CTRL'].rotation_euler.x+=.09
        bones['NECK_CTRL'].rotation_euler.z*=.45
    if state=='chase':
        bones['TORSO_CTRL'].rotation_euler.x+=.055
        bones['HEAD_CTRL'].rotation_euler.x-=.05
    if state=='alert':bones['HEAD_CTRL'].rotation_euler.z*=.6
    if state=='ritual':bones['HEAD_CTRL'].rotation_euler.z+=.025*math.sin(cycle*2)
    grip=.12 if state in {'idle','walk','search'} else .30 if state=='chase' else .08
    if state=='lament':grip=.32*api.smoothstep(1.7,2.7,t)*(1-api.smoothstep(duration-.8,duration,t))
    if state=='feed':grip=.74*api.smoothstep(.75,1.35,t)*(1-api.smoothstep(duration-.7,duration,t))
    for side in ['L','R']:
        hand_grip=.55 if state=='ritual' and side=='R' else grip
        for finger in range(4):
            bones[f'FINGER_{side}_{finger}_CTRL'].rotation_euler.x=-hand_grip*.72
            bones[f'FINGER_{side}_{finger}_TIP_CTRL'].rotation_euler.x=-hand_grip*1.05
        bones[f'THUMB_{side}_CTRL'].rotation_euler.x=-hand_grip*.35
        bones[f'THUMB_{side}_TIP_CTRL'].rotation_euler.x=-hand_grip*.6
    if state=='feed':
        amount=api.smoothstep(.75,1.35,t)*(1-api.smoothstep(duration-.7,duration,t))
        if amount>.001:
            head=pose_matrix(rig,'HEAD_CTRL');scale=rig.get('height_scale',1.)
            # Use a position in rig space; scale the mouth offset, not the root.
            target=head@Vector((-.015*scale,-.02*scale,.185*scale))
            solve_hand(rig,'L','FOOD_PROP_CTRL',target,amount)
            support=head@Vector((.06*scale,-.07*scale,.18*scale))
            solve_hand(rig,'R','MEMORY_PROP_CTRL',support,amount)


def pose_matrix(rig,name):
    """Forward kinematics without evaluating/overwriting the action being baked."""
    b=rig.pose.bones[name];rest=rig.data.bones[name].matrix_local
    relative=rig.data.bones[b.parent.name].matrix_local.inverted()@rest if b.parent else rest
    local=relative@Matrix.LocRotScale(b.location,b.rotation_euler.to_quaternion(),b.scale)
    return pose_matrix(rig,b.parent.name)@local if b.parent else local


def solve_hand(rig,side,prop,target,influence):
    """Bake a small numerical IK solve to Euler keys; GLB needs no constraints."""
    arm=rig.pose.bones[f'ARM_{side}_CTRL'];elbow=rig.pose.bones[f'ELBOW_{side}_CTRL'];hand=rig.pose.bones[f'HAND_{side}_CTRL']
    variables=[(arm,0),(arm,1),(arm,2),(elbow,0),(hand,0)]
    original=[bone.rotation_euler[index] for bone,index in variables]
    parent=pose_matrix(rig,arm.parent.name)
    rest=[rig.data.bones[b.name].matrix_local for b in [arm,elbow,hand]]
    relative_arm=rig.data.bones[arm.parent.name].matrix_local.inverted()@rest[0]
    relative_elbow=rest[0].inverted()@rest[1]
    relative_hand=rest[1].inverted()@rest[2]
    anchor=(rest[2].inverted()@rig.data.bones[prop].matrix_local).translation
    def error():
        matrix=parent@relative_arm@arm.rotation_euler.to_matrix().to_4x4()@relative_elbow@elbow.rotation_euler.to_matrix().to_4x4()@relative_hand@hand.rotation_euler.to_matrix().to_4x4()
        return (matrix@anchor-target).length_squared
    best=error()
    for step in [.30,.15,.07,.035,.015]:
        for _ in range(3):
            improved=False
            for bone,index in variables:
                value=bone.rotation_euler[index];chosen=value
                for sign in [-1,1]:
                    bone.rotation_euler[index]=value+step*sign;score=error()
                    if score<best:best=score;chosen=value+step*sign;improved=True
                bone.rotation_euler[index]=chosen
            if not improved:break
    for (bone,index),start in zip(variables,original):
        bone.rotation_euler[index]=start+(bone.rotation_euler[index]-start)*influence


def build_actions(rig):
    original=api.set_pose
    try:
        # Core action export retains the exact game durations and loop seams.
        api.set_pose=lambda *args:set_pose_using(original,*args)
        api.build_actions(rig)
    finally:api.set_pose=original


def set_pose_using(original,rig,state,t,duration):
    original(rig,state,t,duration)
    adjust_pose(rig,state,t,duration)


def build_one(profile):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    api.PARTS.clear();api.MATERIALS.clear();api.finish=finish
    make_atlas(profile);root,rig=create_rig(profile)
    build_body(api,profile);build_head(api,profile);build_props(profile)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in api.PARTS:obj.select_set(True)
    bpy.context.view_layer.objects.active=api.PARTS[0];bpy.ops.object.join()
    body=bpy.context.object;body.name='Reference_'+profile['id']+'_Skinned_Mesh'
    modifier=body.modifiers.new('Reference_Deform','ARMATURE');modifier.object=rig
    body.data.calc_loop_triangles();triangles=len(body.data.loop_triangles)
    assert 20000<=triangles<=40000,f'{profile["id"]}: triangle budget exceeded ({triangles})'
    # Bake metres into geometry and rest bones. The skinned mesh stays a scene
    # root, so consumers need no special handling for scaled parent transforms.
    factor=profile['height']/1.97
    for vertex in body.data.vertices:vertex.co*=factor
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:bone.head*=factor;bone.tail*=factor
    bpy.ops.object.mode_set(mode='OBJECT');rig['height_scale']=factor
    build_actions(rig)
    scene=bpy.context.scene;scene.render.fps=api.FPS;scene.frame_start=0
    scene.frame_end=max(round(d*api.FPS) for d in api.CLIPS.values())
    api.authoring_scene();scene.frame_set(0);rig.animation_data.action=bpy.data.actions['idle']
    blend=EXPORT/f"pursuer_{profile['id']}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    rig.animation_data.action=None;set_pose(rig,'idle',0,api.CLIPS['idle'])
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [root,rig,body]:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    glb=MODELS/f"pursuer_{profile['id']}.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,
        export_frame_range=False,export_extras=True,export_yup=True,export_normals=True,
        export_materials='EXPORT',export_cameras=False,export_lights=False)
    report={'character':profile['display_name'],'id':profile['id'],'blender_version':bpy.app.version_string,
            'triangles':triangles,'skinned_meshes':1,'bones':len(rig.data.bones),
            'texture':{'size':[2048,2048],'count':1,'packed':True},
            'clips':[{'name':n,'duration_seconds':d,'loop':n in api.LOOPS,'in_place':True} for n,d in api.CLIPS.items()],
            'glb_bytes':glb.stat().st_size,'forward_gltf':'+Z','units':'metres',
            'height_target_metres':profile['height'],'player_model':False,
            'pov_arms_asset':'separate pov_arms.glb, reserved for later',
            'reference':'user-supplied portrait; unseen surfaces reconstructed; no personal labels'}
    (EXPORT/f"pursuer_{profile['id']}_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    api.log(report)
    return report


def main():
    for p in [EXPORT,MODELS,EXPORT/'textures']:p.mkdir(parents=True,exist_ok=True)
    reports=[build_one(profile) for profile in PROFILES]
    (EXPORT/'reference_build_report.json').write_text(json.dumps({'characters':reports},ensure_ascii=False,indent=2)+'\n')
    api.log('REFERENCE PURSUERS DONE')


if __name__=='__main__':
    error=ROOT/'reference_build_python_error.txt'
    try:
        error.unlink(missing_ok=True);main()
    except Exception:
        error.write_text(traceback.format_exc());print(error.read_text(),flush=True);raise
