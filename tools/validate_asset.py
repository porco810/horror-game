"""Validate the actual generated binary asset, including animation and skin data."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'idle':3.6,'walk':1.2,'alert':2.4,'chase':.8,'search':4.8,'lament':7.2,'feed':5.2,'ritual':5.6}
LOOPS={'idle','walk','chase','search','ritual'}
ASSETS={
    'kuchikagura':{'model':'kuchikagura','root':'KUCHI_KAGURA','blend':'kuchikagura_game.blend',
                  'report':'build_report.json','size':1024,'bones':20},
    'glasses':{'model':'pursuer_glasses','root':'PURSUER_GLASSES','blend':'pursuer_glasses.blend',
               'report':'pursuer_glasses_report.json','size':2048,'bones':40},
    'cropped':{'model':'pursuer_cropped','root':'PURSUER_CROPPED','blend':'pursuer_cropped.blend',
               'report':'pursuer_cropped_report.json','size':2048,'bones':40},
}

def validate_asset(asset):
    spec=ASSETS[asset]
    data=(ROOT/'web/assets/models'/(spec['model']+'.glb')).read_bytes()
    assert len(data)>=28, 'Truncated GLB'
    magic,version,total=struct.unpack_from('<4sII',data)
    assert (magic,version,total)==(b'glTF',2,len(data)), 'Invalid GLB header'
    length,kind=struct.unpack_from('<II',data,12)
    assert kind==0x4E4F534A and length%4==0
    g=json.loads(data[20:20+length]);offset=20+length
    binary_length,binary_kind=struct.unpack_from('<II',data,offset)
    assert binary_kind==0x004E4942 and binary_length%4==0
    assert offset+8+binary_length==len(data), 'Truncated or extra chunks'
    binary=data[offset+8:]
    assert len(g['buffers'])==1 and 'uri' not in g['buffers'][0], 'External buffer'
    assert 0<=binary_length-g['buffers'][0]['byteLength']<=3, 'Invalid buffer length'
    formats={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}
    widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
    cache={}
    def values(index):
        if index in cache:return cache[index]
        a=g['accessors'][index]
        assert 'sparse' not in a and 'bufferView' in a, 'Unexpected sparse accessor'
        v=g['bufferViews'][a['bufferView']]
        assert v['buffer']==0
        fmt='<'+formats[a['componentType']]*widths[a['type']]
        start=v.get('byteOffset',0)+a.get('byteOffset',0)
        stride=v.get('byteStride',struct.calcsize(fmt))
        assert stride>=struct.calcsize(fmt) and a['count']>0
        end=start+(a['count']-1)*stride+struct.calcsize(fmt)
        assert end<=v.get('byteOffset',0)+v['byteLength']<=len(binary), 'Accessor out of bounds'
        result=[struct.unpack_from(fmt,binary,start+i*stride) for i in range(a['count'])]
        assert all(math.isfinite(x) for row in result for x in row), 'Nonfinite attribute'
        if a.get('normalized'):
            limits={5120:127,5121:255,5122:32767,5123:65535}
            assert a['componentType'] in limits, 'Invalid normalized component'
            result=[tuple(max(-1,x/limits[a['componentType']]) for x in row) for row in result]
        cache[index]=result
        return result
    for index in range(len(g['accessors'])):values(index)
    assert len(g['skins'])==1 and len(g['skins'][0]['joints'])==spec['bones']
    assert len(set(g['skins'][0]['joints']))==spec['bones'], 'Duplicate joints'
    mesh_nodes=[node for node in g['nodes'] if 'mesh' in node]
    assert len(mesh_nodes)==1 and mesh_nodes[0].get('skin')==0, 'Mesh is not skinned'
    assert len(g['meshes'])==1
    triangles=0
    for primitive in g['meshes'][0]['primitives']:
        assert primitive.get('mode',4)==4
        indices=values(primitive['indices'])
        assert len(indices)%3==0
        triangles+=len(indices)//3
        attrs=primitive['attributes']
        assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=attrs.keys()
        vertex_count=len(values(attrs['POSITION']))
        assert all(len(values(index))==vertex_count for index in attrs.values()), 'Attribute count mismatch'
        assert all(0<=row[0]<vertex_count for row in indices), 'Vertex index out of bounds'
        for weights,joints in zip(values(attrs['WEIGHTS_0']),values(attrs['JOINTS_0'])):
            assert abs(sum(weights)-1)<1e-4 and min(weights)>=0, 'Unnormalized skin weights'
            assert all(0<=joint<spec['bones'] for joint in joints), 'Joint index out of bounds'
    assert 20000<=triangles<=40000
    assert len(g['images'])==1 and 'uri' not in g['images'][0], 'Texture must be embedded'
    image=g['bufferViews'][g['images'][0]['bufferView']]
    png=binary[image.get('byteOffset',0):][:image['byteLength']]
    assert png[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack_from('>II',png,16)==(spec['size'],spec['size'])
    clips={a['name']:a for a in g['animations']}
    assert len(clips)==len(g['animations']) and set(clips)==set(EXPECTED)
    for name,animation in clips.items():
        changed=False
        assert animation['channels'], f'No channels: {name}'
        for channel in animation['channels']:
            sampler=animation['samplers'][channel['sampler']]
            times=values(sampler['input']);output=values(sampler['output'])
            assert sampler.get('interpolation','LINEAR')!='CUBICSPLINE', 'Unexpected cubic sampler'
            assert len(times)==len(output), 'Animation sample count mismatch'
            assert abs(times[0][0])<1e-5 and abs(times[-1][0]-EXPECTED[name])<.04
            assert all(times[i][0]<times[i+1][0] for i in range(len(times)-1))
            rotation=channel['target']['path']=='rotation'
            def distance(a,b):
                direct=max(abs(x-y) for x,y in zip(a,b))
                return min(direct,max(abs(x+y) for x,y in zip(a,b))) if rotation else direct
            changed |= any(distance(output[0],row)>1e-4 for row in output[1:])
            if rotation:
                assert all(abs(sum(x*x for x in row)-1)<1e-3 for row in output), 'Unnormalized rotation'
            if name in LOOPS:
                assert distance(output[0],output[-1])<1e-4, f'Loop seam in {name}'
        assert changed, f'Static animation: {name}'
    names={node.get('name') for node in g['nodes']}
    assert 'AUTHORING_GROUND' not in names and spec['root'] in names
    assert not any('pov' in str(name).lower() or 'player' in str(name).lower() for name in names)
    report=json.loads((ROOT/'export'/spec['report']).read_text())
    assert report['triangles']==triangles and report['glb_bytes']==len(data)
    assert report['bones']==spec['bones'] and report['skinned_meshes']==1, 'Report skin mismatch'
    assert report['texture']['size']==[spec['size'],spec['size']]
    assert report['texture']['count']==1 and report['texture']['packed'], 'Report texture mismatch'
    reported_clips={clip['name']:clip for clip in report['clips']}
    assert set(reported_clips)==set(EXPECTED)
    for name,clip in reported_clips.items():
        assert abs(clip['duration_seconds']-EXPECTED[name])<.04
        assert clip['loop']==(name in LOOPS) and clip['in_place'], 'Report animation mismatch'
    blend=(ROOT/'export'/spec['blend']).read_bytes()
    assert blend[:7]==b'BLENDER'
    return {'asset':spec['model'],'status':'passed','triangles':triangles,'glb_bytes':len(data),'bones':spec['bones'],
            'texture':f"one embedded {spec['size']}x{spec['size']} PNG",'animations':list(EXPECTED),
            'loop_seams':'passed','skin_weights':'passed','finite_attributes':'passed',
            'report_consistency':'passed','blend_header':'passed',
            'glb_sha256':hashlib.sha256(data).hexdigest(),'blend_sha256':hashlib.sha256(blend).hexdigest()}

def validate(assets=None):
    selected=list(ASSETS) if assets is None else assets
    results={name:validate_asset(name) for name in selected}
    if 'kuchikagura' in results:
        (ROOT/'export/asset_validation.json').write_text(json.dumps(results['kuchikagura'],indent=2)+'\n')
    references={name:result for name,result in results.items() if name!='kuchikagura'}
    if references:
        result={'status':'passed','assets':references,'both_reference_characters':set(references)=={'glasses','cropped'}}
        (ROOT/'export/reference_asset_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'passed','assets':results},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset',choices=list(ASSETS),nargs='+',help='Inspect selected assets (default: all three)')
    validate(parser.parse_args().asset)
