"""Preserve the finished project and minimal offline runtime as a verified ZIP."""
from pathlib import Path
import hashlib
import json
import zipfile

from build_web import RUNTIME

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT.parent/'artifacts/KUCHI_KAGURA_GAME_V1.zip'
PREFIX='KUCHI_KAGURA_GAME_V1'

def main():
    files=[]
    for name in ['README.md','README_FIRST.txt','GAME_DESIGN.md','CHARACTER_SPEC.md',
                 'THIRD_PARTY_NOTICES.txt','PLAY.bat','PREVIEW_ONLY.bat','BUILD_AND_PREVIEW.bat',
                 'OPEN_IN_BLENDER.bat','package.json','package-lock.json','.gitignore']:
        files.append(ROOT/name)
    files.extend(p for p in (ROOT/'web').rglob('*') if p.is_file())
    files.extend(p for p in (ROOT/'.github').rglob('*') if p.is_file())
    for directory,suffixes in [('blender',{'.py'}),('tools',{'.py','.sh','.cjs'}),('tests',{'.mjs'})]:
        files.extend(p for p in (ROOT/directory).iterdir() if p.is_file() and p.suffix in suffixes)
    for name in ['kuchikagura_game.blend','textures/kuchikagura_atlas_1k.png','build_report.json',
                 'build_report.txt','asset_validation.json','gltf_validation.json',
                 'game-verification/game_validation.json','game-verification/static_validation.json',
                 'verification/browser_validation.json','game-verification/title.png']:
        files.append(ROOT/'export'/name)
    files.extend(ROOT/'node_modules/three'/name for name in RUNTIME)
    files=sorted(set(files))
    if any(not p.is_file() for p in files):raise SystemExit('Complete and validate the game before packaging.')
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    OUTPUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in files:archive.write(p,PREFIX+'/'+str(p.relative_to(ROOT)))
        archive.writestr(PREFIX+'/FILE_HASHES.json',json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        for name,expected in hashes.items():assert hashlib.sha256(archive.read(PREFIX+'/'+name)).hexdigest()==expected
    digest=hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_suffix('.zip.sha256').write_text(digest+'  '+OUTPUT.name+'\n')
    print(json.dumps({'status':'passed','archive':str(OUTPUT),'files':len(files)+1,'bytes':OUTPUT.stat().st_size,'sha256':digest},indent=2))

if __name__=='__main__':main()
