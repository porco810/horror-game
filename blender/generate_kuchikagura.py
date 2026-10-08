"""Original skinned folklore pursuer. Metres, Z-up, facing -Y in Blender."""
import json
import math
import traceback
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
EXPORT, MODELS = ROOT / 'export', ROOT / 'web/assets/models'
ERROR = ROOT / 'build_python_error.txt'
FPS = 30
CLIPS = {'idle': 3.6, 'walk': 1.2, 'alert': 2.4, 'chase': .8,
         'search': 4.8, 'lament': 7.2, 'feed': 5.2, 'ritual': 5.6}
LOOPS = {'idle', 'walk', 'chase', 'search', 'ritual'}
PARTS, MATERIALS = [], {}
TILES = {'cloth': 0, 'red': 1, 'skin': 2, 'hair': 3, 'rope': 4, 'moss': 5, 'paper': 6, 'metal': 7}

def log(text):
    print('[KUCHI_KAGURA] ' + str(text), flush=True)

def make_atlas():
    colors = [(.61,.59,.51),(.32,.105,.086),(.57,.54,.48),(.027,.033,.030),
              (.43,.34,.20),(.125,.19,.091),(.72,.70,.60),(.43,.30,.10)]
    pixels = np.ones((1024,1024,4), dtype=np.float32)
    rng = np.random.default_rng(810)
    yy,xx = np.mgrid[0:512,0:256]
    for i,color in enumerate(colors):
        noise = rng.normal(0,.017,(512,256))
        weave = .012*np.sin(xx*2.9)+.011*np.cos(yy*2.3)
        stain = .10*np.maximum(0,np.sin(xx*.061+np.sin(yy*.019))*np.cos(yy*.041))
        variation = 1+noise+weave-stain-.10*np.exp(-yy/65)
        if i==3: variation += .12*np.sin(xx*.9+yy*.02)
        if i==5: variation += .15*np.sin(xx*.12)*np.sin(yy*.15)
        row,col=divmod(i,4)
        pixels[row*512:(row+1)*512,col*256:(col+1)*256,:3] = np.clip(np.array(color)[None,None,:]*variation[:,:,None],.001,1)
    image=bpy.data.images.new('Kuchi_Atlas_1K',width=1024,height=1024,alpha=False)
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw=str(EXPORT/'textures/kuchikagura_atlas_1k.png')
    image.file_format='PNG'
    image.save()
    image.pack()
    for name in TILES:
        mat=bpy.data.materials.new('Kuchi_'+name)
        mat.use_nodes=True
        shader=mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value=.52 if name=='metal' else (.66 if name=='hair' else .92)
        shader.inputs['Metallic'].default_value=.55 if name=='metal' else 0
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
        mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
        MATERIALS[name]=mat

def finish(obj,material,bone,weights=None):
    obj.data.materials.clear();obj.data.materials.append(MATERIALS[material])
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
    col,row=TILES[material]%4,TILES[material]//4
    for item in uv.data:
        u,v=item.uv
        item.uv=(col/4+.008+float(u)*.234,row/2+.008+float(v)*.484)
    groups={}
    for vertex in obj.data.vertices:
        for name,weight in (weights(vertex.co) if weights else {bone:1.0}).items():
            if weight>1e-6:
                if name not in groups: groups[name]=obj.vertex_groups.new(name=name)
                groups[name].add([vertex.index],float(weight),'REPLACE')
    for face in obj.data.polygons: face.use_smooth=True
    PARTS.append(obj)
    return obj

def mesh(name,verts,faces,material,bone,uv=None,weights=None):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    layer=data.uv_layers.new(name='UVMap')
    if uv:
        for loop in data.loops: layer.data[loop.index].uv=uv[loop.vertex_index]
    return finish(obj,material,bone,weights)

def ellipsoid(name,center,scale,material,bone,subdivisions=3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions,radius=1,location=center)
    obj=bpy.context.object;obj.name=name;obj.scale=scale
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return finish(obj,material,bone)

def block(name,center,dims,material,bone,bevel=0,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center,rotation=rotation)
    obj=bpy.context.object;obj.name=name;obj.dimensions=dims
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    if bevel:
        mod=obj.modifiers.new('Worn_edges','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(obj,material,bone)

def tube(name,points,radii,material,bone,sides=12,weights=None):
    verts,faces,uv=[],[],[]
    for j,(point,radius) in enumerate(zip(points,radii)):
        point=Vector(point)
        tangent=(Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])).normalized()
        ref=Vector((0,1,0)) if abs(tangent.y)<.9 else Vector((1,0,0))
        right=tangent.cross(ref).normalized();up=tangent.cross(right).normalized()
        rx,ry=(radius,radius) if isinstance(radius,(int,float)) else radius
        for i in range(sides+1):
            a=math.tau*i/sides
            verts.append(tuple(point+right*math.cos(a)*rx+up*math.sin(a)*ry))
            uv.append((i/sides,j/(len(points)-1)))
    stride=sides+1
    for j in range(len(points)-1):
        for i in range(sides):
            a=j*stride+i;faces.append((a,a+1,a+stride+1,a+stride))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(points)-1)*stride+i for i in range(sides)))
    return mesh(name,verts,faces,material,bone,uv,weights)

def curve(name,controls,radius,material,bone,samples=20,sides=8,weights=None):
    controls=[Vector(p) for p in controls];points=[]
    for n in range(samples+1):
        v=n/samples*(len(controls)-1);i=min(int(v),len(controls)-2);t=v-i
        a,b,c,d=controls[max(0,i-1)],controls[i],controls[i+1],controls[min(i+2,len(controls)-1)]
        points.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3)))
    return tube(name,points,[radius*(1-.78*(i/samples)**2) for i in range(samples+1)],material,bone,sides,weights)

def create_rig():
    root=bpy.data.objects.new('KUCHI_KAGURA',None);bpy.context.collection.objects.link(root)
    for key,value in {'character_name':'朽ち神楽 / Kuchikagura','game_role':'original_folkloric_pursuer',
                      'units':'metres','forward_axis':'+Z in glTF; -Y in Blender','reaction_states':','.join(CLIPS),
                      'memory_items':'photograph,hairpin,child_sandals','food_items':'onigiri,dango'}.items(): root[key]=value
    data=bpy.data.armatures.new('Kuchi_Skeleton');rig=bpy.data.objects.new('Kuchi_Rig',data)
    bpy.context.collection.objects.link(rig);rig.parent=root;rig.show_in_front=True
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,head,tail,parent=None):
        b=data.edit_bones.new(name);b.head=head;b.tail=tail
        if parent: b.parent=data.edit_bones[parent]
    bone('ROOT_CTRL',(0,0,0),(0,0,.18))
    bone('HIPS_CTRL',(0,0,.97),(0,0,1.09),'ROOT_CTRL')
    bone('TORSO_CTRL',(0,0,1.05),(0,0,1.48),'HIPS_CTRL')
    bone('NECK_CTRL',(0,0,1.48),(0,0,1.69),'TORSO_CTRL')
    bone('HEAD_CTRL',(0,0,1.69),(0,0,1.93),'NECK_CTRL')
    for s,sign in [('L',-1),('R',1)]:
        bone(f'ARM_{s}_CTRL',(sign*.235,0,1.47),(sign*.33,0,1.04),'TORSO_CTRL')
        bone(f'ELBOW_{s}_CTRL',(sign*.33,0,1.04),(sign*.385,0,.63),f'ARM_{s}_CTRL')
        bone(f'HAND_{s}_CTRL',(sign*.385,0,.63),(sign*.40,0,.50),f'ELBOW_{s}_CTRL')
        bone(f'THIGH_{s}_CTRL',(sign*.13,0,.97),(sign*.13,0,.52),'HIPS_CTRL')
        bone(f'SHIN_{s}_CTRL',(sign*.13,0,.52),(sign*.13,0,.13),f'THIGH_{s}_CTRL')
        bone(f'FOOT_{s}_CTRL',(sign*.13,0,.13),(sign*.13,-.16,.075),f'SHIN_{s}_CTRL')
    for name,x,hand in [('MEMORY',.40,'R'),('FOOD',-.40,'L'),('BELL',.40,'R')]:
        bone(name+'_PROP_CTRL',(x,-.018,.54),(x,-.018,.69),'HAND_'+hand+'_CTRL')
    bpy.ops.object.mode_set(mode='OBJECT')
    for b in rig.pose.bones: b.rotation_mode='XYZ'
    return root,rig

def blossom(center,bone,radius=.032):
    x,y,z=center
    for j in range(5):
        a=j*math.tau/5
        ellipsoid('Pale_invasive_petal',(x+radius*.62*math.cos(a),y-.006,z+radius*.62*math.sin(a)),
                  (radius*.45,.008,radius*.53),'paper',bone,1)
    ellipsoid('Flower_seed',(x,y-.014,z),(.009,.007,.009),'rope',bone,1)

def build_body():
    heights=[.91,.99,1.10,1.22,1.34,1.43,1.49];widths=[.24,.21,.18,.19,.235,.255,.205]
    tube('White_ritual_robe',[(0,0,z) for z in heights],[(w,.125+.013*math.sin(i)) for i,w in enumerate(widths)],'cloth','TORSO_CTRL',40)
    ellipsoid('Neck',(0,0,1.62),(.064,.062,.13),'skin','NECK_CTRL',2)
    block('Collar_left',(-.05,-.135,1.38),(.054,.02,.30),'paper','TORSO_CTRL',.008,(0,-.33,0))
    block('Collar_right',(.05,-.14,1.38),(.054,.02,.30),'cloth','TORSO_CTRL',.008,(0,.33,0))
    for row in range(3):
        pts=[(.222*math.cos(i*math.tau/40),.148*math.sin(i*math.tau/40),1.01+row*.019) for i in range(41)]
        tube(f'Waist_straw_{row}',pts,[.012]*len(pts),'rope','TORSO_CTRL',8)
    for sign in [-1,1]:
        curve('Straw_knot',[(0,-.17,1.03),(sign*.11,-.19,1.08),(sign*.12,-.20,1.01),(sign*.03,-.17,1.04)],.013,'rope','TORSO_CTRL',16)
    for i in range(6):
        x=(i-2.5)*.055;verts=[]
        for xx,y,z in [(x,-.153,1.0),(x+.015,-.16,.95),(x-.008,-.18,.89),(x+.012,-.175,.82)]:
            verts.extend([(xx-.016,y,z),(xx+.016,y,z)])
        mesh(f'Folded_shide_{i}',verts,[(0,1,3,2),(2,3,5,4),(4,5,7,6)],'paper','TORSO_CTRL',[(n%2,n//2/3) for n in range(8)])
    for s,sign in [('L',-1),('R',1)]:
        arm,elbow,hand=f'ARM_{s}_CTRL',f'ELBOW_{s}_CTRL',f'HAND_{s}_CTRL'
        tube(f'Hanging_sleeve_{s}',[(sign*(.235+.095*t),0,1.465-.43*t) for t in [0,.15,.35,.55,.75,.95]],
             [(.095,.090),(.11,.10),(.13,.12),(.16,.135),(.17,.15),(.14,.13)],'cloth',arm,32)
        tube(f'Forearm_{s}',[(sign*.33,0,1.055),(sign*.35,0,.89),(sign*.37,0,.72),(sign*.385,0,.63)],
             [(.052,.045),(.046,.04),(.034,.029),(.027,.024)],'skin',elbow,20)
        ellipsoid(f'Palm_{s}',(sign*.394,-.003,.585),(.041,.027,.071),'skin',hand,2)
        for i,length in enumerate([.087,.105,.10,.073]):
            x=sign*(.394+(i-1.5)*.018)
            curve(f'Finger_{s}_{i}',[(x,-.005,.545),(x+sign*.008,-.013,.505),(x+sign*.013,-.019,.545-length)],.010,'skin',hand,6,8)
        curve(f'Thumb_{s}',[(sign*.36,-.009,.603),(sign*.345,-.025,.57),(sign*.35,-.03,.55)],.013,'skin',hand,6,8)
        thigh,shin=f'THIGH_{s}_CTRL',f'SHIN_{s}_CTRL'
        def weights(co,a=thigh,b=shin):
            w=max(0.,min(1.,(co.z-.43)/.20));return {a:w,b:1-w}
        points=[(sign*.13,.015,h) for h in [.16,.24,.38,.52,.66,.8,.94,1.0]]
        radii=[(.125,.14),(.15,.155),(.16,.16),(.156,.16),(.15,.15),(.143,.144),(.137,.132),(.13,.13)]
        obj=tube(f'Hakama_{s}',points,radii,'red',thigh,48,weights)
        for v in obj.data.vertices:
            a=math.atan2(v.co.y-.015,v.co.x-sign*.13)
            v.co.x+=.008*math.cos(a)*math.cos(a*12);v.co.y+=.008*math.sin(a)*math.cos(a*12)
        foot=f'FOOT_{s}_CTRL'
        block(f'Foot_{s}',(sign*.13,-.074,.074),(.115,.225,.08),'hair',foot,.018)
        block(f'Straw_sandal_{s}',(sign*.13,-.074,.029),(.14,.25,.025),'rope',foot,.01)
        curve(f'Sandal_strap_{s}',[(sign*.13-.06,-.04,.085),(sign*.13,-.1,.124),(sign*.13+.06,-.04,.085)],.009,'rope',foot,8)

def build_head():
    head='HEAD_CTRL'
    ellipsoid('Face',(0,-.015,1.787),(.148,.134,.191),'skin',head,3)
    ellipsoid('Jaw',(0,-.049,1.70),(.106,.090,.08),'skin',head,2)
    ellipsoid('Nose',(.003,-.145,1.778),(.017,.025,.048),'skin',head,2)
    for x in [-.054,.054]: ellipsoid('Recessed_eye',(x,-.137,1.811),(.024,.007,.008),'hair',head,2)
    curve('Closed_mouth',[(-.028,-.134,1.712),(0,-.142,1.709),(.028,-.134,1.712)],.003,'red',head,8,6)
    ellipsoid('Black_hair_cap',(0,.011,1.855),(.16,.143,.148),'hair',head,3)
    def hair_weights(co):
        weight=max(.12,min(1.,(co.z-1.35)/.42))
        return {'HEAD_CTRL':weight,'TORSO_CTRL':1-weight}
    verts,uv,faces=[],[],[]
    for row in range(19):
        t=row/18
        for col in range(33):
            a=col/32*math.pi
            verts.append((math.cos(a)*(.16+.045*t),.018+math.sin(a)*(.135+.035*t),1.92-.82*t+.018*math.sin(a*5)*t))
            uv.append((col/32,1-t))
    for row in range(18):
        for col in range(32):
            n=row*33+col;faces.append((n,n+33,n+34,n+1))
    mesh('Long_hair_curtain',verts,faces,'hair',head,uv,hair_weights)
    for i in range(30):
        a=i/30*math.tau;x,y=math.cos(a)*.144,math.sin(a)*.125;front=y<-.052
        end=1.51+.07*math.sin(i*1.8) if front else 1.03+.10*math.sin(i*1.7)
        if front:
            x+=.04 if x>0 else -.04
            if abs(x)<.095: x=math.copysign(.105,x)
        pts=[(x*.80,y*.7,1.965),(x*1.07,y*1.08,1.82),(x*1.15+.018*math.sin(i),y*1.15,1.62),
             (x*1.3+.03*math.sin(i*1.3),y*1.22+.025,end)]
        curve(f'Long_black_hair_{i:02}',pts,.026 if not front else .019,'hair',head,22,10,hair_weights)
    curve('Reed_hairpin',[(-.19,.02,1.88),(-.10,-.004,1.90),(.08,-.016,1.94)],.008,'rope',head,10,8)
    blossom((-.155,-.055,1.90),head,.055)

def build_overgrowth():
    vines=[[(-.19,-.145,1.47),(-.235,-.143,1.32),(-.14,-.14,1.13),(-.20,-.15,.96)],
           [(.20,-.14,1.47),(.18,-.16,1.32),(.09,-.16,1.18),(.16,-.17,1.0)],
           [(-.12,.13,1.43),(.05,.14,1.29),(.16,.13,1.12),(.11,.14,.96)]]
    for i,pts in enumerate(vines):
        curve(f'Robe_invasion_{i}',pts,.010,'moss','TORSO_CTRL',24)
        for p in pts[:3]: blossom((p[0],p[1]-.008,p[2]),'TORSO_CTRL',.033+i*.003)
    for s,sign in [('L',-1),('R',1)]:
        arm=f'ARM_{s}_CTRL'
        curve(f'Sleeve_vine_{s}',[(sign*.28,-.10,1.40),(sign*.40,-.12,1.30),(sign*.45,-.10,1.17),(sign*.36,-.15,1.08)],.010,'moss',arm,18)
        blossom((sign*.4,-.135,1.30),arm,.036)

def build_props():
    block('Memory_photograph',(.40,-.035,.56),(.12,.009,.15),'paper','MEMORY_PROP_CTRL',.002)
    block('Faded_photo_field',(.40,-.042,.57),(.099,.004,.104),'hair','MEMORY_PROP_CTRL')
    ellipsoid('Photo_silhouette',(.40,-.046,.58),(.021,.003,.035),'cloth','MEMORY_PROP_CTRL',1)
    verts=[(-.46,y,.51) for y in [-.052,.018]]+[(-.34,y,.51) for y in [-.052,.018]]+[(-.40,y,.63) for y in [-.052,.018]]
    mesh('Onigiri',verts,[(0,2,4),(1,5,3),(0,1,3,2),(2,3,5,4),(4,5,1,0)],'paper','FOOD_PROP_CTRL',[(0,0),(0,1),(1,0),(1,1),(.5,1),(.5,0)])
    block('Nori',(-.4,-.055,.535),(.049,.006,.047),'hair','FOOD_PROP_CTRL',.002)
    tube('Bell_handle',[(.40,-.02,.50),(.40,-.02,.68)],[.009,.009],'rope','BELL_PROP_CTRL',8)
    for i in range(3): ellipsoid('Kagura_bell',(.40+(i-1)*.038,-.025,.67+(i%2)*.025),(.024,.022,.024),'metal','BELL_PROP_CTRL',2)
    curve('Bell_ribbon',[(.40,-.02,.64),(.46,-.024,.58),(.43,-.04,.48),(.49,-.035,.42)],.008,'red','BELL_PROP_CTRL',12,6)

def smoothstep(a,b,value):
    x=min(1.,max(0.,(value-a)/(b-a)));return x*x*(3-2*x)

def set_pose(rig,state,t,duration):
    bones=rig.pose.bones
    for b in bones: b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
    for n in ['MEMORY_PROP_CTRL','FOOD_PROP_CTRL','BELL_PROP_CTRL']: bones[n].scale=(.001,)*3
    def rot(name,x=0,y=0,z=0): bones[name].rotation_euler=(x,y,z)
    def crouch(amount):
        bones['ROOT_CTRL'].location.y-=.84-(.45*math.cos(1.13*amount)+.39*math.cos(.72*amount))
        for s in ['L','R']:
            rot(f'THIGH_{s}_CTRL',-1.13*amount);rot(f'SHIN_{s}_CTRL',1.85*amount);rot(f'FOOT_{s}_CTRL',-.72*amount)
    cycle=t/duration*math.tau;sway=math.sin(cycle)
    rot('NECK_CTRL',-.045,0,.17);rot('HEAD_CTRL',.035,.018*sway,-.035)
    rot('ARM_L_CTRL',-.035,0,.025);rot('ARM_R_CTRL',.03,0,-.025)
    if state=='idle':
        bones['ROOT_CTRL'].location.y=.005*math.sin(2*cycle)
        rot('TORSO_CTRL',.018*sway,0,.015*sway);rot('HEAD_CTRL',.035+.02*sway,.035*sway,-.035)
    elif state in {'walk','chase'}:
        run=state=='chase';stride=.58 if run else .30
        bones['ROOT_CTRL'].location.y=(.027 if run else .010)*(1-math.cos(2*cycle))
        rot('TORSO_CTRL',.22 if run else .045,.025*sway,.025*sway);rot('NECK_CTRL',-.12 if run else -.025,0,.12)
        for s,offset in [('L',0),('R',math.pi)]:
            wave=math.sin(cycle+offset);thigh=stride*wave;knee=max(0.,-wave)*(.90 if run else .48)
            rot(f'THIGH_{s}_CTRL',thigh);rot(f'SHIN_{s}_CTRL',knee);rot(f'FOOT_{s}_CTRL',-thigh*.45-knee*.5)
            rot(f'ARM_{s}_CTRL',-(.52 if run else .22)*wave);rot(f'ELBOW_{s}_CTRL',-.47 if run else -.12)
    elif state=='alert':
        e=smoothstep(0,.55,t);rot('HEAD_CTRL',-.07*e,.19*math.sin(t*1.6)*e,.29*e)
        rot('TORSO_CTRL',-.025*e,.08*e);rot('ARM_L_CTRL',-.18*e,0,.09*e);rot('ARM_R_CTRL',-.12*e,0,-.09*e)
    elif state=='search':
        rot('HIPS_CTRL',0,.16*sway);rot('TORSO_CTRL',.08,.20*sway);rot('HEAD_CTRL',.06,.34*math.sin(cycle+.3),.13)
        rot('ARM_R_CTRL',-.58-.08*math.sin(cycle),0,-.12);rot('ELBOW_R_CTRL',-.24);rot('ARM_L_CTRL',-.13,0,.11)
    elif state=='lament':
        pickup=smoothstep(.15,1.2,t);recover=smoothstep(1.7,2.7,t);grief=smoothstep(3.1,4.5,t);end=1-smoothstep(duration-.8,duration,t)
        crouch((.80*pickup*(1-recover)+.95*grief)*end)
        rot('TORSO_CTRL',(.58*pickup*(1-recover)+.25*recover+.28*grief)*end+.012*math.sin(t*21)*grief*end)
        rot('HEAD_CTRL',(.32*pickup+.30*grief)*end,0,.12*grief*end)
        rot('ARM_R_CTRL',(-.10*pickup-1.05*recover)*end);rot('ELBOW_R_CTRL',-1.65*recover*end)
        rot('ARM_L_CTRL',(-.98*recover-.47*grief)*end);rot('ELBOW_L_CTRL',-1.75*recover*end)
        scale=max(.001,smoothstep(1.15,1.30,t)*end);bones['MEMORY_PROP_CTRL'].scale=(scale,)*3
    elif state=='feed':
        pickup=smoothstep(.1,.65,t);recover=smoothstep(.75,1.35,t);end=1-smoothstep(duration-.7,duration,t)
        crouch(.8*pickup*(1-recover)*end);bite=math.sin(t*10)*.065*recover*end
        rot('TORSO_CTRL',(.58*pickup*(1-recover)+.16*recover)*end);rot('HEAD_CTRL',.26*recover*end+bite)
        rot('ARM_L_CTRL',-1.02*recover*end)
        rot('ELBOW_L_CTRL',-(2.1+.28*max(0.,math.sin(t*10)))*recover*end)
        rot('ARM_R_CTRL',-1.1*recover*end);rot('ELBOW_R_CTRL',-1.75*recover*end-bite)
        scale=max(.001,smoothstep(.65,.75,t)*(1-smoothstep(3.9,4.4,t)));bones['FOOD_PROP_CTRL'].scale=(scale,)*3
    elif state=='ritual':
        rot('HIPS_CTRL',0,.12*sway,.03*math.sin(2*cycle));rot('TORSO_CTRL',.06*math.sin(2*cycle),-.10*sway,.06*sway)
        rot('NECK_CTRL',-.07,.10*sway,.22);rot('HEAD_CTRL',-.06,.12*math.cos(cycle),.16*math.sin(2*cycle))
        rot('ARM_L_CTRL',-.35+.18*math.sin(cycle),0,.94-.12*math.cos(cycle))
        rot('ARM_R_CTRL',-.35-.18*math.sin(cycle),0,-.94+.12*math.cos(cycle))
        rot('ELBOW_L_CTRL',-.55+.18*math.sin(2*cycle));rot('ELBOW_R_CTRL',-.55-.18*math.sin(2*cycle))
        bones['ROOT_CTRL'].location.y=.012*(1-math.cos(2*cycle));bones['BELL_PROP_CTRL'].scale=(1,)*3

def build_actions(rig):
    rig.animation_data_create()
    for name,duration in CLIPS.items():
        action=bpy.data.actions.new(name);action.use_fake_user=True;action['loop']=name in LOOPS;action['in_place']=True
        rig.animation_data.action=action;last=round(duration*FPS)
        for frame in range(last+1):
            set_pose(rig,name,frame/FPS,duration)
            for b in rig.pose.bones:
                b.keyframe_insert(data_path='rotation_euler',frame=frame,group=b.name)
                if b.name=='ROOT_CTRL': b.keyframe_insert(data_path='location',frame=frame,group=b.name)
                if b.name.endswith('PROP_CTRL'): b.keyframe_insert(data_path='scale',frame=frame,group=b.name)
        # Blender 4.3 uses legacy actions; 4.4+ also has layered action slots.
        if hasattr(action,'fcurves'):
            fcurves=action.fcurves
        else:
            fcurves=[f for layer in action.layers for strip in layer.strips for bag in strip.channelbags for f in bag.fcurves]
        for fcurve in fcurves:
            for key in fcurve.keyframe_points: key.interpolation='LINEAR'
        log(f'animation {name}: {duration:.2f}s / {last+1} frames')
    rig.animation_data.action=None;set_pose(rig,'idle',0,CLIPS['idle'])

def authoring_scene():
    collection=bpy.data.collections.new('AUTHORING_ONLY');bpy.context.scene.collection.children.link(collection)
    def move(obj):
        for c in list(obj.users_collection): c.objects.unlink(obj)
        collection.objects.link(obj)
    bpy.ops.mesh.primitive_plane_add(size=6);ground=bpy.context.object;ground.name='AUTHORING_GROUND';move(ground)
    for name,position,power in [('Key',(2,-3,4),450),('Rim',(-2,1,3),600)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=3
        light=bpy.data.objects.new(name,data);collection.objects.link(light);light.location=position
        light.rotation_euler=(Vector((0,0,1.1))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add(location=(2.5,-4,2.1));camera=bpy.context.object;move(camera)
    camera.rotation_euler=(Vector((0,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera=camera;bpy.context.scene.render.engine='BLENDER_EEVEE_NEXT'
    bpy.context.scene.render.resolution_x=900;bpy.context.scene.render.resolution_y=1100

def build():
    for p in [EXPORT,MODELS,EXPORT/'textures']: p.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    make_atlas();root,rig=create_rig();build_body();build_head();build_overgrowth();build_props()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in PARTS: obj.select_set(True)
    bpy.context.view_layer.objects.active=PARTS[0];bpy.ops.object.join()
    body=bpy.context.object;body.name='Kuchi_Skinned_Mesh'
    mod=body.modifiers.new('Kuchi_Deform','ARMATURE');mod.object=rig
    body.data.calc_loop_triangles();triangles=len(body.data.loop_triangles)
    assert 20000<=triangles<=40000, f'Triangle budget exceeded: {triangles}'
    build_actions(rig);scene=bpy.context.scene;scene.render.fps=FPS
    scene.frame_start=0;scene.frame_end=max(round(d*FPS) for d in CLIPS.values());authoring_scene();scene.frame_set(0)
    rig.animation_data.action=bpy.data.actions['idle']
    bpy.ops.wm.save_as_mainfile(filepath=str(EXPORT/'kuchikagura_game.blend'))
    rig.animation_data.action=None;set_pose(rig,'idle',0,CLIPS['idle']);bpy.ops.object.select_all(action='DESELECT')
    for obj in [root,rig,body]: obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(MODELS/'kuchikagura.glb'),export_format='GLB',use_selection=True,
        export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,
        export_frame_range=False,export_extras=True,export_yup=True,export_normals=True,
        export_materials='EXPORT',export_cameras=False,export_lights=False)
    report={'character':'朽ち神楽','blender_version':bpy.app.version_string,'triangles':triangles,
            'skinned_meshes':1,'bones':len(rig.data.bones),'texture':{'size':[1024,1024],'count':1,'packed':True},
            'clips':[{'name':n,'duration_seconds':d,'loop':n in LOOPS,'in_place':True} for n,d in CLIPS.items()],
            'glb_bytes':(MODELS/'kuchikagura.glb').stat().st_size,'forward_gltf':'+Z','units':'metres',
            'player_model':False,'pov_arms_asset':'separate pov_arms.glb, reserved for later'}
    (EXPORT/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (EXPORT/'build_report.txt').write_text(f'KUCHI KAGURA\ntriangles={triangles}\nbones={len(rig.data.bones)}\ntexture=1x1024\nanimations={",".join(CLIPS)}\n',encoding='utf-8')
    log(report);log('DONE')

if __name__=='__main__':
    try:
        ERROR.unlink(missing_ok=True);build()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8');print(ERROR.read_text(encoding='utf-8'),flush=True)
        raise
