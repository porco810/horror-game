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
URL=os.environ.get('KUCHI_GAME_URL','http://127.0.0.1:'+os.environ.get('KUCHI_PREVIEW_PORT','8765')).rstrip('/')+'/'

def test_mobile(browser,errors,failures,record):
    mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
    mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)))
    mp.on('requestfailed',lambda r:failures.append({'url':r.url,'failure':r.failure}))
    mp.goto(URL+'?test=1',wait_until='networkidle');mp.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
    mp.screenshot(path=str(OUTPUT/'mobile-portrait.png'))
    assert mp.locator('#orientation-screen').is_visible()
    assert mp.locator('#title-screen').evaluate('(e)=>e.inert')
    mp.set_viewport_size({'width':844,'height':390});mp.wait_for_function("document.querySelector('#orientation-screen').hidden")
    mp.screenshot(path=str(OUTPUT/'mobile-title.png'));mp.locator('#start').tap()
    mp.wait_for_function('document.fullscreenElement !== null')
    assert mp.locator('#touch-fullscreen').inner_text()=='縮小'
    mp.evaluate("window.kuchiGame.actors.forEach((a,i)=>{a.enemy.grace=999;if(i){a.enemy.transition('idle',999);a.enemy.timer=999;}})")
    cdp=mobile.new_cdp_session(mp)
    def advance(t):mp.evaluate('(t)=>window.kuchiGame.advance(t)',t)
    def state():return mp.evaluate('window.kuchiGame.snapshot()')
    def point(selector,dx=0,dy=0,id=1):
        r=mp.locator(selector).bounding_box()
        return {'x':r['x']+r['width']/2+dx,'y':r['y']+r['height']/2+dy,'id':id}
    def touch(kind,points):cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
    def check_layout(width,height):
        assert mp.evaluate('document.documentElement.scrollWidth')==width
        controls=['#joystick','#look-pad','#inventory-toggle','#touch-interact','#touch-offer','#touch-mode','#torch-toggle','#journal-toggle','#pause-toggle','#touch-fullscreen']
        for selector in controls:
            r=mp.locator(selector).bounding_box()
            assert r and r['x']>=0 and r['y']>=0 and r['x']+r['width']<=width and r['y']+r['height']<=height,(selector,r,width,height)
            assert mp.locator(selector).evaluate('(e)=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return e===hit||e.contains(hit)}'),selector
        left=mp.locator('.move-pad-wrap').bounding_box();right=mp.locator('.look-pad-wrap').bounding_box()
        assert left['x']+left['width']<width*.4 and right['x']>width*.6
        for pad,buttons in [('#joystick',['#inventory-toggle','#touch-mode']),('#look-pad',['#touch-interact','#touch-offer'])]:
            r=mp.locator(pad).bounding_box()
            for selector in buttons:
                b=mp.locator(selector).bounding_box();assert b['y']>r['y']+r['height']
                assert b['width']>=44 and b['height']>=44
        assert mp.locator('#touch-mode').count()==1
        assert mp.locator('#touch-walk,#touch-run,#touch-crouch,.touch-dock').count()==0
        assert not mp.locator('#inventory').is_visible()
    check_layout(844,390)
    assert mp.locator('#touch-mode-label').inner_text()=='歩く'
    mp.locator('#touch-mode').tap();assert mp.locator('#touch-mode-label').inner_text()=='走る'
    mp.locator('#touch-mode').tap();advance(.1);assert state()['player']['crouching']
    assert mp.locator('#touch-mode-label').inner_text()=='屈む'
    mp.locator('#touch-mode').tap();advance(.1);assert not state()['player']['crouching']
    assert mp.locator('#touch-mode-label').inner_text()=='歩く'
    # Native full screen starts on play, pauses on exit and re-enters on resume.
    mp.locator('#touch-fullscreen').tap();mp.wait_for_function('document.fullscreenElement === null')
    assert state()['mode']=='paused';mp.locator('#fullscreen-note').wait_for(state='visible')
    mp.locator('#resume').tap();mp.wait_for_function('document.fullscreenElement !== null')
    assert state()['mode']=='playing'
    mp.locator('#torch-toggle').tap();assert not state()['player']['flashlight']
    mp.evaluate('window.kuchiGame.teleport(0,25)')
    before=state()['player'];left=point('#joystick',dy=-30)
    touch('touchStart',[left]);advance(.4);touch('touchEnd',[])
    after=state()['player'];assert after['z']<before['z']-.8;assert after['yaw']==before['yaw']
    advance(.2);assert state()['player']['z']==after['z']
    mp.locator('#touch-mode').tap();before=state()['player']['z']
    touch('touchStart',[left]);advance(.4);assert state()['player']['running'];touch('touchEnd',[])
    assert state()['player']['z']<before-1.5
    mp.locator('#touch-mode').tap();mp.locator('#touch-mode').tap()
    before=state()['player'];right=point('#look-pad',dx=30,dy=15,id=2)
    touch('touchStart',[right]);advance(.4);touch('touchEnd',[])
    after=state()['player'];assert .32<abs(after['yaw']-before['yaw'])<.45;assert .12<abs(after['pitch']-before['pitch'])<.19
    assert after['x']==before['x'] and after['z']==before['z']
    advance(.2);assert state()['player']['yaw']==after['yaw']
    # Two actual browser touches control independent pads at the same time.
    mp.evaluate('window.kuchiGame.teleport(0,25)');before=state()['player']
    touch('touchStart',[left,right]);advance(.4)
    after=state()['player'];assert after['z']<before['z']-.5;assert .32<abs(after['yaw']-before['yaw'])<.45
    touch('touchCancel',[]);advance(.2);assert state()['player']['yaw']==after['yaw'];assert state()['player']['z']==after['z']
    assert mp.locator('#joystick-knob').evaluate('(e)=>e.style.transform')==''
    assert mp.locator('#look-pad-knob').evaluate('(e)=>e.style.transform')==''
    # Leaving play releases captured input, even while fingers are held down.
    touch('touchStart',[left,right]);mp.locator('#pause-toggle').click();assert state()['mode']=='paused'
    frozen=state();advance(2);assert state()['progress']['elapsed']==frozen['progress']['elapsed']
    touch('touchEnd',[]);mp.locator('#resume').tap();before=state()['player'];advance(.3);assert state()['player']==before
    # Portrait freezes AI, timers and motion; rotating back requires fresh input.
    touch('touchStart',[left,right]);mp.set_viewport_size({'width':390,'height':844})
    mp.wait_for_function("!document.querySelector('#orientation-screen').hidden")
    frozen=state();advance(2);assert state()==frozen
    touch('touchEnd',[]);mp.set_viewport_size({'width':844,'height':390})
    mp.wait_for_function("document.querySelector('#orientation-screen').hidden")
    before=state()['player'];advance(.3);assert state()['player']==before
    # Real action taps collect items and open notes.
    mp.evaluate("window.kuchiGame.teleport(1,31);window.kuchiGame.aim('note_village')")
    assert mp.locator('#touch-interact').inner_text()=='読む';mp.locator('#touch-interact').tap()
    assert mp.locator('#journal-screen').is_visible()
    r=mp.locator('.journal-card').bounding_box();assert r['x']>=0 and r['x']+r['width']<=844
    mp.screenshot(path=str(OUTPUT/'mobile-journal.png'));mp.locator('#close-journal').tap()
    for item,x,z in [('bell',2.4,30.6),('rice_start',3,30.6)]:
        mp.evaluate('([x,z,id])=>{window.kuchiGame.teleport(x,z);window.kuchiGame.aim(id)}',[x,z,item])
        assert mp.locator('#touch-interact').inner_text()=='拾う';mp.locator('#touch-interact').tap()
        assert item in state()['progress']['collected']
    mp.locator('#inventory-toggle').tap();assert state()['mode']=='inventory'
    assert mp.locator('#inventory-toggle').get_attribute('aria-expanded')=='true'
    frozen=state();advance(3);assert state()==frozen
    assert mp.locator('#mobile-inventory [data-item="photograph"]').is_disabled()
    mp.screenshot(path=str(OUTPUT/'mobile-inventory.png'))
    mp.locator('#mobile-inventory [data-item="onigiri"]').tap();assert state()['mode']=='playing'
    assert mp.locator('#touch-offer-label').inner_text()=='手向ける'
    assert mp.locator('#touch-selected').inner_text()=='握り飯'
    mp.evaluate("const g=window.kuchiGame;g.teleport(0,10);g.enemy.position={x:0,z:4};g.enemy.transition('idle',50)")
    before=state()['progress']['inventory']['onigiri'];mp.locator('#touch-offer').tap()
    assert state()['progress']['inventory']['onigiri']==before-1;advance(1.6);assert state()['enemy']['state']=='feed'
    mp.locator('#inventory-toggle').tap();mp.locator('#mobile-inventory [data-item="kagura_bell"]').tap()
    assert mp.locator('#touch-offer-label').inner_text()=='鈴を鳴らす'
    mp.locator('#touch-offer').tap();assert state()['bellCooldown']>11
    assert mp.locator('#touch-offer').is_disabled();assert '秒' in mp.locator('#touch-offer-hint').inner_text()
    mp.locator('#inventory-toggle').tap();mp.locator('#close-inventory').tap();assert state()['mode']=='playing'
    mp.screenshot(path=str(OUTPUT/'mobile-play.png'))
    # Short and notched-phone-sized landscapes keep both pads and all actions reachable.
    for width,height in [(640,320),(667,375),(932,430)]:
        mp.set_viewport_size({'width':width,'height':height});check_layout(width,height)
        mp.locator('#inventory-toggle').tap()
        r=mp.locator('.inventory-card').bounding_box();assert r['x']>=0 and r['y']>=0 and r['x']+r['width']<=width and r['y']+r['height']<=height
        mp.locator('#close-inventory').tap()
        mp.screenshot(path=str(OUTPUT/f'mobile-landscape-{width}.png'))
        mp.locator('#pause-toggle').tap();mp.locator('#return-title').tap()
        for selector in ['#start','#continue','#title-settings']:
            r=mp.locator(selector).bounding_box();assert r and r['y']>=0 and r['y']+r['height']<=height,(selector,r,height)
        mp.locator('#continue').tap()
    mobile.close();record('mobile/slower-look/side-controls/single-cycle-button/fullscreen-entry-exit-resume/multitouch/inventory/rotation/four-layouts')
    # A browser without full screen remains playable, with a home-screen path.
    fallback=browser.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True)
    fallback.add_init_script("Object.defineProperty(Element.prototype,'requestFullscreen',{value:undefined,configurable:true});Object.defineProperty(Element.prototype,'webkitRequestFullscreen',{value:undefined,configurable:true});")
    fp=fallback.new_page();fp.on('pageerror',lambda e:errors.append(str(e)))
    fp.on('requestfailed',lambda r:failures.append({'url':r.url,'failure':r.failure}))
    fp.goto(URL+'?test=1',wait_until='networkidle');fp.wait_for_function("document.body.dataset.ready==='true'",timeout=60000)
    fp.locator('#start').tap();assert fp.evaluate("window.kuchiGame.mode==='playing' && document.fullscreenElement===null")
    fp.locator('#pause-toggle').tap();assert fp.locator('#fullscreen-note').is_visible()
    manifest=fp.evaluate("fetch('manifest.webmanifest').then(r=>r.json())")
    assert manifest['display']=='fullscreen' and manifest['orientation']=='landscape'
    for icon in manifest['icons']:
        width=fp.evaluate("src=>new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i.naturalWidth);i.onerror=reject;i.src=src})",icon['src'])
        assert width==int(icon['sizes'].split('x')[0])
    fp.screenshot(path=str(OUTPUT/'mobile-fullscreen-fallback.png'))
    fallback.close();record('mobile/fullscreen-unavailable/home-screen-manifest/icons')

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
            result={'status':'passed','url':URL,'checks':checks,'javascript_errors':errors,'failed_requests':failures}
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
            page.evaluate("window.kuchiGame.actors.forEach((a,i)=>{a.enemy.grace=999;if(i){a.enemy.transition('idle',999);a.enemy.timer=999;}})")
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
        page.evaluate("window.kuchiGame.actors.forEach((a,i)=>{a.enemy.grace=999;if(i){a.enemy.transition('idle',999);a.enemy.timer=999;}})");teleport(d['x']+1,d['z']);aim(d['id']);page.keyboard.press('e')
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
        page.evaluate("window.kuchiGame.actors.forEach((a,i)=>{a.enemy.grace=999;if(i){a.enemy.transition('idle',999);a.enemy.timer=999;}})");record('alert/chase/occluded-search/catch/checkpoint-retry')
        # Pause prevents simulation, including reaction cooldown and enemy travel.
        page.keyboard.press('p');before=snapshot();step(5);assert snapshot()==before
        page.click('#resume');record('pause-freezes-world')
        unlock();escape();assert page.locator('#end-title').inner_text()=='霧の外へ'
        page.screenshot(path=str(OUTPUT/'ending-normal.png'));record('altar/key/gate/normal-ending')
        # An independent full playthrough earns the three memories and final ending.
        page.click('#retry');assert snapshot()['progress']['seals']==[]
        page.evaluate("window.kuchiGame.actors.forEach((a,i)=>{a.enemy.grace=999;if(i){a.enemy.transition('idle',999);a.enemy.timer=999;}})");collect()
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
        result={'status':'passed','url':URL,'browser':browser.version,'checks':checks,'javascript_errors':errors,'failed_requests':failures}
        (OUTPUT/'game_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        browser.close()

if __name__=='__main__':main()
