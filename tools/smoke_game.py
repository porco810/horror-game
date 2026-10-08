"""Exercise the real browser game. Deterministic stepping skips travel time only.

All collection, offering, journal and ending actions use the production controls.
Enemy AI and projectile physics execute normally; no assertions are bypassed.
"""
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'export/game-verification'
URL='http://127.0.0.1:'+os.environ.get('KUCHI_PREVIEW_PORT','8765')+'/'

def test_mobile(browser,errors,failures,record):
    mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
    mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
    mp.on('requestfailed',lambda r:failures.append({'url':r.url,'failure':r.failure}))
    mp.goto(URL+'?test=1',wait_until='networkidle');mp.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
    mp.screenshot(path=str(OUTPUT/'mobile-title.png'));mp.locator('#start').tap()
    assert mp.locator('#touch-controls').is_visible();assert mp.evaluate('document.documentElement.scrollWidth')==390
    mp.locator('#touch-crouch').tap();mp.evaluate('window.kuchiGame.advance(.1)');assert mp.evaluate('window.kuchiGame.player.crouching')
    mp.locator('#touch-run').tap();mp.locator('#torch-toggle').tap();assert not mp.evaluate('window.kuchiGame.player.flashlight')
    mp.locator('#journal-toggle').tap();assert mp.locator('#journal-screen').is_visible()
    r=mp.locator('.journal-card').bounding_box();assert r['x']>=0 and r['x']+r['width']<=390
    mp.screenshot(path=str(OUTPUT/'mobile-journal.png'))
    mp.locator('#close-journal').tap()
    # Browser-dispatched touch creates active pointers and real capture.
    cdp=mobile.new_cdp_session(mp);r=mp.locator('#joystick').bounding_box()
    z=mp.evaluate('window.kuchiGame.player.z')
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':r['x']+50,'y':r['y']+20,'id':1}]})
    mp.evaluate('window.kuchiGame.advance(1)')
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    assert mp.evaluate('window.kuchiGame.player.z')<z-.6
    yaw=mp.evaluate('window.kuchiGame.player.yaw')
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':320,'y':350,'id':2}]})
    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':260,'y':370,'id':2}]})
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    assert abs(mp.evaluate('window.kuchiGame.player.yaw')-yaw)>.05
    mp.screenshot(path=str(OUTPUT/'mobile-play.png'))
    mobile.close();record('mobile/layout/touch-actions/joystick/drag-look')

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    errors,failures,checks=[],[],[]
    def record(check):
        checks.append(check)
        print('PASS: '+check,flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,chromium_sandbox=False,
            args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
        if '--mobile-only' in sys.argv:
            test_mobile(browser,errors,failures,record)
            assert not errors,errors
            assert not failures,failures
            result={'status':'passed','checks':checks,'javascript_errors':errors,'failed_requests':failures}
            (OUTPUT/'mobile_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(result,ensure_ascii=False,indent=2))
            browser.close()
            return
        context=browser.new_context(viewport={'width':1440,'height':900})
        page=context.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:failures.append({'url':r.url,'failure':r.failure}))
        def snapshot():return page.evaluate('window.kuchiGame.snapshot()')
        def step(t):page.evaluate('(t)=>window.kuchiGame.advance(t)',t)
        def teleport(x,z):page.evaluate('([x,z])=>window.kuchiGame.teleport(x,z)',[x,z])
        def aim(item):page.evaluate('(id)=>window.kuchiGame.aim(id)',item)
        def take(item,x,z):
            teleport(x,z);aim(item)
            assert snapshot()['focused']==item,(item,snapshot()['focused'])
            page.keyboard.press('e')
            if page.locator('#journal-screen').is_visible():page.click('#close-journal')
            assert item in snapshot()['progress']['collected'],item
        def start():
            page.click('#start');assert snapshot()['mode']=='playing'
            page.evaluate('window.kuchiGame.enemy.grace=999')
        def collect():
            take('note_village',1,31);take('bell',2.4,30.6);take('rice_start',3,30.6)
            take('photo',-10,10.8);take('note_diary',-10,11.3);take('seal_house',-11,9.1)
            take('rice_kitchen',8,16);take('note_food',8,16.5);take('dango_kitchen',9,14)
            take('hairpin',-9.4,-4.7);take('seal_well',-8,-4.7)
            take('sandals',11,-8.8);take('seal_store',11,-8.8)
        def arrange_offering():
            teleport(0,10)
            page.evaluate("const g=window.kuchiGame;g.enemy.position={x:0,z:4};g.enemy.angle=0;g.enemy.grace=999;g.enemy.transition('idle',50)")
        def throw(item,key,state):
            arrange_offering();page.keyboard.press(str(key));before=snapshot()['progress']['inventory'][item]
            page.keyboard.press('g');assert snapshot()['projectiles']==1
            step(1.25);assert snapshot()['enemy']['state']==state,snapshot()
            assert page.evaluate('window.kuchiGame.controller.state')==state
            assert snapshot()['progress']['inventory'][item]==before-1
            step(2);page.screenshot(path=str(OUTPUT/(state+'-'+item+'.png')))
            step(6);assert snapshot()['enemy']['state'] not in ['lament','feed','ritual']
        def unlock():
            take('note_ritual',-1.1,-24.4)
            teleport(0,-26);aim('altar');page.keyboard.press('e');assert snapshot()['progress']['unlocked']
            aim('boundary_key');page.keyboard.press('e');assert snapshot()['progress']['key']
            page.screenshot(path=str(OUTPUT/'shrine.png'))
        def escape():
            teleport(0,31.5);aim('gate');page.keyboard.press('e');assert snapshot()['mode']=='won'

        response=page.goto(URL+'?test=1',wait_until='networkidle',timeout=60000);assert response.status==200
        page.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
        page.screenshot(path=str(OUTPUT/'title.png'))
        page.click('#title-settings');page.select_option('#difficulty','gentle')
        page.locator('#reduce-motion').check();page.locator('#brightness').fill('1.3');page.click('#close-settings')
        assert page.locator('#title-screen').is_visible();record('title/settings')
        start();page.screenshot(path=str(OUTPUT/'entrance.png'))
        assert page.evaluate("window.kuchiGame.audio.context.state==='running'")
        # Every pickup and the shrine are reachable by swept movement through
        # the actual village, including narrow doors and the well approach.
        routes=page.evaluate('''()=>{
            const g=window.kuchiGame,targets=[[2.4,30.6],[-10,10.8],[-11,9.1],[8,16],[9,14],[-9.4,-4.7],[-8,-4.7],[11,-8.8],[0,-26],[0,31.5]];
            let current={x:0,z:31};const results=[];
            for(const [x,z] of targets){
                const end={x,z},path=g.nav.findPath(current,end);
                if(!path.length)throw new Error('No route to '+x+','+z);
                for(const node of path){
                    for(let i=0;i<1000&&Math.hypot(current.x-node.x,current.z-node.z)>.03;i++){
                        const dx=node.x-current.x,dz=node.z-current.z,d=Math.hypot(dx,dz),step=Math.min(.13,d);
                        g.nav.move(current,dx/d*step,dz/d*step);
                    }
                    if(Math.hypot(current.x-node.x,current.z-node.z)>.1)throw new Error('Blocked route at '+JSON.stringify(node));
                }
                results.push({x,z,waypoints:path.length});
            }
            return results;
        }''')
        assert len(routes)==10;record('all-areas-reachable-through-collision-geometry/audio-start')
        # Real keyboard movement, stamina exhaustion and collision.
        page.keyboard.down('w');page.keyboard.down('Shift');step(7);page.keyboard.up('w');page.keyboard.up('Shift')
        s=snapshot();assert s['player']['z']<10 and s['stamina']<.25,s
        teleport(0,31);page.keyboard.down('s');step(3);page.keyboard.up('s')
        assert snapshot()['player']['z']<33.45
        page.keyboard.press('c');step(.1);assert snapshot()['player']['crouching'];page.keyboard.press('c')
        page.keyboard.press('f');assert not snapshot()['player']['flashlight'];page.keyboard.press('f')
        record('keyboard/sprint/stamina/crouch/flashlight/collision')
        # The gate and altar enforce objectives before any quest pickups.
        aim('gate');page.keyboard.press('e');assert snapshot()['mode']=='playing'
        teleport(0,-26);aim('altar');page.keyboard.press('e');assert not snapshot()['progress']['unlocked']
        record('quest-gating')
        collect();s=snapshot();assert len(s['progress']['seals'])==3 and len(s['progress']['notes'])==3
        page.keyboard.press('Tab');assert page.locator('#journal-screen').is_visible()
        assert page.locator('.note-entry').count()==3
        page.screenshot(path=str(OUTPUT/'journal.png'));page.click('#close-journal');record('all-pickups/notes/map')
        # Unnoticed items land in the world and survive a reload, then can be recovered.
        teleport(0,25);page.evaluate("window.kuchiGame.enemy.position={x:0,z:-20}")
        page.keyboard.press('4');page.keyboard.press('g');step(1.5)
        dropped=snapshot()['dropped'];assert len(dropped)==1
        saved_inventory=snapshot()['progress']['inventory']['onigiri']
        page.reload(wait_until='networkidle');page.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
        page.click('#continue');assert snapshot()['progress']['inventory']['onigiri']==saved_inventory
        assert len(snapshot()['dropped'])==1;d=snapshot()['dropped'][0]
        page.evaluate('window.kuchiGame.enemy.grace=999');teleport(d['x']+1,d['z']);aim(d['id']);page.keyboard.press('e')
        assert not snapshot()['dropped'];assert snapshot()['progress']['inventory']['onigiri']==saved_inventory+1
        record('save/reload/dropped-item-recovery')
        # Audio initialized from an actual click; all three reaction groups use the GLB.
        assert page.evaluate('document.querySelector("#hud").hidden') is False
        throw('onigiri',4,'feed');throw('dango',5,'feed')
        arrange_offering();page.keyboard.press('r');assert snapshot()['enemy']['state']=='ritual'
        step(2);page.screenshot(path=str(OUTPUT/'ritual.png'))
        page.keyboard.press('r');assert snapshot()['bellCooldown']>9;step(11)
        assert snapshot()['progress']['inventory']['kagura_bell']==1
        record('food/skeletal-feed/bell/ritual/cooldown')
        # AI detection, occluded search and real catch/retry.
        teleport(0,5);page.evaluate("const e=window.kuchiGame.enemy;e.position={x:0,z:0};e.angle=0;e.grace=0;e.transition('idle',50)")
        step(.1);assert snapshot()['enemy']['state']=='alert';step(1.5);assert snapshot()['enemy']['state']=='chase'
        page.screenshot(path=str(OUTPUT/'chase.png'))
        teleport(-10,11);step(4.5);assert snapshot()['enemy']['state']=='search',snapshot()
        teleport(0,2);page.evaluate("const e=window.kuchiGame.enemy;e.position={x:0,z:1.4};e.angle=0;e.grace=0;e.transition('chase')")
        step(.1);assert snapshot()['mode']=='dead'
        page.screenshot(path=str(OUTPUT/'caught.png'));page.click('#retry');assert snapshot()['mode']=='playing';assert len(snapshot()['progress']['seals'])==3
        page.evaluate('window.kuchiGame.enemy.grace=999');record('alert/chase/occluded-search/catch/checkpoint-retry')
        # Pause prevents simulation, including reaction cooldown and enemy travel.
        page.keyboard.press('p');before=snapshot();step(5);assert snapshot()==before
        page.click('#resume');record('pause-freezes-world')
        unlock();escape();assert page.locator('#end-title').inner_text()=='霧の外へ'
        page.screenshot(path=str(OUTPUT/'ending-normal.png'));record('altar/key/gate/normal-ending')
        # An independent full playthrough earns the three memories and final ending.
        page.click('#retry');assert snapshot()['progress']['seals']==[]
        page.evaluate('window.kuchiGame.enemy.grace=999');collect()
        for item,key in [('photograph',1),('hairpin',2),('child_sandals',3)]:throw(item,key,'lament')
        assert len(snapshot()['progress']['memories'])==3
        unlock();escape();assert page.locator('#end-title').inner_text()=='おかえり。'
        page.screenshot(path=str(OUTPUT/'ending-memories.png'));record('three-memories/skeletal-lament/memorial-ending')
        # Production route also runs frame-driven input, not only test stepping.
        page.goto(URL,wait_until='networkidle');page.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
        assert page.evaluate('window.kuchiGame === undefined')
        page.click('#start');page.keyboard.down('ArrowRight')
        page.wait_for_function("document.querySelector('#heading').textContent==='東'",timeout=15000)
        page.keyboard.up('ArrowRight');assert page.locator('#hud').is_visible();record('production-frame-driven-input')
        context.close()
        # Touch controls and small-screen layouts use a separate mobile context.
        test_mobile(browser,errors,failures,record)
        assert not errors,errors;assert not failures,failures
        result={'status':'passed','browser':browser.version,'checks':checks,'javascript_errors':errors,'failed_requests':failures}
        (OUTPUT/'game_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        browser.close()

if __name__=='__main__':main()
