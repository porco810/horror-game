"""Check the generated static site from a subdirectory, including local imports."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'export/game-verification'
PORT=int(os.environ.get('KUCHI_STATIC_PORT','8766'))

def main():
    errors,failures=[],[]
    OUTPUT.mkdir(parents=True,exist_ok=True)
    if not (ROOT/'dist/index.html').is_file():raise SystemExit('Run npm run build:web first.')
    with tempfile.TemporaryDirectory(prefix='kuchi-static-',dir='/tmp') as directory:
        root=Path(directory)
        shutil.copytree(ROOT/'dist',root/'site')
        with (root/'server.log').open('w') as log:
            server=subprocess.Popen(['python3','-m','http.server',str(PORT),'--bind','127.0.0.1','--directory',str(root)],stdout=log,stderr=log)
            try:
                url=f'http://127.0.0.1:{PORT}/site/'
                deadline=time.monotonic()+5
                while True:
                    if server.poll() is not None:raise RuntimeError('Static server failed to start; choose an unused KUCHI_STATIC_PORT.')
                    try:
                        with urllib.request.urlopen(url,timeout=.5) as response:assert response.status==200
                        break
                    except OSError:
                        if time.monotonic()>deadline:raise
                        time.sleep(.05)
                with urllib.request.urlopen(url+'assets/models/kuchikagura.glb') as response:
                    assert hashlib.sha256(response.read()).digest()==hashlib.sha256((ROOT/'web/assets/models/kuchikagura.glb').read_bytes()).digest()
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,chromium_sandbox=False,args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
                    page=browser.new_page(viewport={'width':1024,'height':768})
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.on('requestfailed',lambda r:failures.append({'url':r.url,'failure':r.failure}))
                    page.goto(url+'?test=1',wait_until='networkidle',timeout=60000)
                    page.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
                    page.click('#start');page.evaluate("window.kuchiGame.teleport(1,31);window.kuchiGame.aim('note_village')")
                    page.keyboard.press('e');assert page.locator('#journal-screen').is_visible()
                    assert page.evaluate("window.kuchiGame.progress.notes.includes('village')")
                    # Restarting must schedule fresh footfalls, even after the
                    # previous game's elapsed clock was much larger.
                    page.click('#close-journal');page.keyboard.down('w');page.evaluate('window.kuchiGame.advance(8)');page.keyboard.up('w')
                    page.keyboard.press('p');page.click('#return-title');page.click('#start')
                    page.evaluate("()=>{const a=window.kuchiGame.audio,original=a.tone.bind(a);window.footfalls=0;a.tone=(...args)=>{if(args[3]==='triangle')window.footfalls++;return original(...args)};}")
                    page.keyboard.down('w');page.evaluate('window.kuchiGame.advance(.3)');page.keyboard.up('w')
                    assert page.evaluate('window.footfalls')>0
                    assert not errors,errors;assert not failures,failures
                    result={'status':'passed','subdirectory':'/site/','exact_glb':'passed','local_imports':'passed','first_interaction':'passed','audio_after_new_game':'passed','javascript_errors':errors,'failed_requests':failures}
                    (OUTPUT/'static_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
                    browser.close()
            finally:
                server.terminate()
                try:server.wait(timeout=5)
                except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
