"""Exercise both independent pursuers through the real game and skeleton mixers."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'export/game-verification'
URL='http://127.0.0.1:'+os.environ.get('KUCHI_PREVIEW_PORT','8765')+'/'


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    errors,failures=[],[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,chromium_sandbox=False,
            args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1280,'height':800})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:failures.append(r.url))
        page.goto(URL+'?test=1',wait_until='networkidle',timeout=60000)
        page.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
        page.click('#start')
        def step(t):page.evaluate('t=>window.kuchiGame.advance(t)',t)
        assert page.evaluate("window.kuchiGame.actors.map(a=>a.id)")==['glasses','cropped']
        assert page.evaluate("(()=>{const [a,b]=window.kuchiGame.actors;return a.enemy!==b.enemy&&a.controller.mixer!==b.controller.mixer&&a.controller.model!==b.controller.model&&a.controller.clips.size===8&&b.controller.clips.size===8})()")
        assert page.evaluate('window.kuchiGame.actors.every(a=>window.kuchiGame.nav.free(a.enemy.position,.4)&&a.enemy.patrol.every(p=>window.kuchiGame.nav.free(p,.4)))')
        page.evaluate("()=>{const g=window.kuchiGame;g.teleport(0,10);g.actors.forEach((a,i)=>{a.enemy.position={x:i?3:-3,z:4};a.enemy.angle=0;a.enemy.grace=0;a.enemy.transition('idle',50)})}")
        step(.1);assert page.evaluate("window.kuchiGame.actors.every(a=>a.enemy.state==='alert')")
        step(1.4);assert page.evaluate("window.kuchiGame.actors.every(a=>a.enemy.state==='chase'&&a.controller.state==='chase')")
        before=page.evaluate('window.kuchiGame.actors.map(a=>({...a.enemy.position}))')
        step(.5)
        after=page.evaluate('window.kuchiGame.actors.map(a=>({...a.enemy.position}))')
        assert all(a['z']>b['z']+.5 for a,b in zip(after,before))
        page.screenshot(path=str(OUTPUT/'two-pursuers-chase.png'))
        # Bell reaches both; an edible offering stops only its nearest recipient.
        page.evaluate("window.kuchiGame.progress.inventory.kagura_bell=1")
        page.keyboard.press('r');assert page.evaluate("window.kuchiGame.actors.every(a=>a.enemy.state==='ritual'&&a.controller.state==='ritual')")
        page.keyboard.press('p')
        frozen=page.evaluate('window.kuchiGame.snapshot().enemies');step(2)
        assert page.evaluate('window.kuchiGame.snapshot().enemies')==frozen
        page.click('#resume')
        page.evaluate("()=>{const g=window.kuchiGame;g.actors.forEach((a,i)=>{a.enemy.position={x:i?12:0,z:i?-20:4};a.enemy.grace=999;a.enemy.transition('idle',50)});g.progress.inventory.onigiri=2;}")
        page.keyboard.press('4');page.keyboard.press('g');step(1.3)
        assert page.evaluate("window.kuchiGame.actors[0].enemy.state==='feed'&&window.kuchiGame.actors[1].enemy.state!=='feed'")
        # Swap which pursuer is nearby and verify independent item ownership.
        page.evaluate("()=>{const g=window.kuchiGame;g.actors[0].enemy.position={x:12,z:-20};g.actors[1].enemy.position={x:0,z:4};}")
        page.keyboard.press('g');step(1.3)
        assert page.evaluate("window.kuchiGame.actors[1].enemy.state==='feed'&&window.kuchiGame.actors[1].controller.state==='feed'")
        assert page.evaluate("window.kuchiGame.actors.every(a=>Math.abs(a.controller.model.getObjectByName('FINGER_L_1_TIP_CTRL').rotation.x)>.2)")
        # The second pursuer can independently capture, and retry resets both.
        page.evaluate("()=>{const g=window.kuchiGame;g.teleport(0,2);const e=g.actors[1].enemy;e.position={x:0,z:1.4};e.angle=0;e.grace=0;e.transition('chase')}")
        step(.1);assert page.evaluate("window.kuchiGame.mode==='dead'")
        page.click('#retry')
        assert page.evaluate("window.kuchiGame.mode==='playing'&&window.kuchiGame.actors.every(a=>a.enemy.state==='idle'&&a.enemy.grace>0)")
        assert not errors,errors;assert not failures,failures
        report={'status':'passed','characters':['glasses','cropped'],'independent_rigs':'passed','independent_patrol_and_chase':'passed','nearest_food_recipient':'passed','animated_finger_grip':'passed','bell_reaches_both':'passed','pause_and_retry':'passed','second_pursuer_capture':'passed','javascript_errors':errors,'failed_requests':failures}
        (OUTPUT/'pursuers_validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2));browser.close()


if __name__=='__main__':main()
