"""Validate the actual generated binary asset, including animation and skin data."""
import json
import math
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'idle':3.6,'walk':1.2,'alert':2.4,'chase':.8,'search':4.8,'lament':7.2,'feed':5.2,'ritual':5.6}
LOOPS={'idle','walk','chase','search','ritual'}

def validate():
    data=(ROOT/'web/assets/models/kuchikagura.glb').read_bytes()
    magic,version,total=struct.unpack_from('<4sII',data)
    assert (magic,version,total)==(b'glTF',2,len(data)), 'Invalid GLB header'
    length,kind=struct.unpack_from('<II',data,12)
    assert kind==0x4E4F534A
    g=json.loads(data[20:20+length]);offset=20+length
    binary_length,binary_kind=struct.unpack_from('<II',data,offset)
    assert binary_kind==0x004E4942
    binary=data[offset+8:offset+8+binary_length]
    formats={5121:'B',5123:'H',5125:'I',5126:'f'}
    widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
    def values(index):
        a=g['accessors'][index];v=g['bufferViews'][a['bufferView']]
        fmt='<'+formats[a['componentType']]*widths[a['type']]
        start=v.get('byteOffset',0)+a.get('byteOffset',0)
        stride=v.get('byteStride',struct.calcsize(fmt))
        result=[struct.unpack_from(fmt,binary,start+i*stride) for i in range(a['count'])]
        assert all(math.isfinite(x) for row in result for x in row), 'Nonfinite attribute'
        return result
    assert len(g['skins'])==1 and len(g['skins'][0]['joints'])==20
    assert len(g['meshes'])==1
    triangles=0
    for primitive in g['meshes'][0]['primitives']:
        assert primitive.get('mode',4)==4
        triangles+=g['accessors'][primitive['indices']]['count']//3
        attrs=primitive['attributes']
        assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=attrs.keys()
        for row in values(attrs['WEIGHTS_0']):
            assert abs(sum(row)-1)<1e-4 and min(row)>=0
    assert 20000<=triangles<=40000
    assert len(g['images'])==1 and 'uri' not in g['images'][0], 'Texture must be embedded'
    image=g['bufferViews'][g['images'][0]['bufferView']]
    png=binary[image.get('byteOffset',0):][:image['byteLength']]
    assert png[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack_from('>II',png,16)==(1024,1024)
    clips={a['name']:a for a in g['animations']}
    assert set(clips)==set(EXPECTED)
    for name,animation in clips.items():
        changed=False
        for channel in animation['channels']:
            sampler=animation['samplers'][channel['sampler']]
            times=values(sampler['input']);output=values(sampler['output'])
            assert abs(times[0][0])<1e-5 and abs(times[-1][0]-EXPECTED[name])<.04
            assert all(times[i][0]<times[i+1][0] for i in range(len(times)-1))
            changed |= any(max(abs(a-b) for a,b in zip(output[0],row))>1e-4 for row in output[1:])
            if name in LOOPS:
                assert max(abs(a-b) for a,b in zip(output[0],output[-1]))<1e-4, f'Loop seam in {name}'
        assert changed, f'Static animation: {name}'
    names={node.get('name') for node in g['nodes']}
    assert 'AUTHORING_GROUND' not in names and 'KUCHI_KAGURA' in names
    assert not any('pov' in str(name).lower() or 'player' in str(name).lower() for name in names)
    report=json.loads((ROOT/'export/build_report.json').read_text())
    assert report['triangles']==triangles and report['glb_bytes']==len(data)
    blend=(ROOT/'export/kuchikagura_game.blend').read_bytes()
    assert blend[:7]==b'BLENDER'
    result={'status':'passed','triangles':triangles,'glb_bytes':len(data),'bones':20,
            'texture':'one embedded 1024x1024 PNG','animations':list(EXPECTED),'loop_seams':'passed','skin_weights':'passed'}
    (ROOT/'export/asset_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': validate()
