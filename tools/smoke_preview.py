"""Browser integration check for all three pursuer assets and the preview UI."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'export/verification'
URL='http://127.0.0.1:'+os.environ.get('KUCHI_PREVIEW_PORT','8765')+'/character.html'
STATES=['idle','walk','alert','chase','search','lament','feed','ritual']
CHARACTERS={'glasses':2048,'cropped':2048,'kuchikagura':1024}
REACTIONS={'photograph':'lament','hairpin':'lament','child_sandals':'lament','onigiri':'feed','dango':'feed','kagura_bell':'ritual'}


def wait_ready(page, character):
    page.wait_for_function("""id => document.body.dataset.ready === 'true'
        && window.kuchiPreview.character === id""", arg=character, timeout=45000)
    assert not page.locator('#missing').is_visible()
    assert page.evaluate('window.kuchiPreview.controller === window.kuchiPreviewAPI.controller')


def check_character(page, character, texture_size):
    target=OUTPUT/character
    target.mkdir(parents=True,exist_ok=True)
    assert page.evaluate('window.kuchiPreview.controller.clips.size')==8
    assert page.locator('#studio').is_checked() == (character!='kuchikagura')
    assert page.locator('#fog').is_checked() == (character=='kuchikagura')
    sizes=page.evaluate("""() => {
        const textures=new Set();
        window.kuchiPreview.controller.model.traverse(o=>{
            for(const material of (Array.isArray(o.material)?o.material:[o.material]))
                if(material?.map)textures.add(material.map);
        });
        return [...textures].map(t=>[t.image.width,t.image.height]);
    }""")
    assert sizes==[[texture_size,texture_size]], sizes
    # The statistics are inside a closed <details>; read its DOM text rather
    # than rendered innerText, which may omit that collapsed content.
    stats=page.locator('#stats').text_content()
    assert f'{texture_size} × {texture_size}' in stats, (character,stats)
    frames={}
    for state in STATES:
        page.locator(f'button[data-state="{state}"]').click()
        assert page.locator('button.active').get_attribute('data-state')==state
        matrices=page.evaluate("""name => {
            const c=window.kuchiPreview.controller;
            c.setPaused(true); c.play(name,{fade:0}); c.seek(0);
            const before=c.model.getObjectByName('HEAD_CTRL').matrixWorld.toArray();
            c.seek(c.duration*.42);
            return [before,c.model.getObjectByName('HEAD_CTRL').matrixWorld.toArray()];
        }""",state)
        assert any(abs(a-b)>1e-5 for a,b in zip(*matrices)), f'Head did not animate: {character}/{state}'
        page.wait_for_timeout(100)
        picture=page.locator('#stage').screenshot()
        frames[state]=hashlib.sha256(picture).hexdigest()
        (target/(state+'.png')).write_bytes(picture)
        if character=='kuchikagura':
            (OUTPUT/(state+'.png')).write_bytes(picture)
    assert len(set(frames.values()))==8, f'States rendered identical frames: {character}'
    phase=page.evaluate("""()=>{
        const c=window.kuchiPreview.controller;c.setPaused(true);
        c.play('lament',{fade:0});c.seek(5);
        const crouch=c.model.getObjectByName('ROOT_CTRL').matrixWorld.elements[13];
        const photoScale=c.model.getObjectByName('MEMORY_PROP_CTRL').scale.x;
        c.play('feed',{fade:0});c.seek(2.04);
        const a=c.model.getObjectByName('FOOD_PROP_CTRL').matrixWorld.elements.slice(12,15);
        const b=c.model.getObjectByName('HEAD_CTRL').matrixWorld.elements.slice(12,15);
        return {crouch,photoScale,foodHeadDistance:Math.hypot(...a.map((v,i)=>v-b[i]))};
    }""")
    assert phase['crouch']<-.25 and phase['photoScale']>.9, (character,phase)
    assert phase['foodHeadDistance']<.38, (character,phase)
    for item,state in REACTIONS.items():
        page.select_option('#item',item);page.click('#offer')
        assert page.evaluate('window.kuchiPreview.controller.state')==state
        assert state==page.locator('button.active').get_attribute('data-state')
    # Let a one-shot return to idle through the real animation mixer event.
    page.evaluate("const c=window.kuchiPreview.controller;c.play('feed',{fade:0});c.seek(c.duration-.08);c.setPaused(false)")
    page.wait_for_function("window.kuchiPreview.controller.state === 'idle'",timeout=3000)
    page.click('#pause');assert page.evaluate('window.kuchiPreview.controller.paused')
    page.locator('#timeline').evaluate("e=>{e.value='1.0';e.dispatchEvent(new Event('input',{bubbles:true}));}")
    assert abs(page.evaluate('window.kuchiPreview.controller.action.time')-1)<.02
    page.click('#replay');assert not page.evaluate('window.kuchiPreview.controller.paused')
    page.select_option('#speed','0.5');assert page.evaluate('window.kuchiPreview.controller.speed')==.5
    page.select_option('#speed','1')
    page.locator('#fog').uncheck();assert page.evaluate('window.kuchiPreview.scene.fog === null')
    page.locator('#fog').check();page.locator('#studio').check();page.locator('#rotate').check()
    angle=page.evaluate('window.kuchiPreview.controller.model.rotation.y')
    page.wait_for_function('(angle)=>window.kuchiPreview.controller.model.rotation.y>angle',arg=angle,timeout=4000)
    page.locator('#rotate').uncheck();page.locator('#fog').uncheck()
    page.evaluate("const c=window.kuchiPreview.controller;c.setPaused(true);c.model.rotation.y=0;c.play('idle',{fade:0});c.seek(0)")
    page.click('#front-camera');page.wait_for_timeout(150)
    assert abs(page.evaluate('window.kuchiPreview.camera.position.x'))<.01
    (target/'front.png').write_bytes(page.locator('#stage').screenshot())
    page.click('#face-camera');page.wait_for_timeout(150)
    assert page.evaluate('window.kuchiPreview.camera.position.distanceTo(window.kuchiPreview.controls.target)')<1
    assert page.evaluate('window.kuchiPreview.controls.target.y')>1.2
    (target/'face.png').write_bytes(page.locator('#stage').screenshot())
    page.click('#reset-camera')
    assert page.evaluate('window.kuchiPreview.camera.position.distanceTo(window.kuchiPreview.controls.target)')>3
    return {'texture_sizes':sizes,'distinct_rendered_frames':len(set(frames.values())),
            'skeletal_clips':STATES,'reaction_pose_checks':phase,'item_reactions':REACTIONS,
            'one_shot_return':'passed','playback_controls':'passed','camera_views':'passed'}


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    errors,requests=[],[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,chromium_sandbox=False,
            args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:requests.append({'url':r.url,'failure':r.failure}))
        response=page.goto(URL,wait_until='networkidle',timeout=45000)
        assert response.status==200
        wait_ready(page,'glasses')
        models={}
        for character,texture_size in CHARACTERS.items():
            if page.evaluate('window.kuchiPreview.character')!=character:
                page.select_option('#character',character)
            wait_ready(page,character)
            assert page.evaluate("new URL(location.href).searchParams.get('character')")==character
            models[character]=check_character(page,character,texture_size)
        # Real selection removes and disposes the previous GPU resources.
        page.evaluate("""() => {
            const old=window.kuchiPreview.controller;
            const resources=new Set();
            old.model.traverse(o=>{
                if(!o.isMesh)return;
                resources.add(o.geometry);
                for(const material of (Array.isArray(o.material)?o.material:[o.material])){
                    resources.add(material);
                    for(const value of Object.values(material))if(value?.isTexture)resources.add(value);
                }
            });
            window.previewDisposal={old,expected:resources.size,actual:0};
            resources.forEach(resource=>resource.addEventListener('dispose',()=>window.previewDisposal.actual++));
        }""")
        page.select_option('#character','glasses');wait_ready(page,'glasses')
        disposal=page.evaluate("""() => ({
            expected:previewDisposal.expected,actual:previewDisposal.actual,
            removed:previewDisposal.old.model.parent===null,
            changed:previewDisposal.old!==window.kuchiPreview.controller
        })""")
        assert disposal['expected']==disposal['actual'] and disposal['removed'] and disposal['changed'],disposal
        # Delay a real GLB response to make the first selection finish last.
        race=page.evaluate("""async () => {
            const original=window.fetch;
            let release;const gate=new Promise(resolve=>release=resolve);
            window.fetch=(input,...args)=>String(input).includes('pursuer_glasses.glb')
                ?gate.then(()=>original(input,...args)):original(input,...args);
            try{
                const first=window.kuchiPreview.selectCharacter('glasses');
                const latest=window.kuchiPreview.selectCharacter('cropped');
                await latest;release();await first;
                return {character:window.kuchiPreview.character,
                    ready:document.body.dataset.ready,
                    matchingScene:window.kuchiPreview.controller.model.parent===window.kuchiPreview.scene};
            }finally{release();window.fetch=original;}
        }""")
        assert race=={'character':'cropped','ready':'true','matchingScene':True},race
        # HTTP failure must disable animation controls and allow another selection.
        page.route('**/assets/models/pursuer_glasses.glb',lambda route:route.fulfill(status=503,body='Temporary model failure'))
        page.select_option('#character','glasses')
        page.wait_for_function("document.body.dataset.ready === 'error'",timeout=15000)
        assert page.locator('#missing').is_visible()
        assert page.locator('#load-error').inner_text().endswith('HTTP 503')
        for selector in ['button[data-state="idle"]','#pause','#offer','#face-camera','#timeline']:
            assert page.locator(selector).is_disabled(),selector
        page.unroute('**/assets/models/pursuer_glasses.glb')
        page.select_option('#character','cropped');wait_ready(page,'cropped')
        assert not page.locator('#offer').is_disabled()
        # URL selection loads the requested GLB directly.
        page.goto(URL+'?character=cropped',wait_until='networkidle',timeout=45000)
        wait_ready(page,'cropped')
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150)
        assert page.evaluate('document.documentElement.scrollWidth')==390
        page.locator('button[data-state="ritual"]').scroll_into_view_if_needed()
        page.locator('button[data-state="ritual"]').click()
        assert page.evaluate('window.kuchiPreview.controller.state')=='ritual'
        for selector in ['#character','#front-camera','#face-camera','#reset-camera']:
            bounds=page.locator(selector).bounding_box()
            assert bounds['x']>=0 and bounds['x']+bounds['width']<=390,bounds
            assert bounds['height']>=44,bounds
        page.locator('#face-camera').click()
        page.evaluate("window.scrollTo(0,0)")
        (OUTPUT/'mobile-face.png').write_bytes(page.screenshot())
        assert not errors,errors
        assert not requests,requests
        result={'status':'passed','browser':browser.version,'characters':models,
                'skeletal_clips':STATES,'distinct_rendered_frames':24,'item_reactions':REACTIONS,
                'resource_disposal':disposal,'stale_response_protection':race,
                'failure_and_recovery':'passed','url_selection':'passed','mobile_controls':'passed',
                'javascript_errors':errors,'failed_requests':requests}
        (OUTPUT/'browser_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        browser.close()

if __name__=='__main__': main()
