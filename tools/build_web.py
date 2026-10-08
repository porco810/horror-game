"""Build a portable static site from the pinned local runtime and game assets."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'
OUTPUT=ROOT/'dist'
RUNTIME=[
    'LICENSE','package.json','build/three.module.js','build/three.core.js',
    'examples/jsm/controls/OrbitControls.js','examples/jsm/loaders/GLTFLoader.js',
    'examples/jsm/utils/BufferGeometryUtils.js',
]

def main():
    if not (WEB/'assets/models/kuchikagura.glb').is_file():
        raise SystemExit('Generate the character first: npm run build')
    for name in RUNTIME:
        if not (ROOT/'node_modules/three'/name).is_file():
            raise SystemExit('Install the pinned runtime first: npm ci')
    OUTPUT.mkdir(exist_ok=True)
    shutil.copytree(WEB,OUTPUT,dirs_exist_ok=True)
    for name in RUNTIME:
        target=OUTPUT/'vendor/three'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'node_modules/three'/name,target)
    shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.txt',OUTPUT/'THIRD_PARTY_NOTICES.txt')
    files={str(p.relative_to(OUTPUT)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(OUTPUT.rglob('*')) if p.is_file() and p.name!='FILE_HASHES.json'}
    (OUTPUT/'FILE_HASHES.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')
    print(f'Static game ready: {OUTPUT} ({len(files)} files)')

if __name__=='__main__':main()
