"""Browser integration check. Uses installed Chromium and Python Playwright."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'export/verification'
URL='http://127.0.0.1:'+os.environ.get('KUCHI_PREVIEW_PORT','8765')+'/character.html'
STATES=['idle','walk','alert','chase','search','lament','feed','ritual']

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    errors,requests=[],[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,chromium_sandbox=False,
            args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:requests.append({'url':r.url,'failure':r.failure}))
        response=page.goto(URL,wait_until='networkidle',timeout=30000)
        assert response.status==200
        page.wait_for_function("document.body.dataset.ready === 'true'",timeout=30000)
        assert not page.locator('#missing').is_visible()
        assert page.evaluate('window.kuchiPreview.controller.clips.size')==8
        frames={}
        for state in STATES:
            page.locator(f'button[data-state="{state}"]').click()
            assert page.locator('button.active').get_attribute('data-state')==state
            matrices=page.evaluate('''name => {
                const c=window.kuchiPreview.controller;
                c.setPaused(true); c.play(name,{fade:0}); c.seek(0);
                const before=c.model.getObjectByName('HEAD_CTRL').matrixWorld.toArray();
                c.seek(c.duration*.42);
                return [before,c.model.getObjectByName('HEAD_CTRL').matrixWorld.toArray()];
            }''',state)
            assert any(abs(a-b)>1e-5 for a,b in zip(*matrices)), f'Head did not animate: {state}'
            page.wait_for_timeout(100)
            picture=page.locator('#stage').screenshot()
            frames[state]=hashlib.sha256(picture).hexdigest()
            (OUTPUT/(state+'.png')).write_bytes(picture)
        assert len(set(frames.values()))==8, 'States rendered identical frames'
        phase=page.evaluate('''()=>{
            const c=window.kuchiPreview.controller;c.setPaused(true);
            c.play('lament',{fade:0});c.seek(5);
            const crouch=c.model.getObjectByName('ROOT_CTRL').matrixWorld.elements[13];
            const photoScale=c.model.getObjectByName('MEMORY_PROP_CTRL').scale.x;
            c.play('feed',{fade:0});c.seek(2.04);
            const a=c.model.getObjectByName('FOOD_PROP_CTRL').matrixWorld.elements.slice(12,15);
            const b=c.model.getObjectByName('HEAD_CTRL').matrixWorld.elements.slice(12,15);
            return {crouch,photoScale,foodHeadDistance:Math.hypot(...a.map((v,i)=>v-b[i]))};
        }''')
        assert phase['crouch']<-.25 and phase['photoScale']>.9, phase
        assert phase['foodHeadDistance']<.38, phase
        reactions={'photograph':'lament','hairpin':'lament','child_sandals':'lament','onigiri':'feed','dango':'feed','kagura_bell':'ritual'}
        for item,state in reactions.items():
            page.select_option('#item',item);page.click('#offer')
            assert page.evaluate('window.kuchiPreview.controller.state')==state
            assert state in page.locator('button.active').get_attribute('data-state')
        # Observe a one-shot completing and returning to idle through the real mixer event.
        page.evaluate("const c=window.kuchiPreview.controller;c.play('feed',{fade:0});c.seek(c.duration-.08);c.setPaused(false)")
        page.wait_for_function("window.kuchiPreview.controller.state === 'idle'",timeout=3000)
        page.click('#pause');assert page.evaluate('window.kuchiPreview.controller.paused')
        page.locator('#timeline').evaluate("e=>{e.value='1.0';e.dispatchEvent(new Event('input',{bubbles:true}));}")
        assert abs(page.evaluate('window.kuchiPreview.controller.action.time')-1)<.02
        page.click('#replay');assert not page.evaluate('window.kuchiPreview.controller.paused')
        page.select_option('#speed','0.5');assert page.evaluate('window.kuchiPreview.controller.speed')==.5
        page.locator('#fog').uncheck();assert page.evaluate('window.kuchiPreview.scene.fog === null')
        page.locator('#fog').check();page.locator('#studio').check();page.locator('#rotate').check()
        angle=page.evaluate('window.kuchiPreview.controller.model.rotation.y')
        page.wait_for_function('(angle)=>window.kuchiPreview.controller.model.rotation.y>angle',arg=angle,timeout=4000)
        page.locator('#rotate').uncheck()
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150)
        assert page.evaluate('document.documentElement.scrollWidth')==390
        page.locator('button[data-state="ritual"]').scroll_into_view_if_needed();page.locator('button[data-state="ritual"]').click()
        assert page.evaluate('window.kuchiPreview.controller.state')=='ritual'
        assert not errors,errors
        assert not requests,requests
        result={'status':'passed','browser':browser.version,'skeletal_clips':STATES,
                'distinct_rendered_frames':8,'item_reactions':reactions,'one_shot_return':'passed',
                'reaction_pose_checks':phase,'playback_controls':'passed','mobile_controls':'passed','javascript_errors':errors,'failed_requests':requests}
        (OUTPUT/'browser_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        browser.close()

if __name__=='__main__': main()
