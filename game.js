import * as THREE from 'three';
import {KuchikaguraController} from './character-controller.js';
import {createVillage,makeOffering} from './world.js';
import {VillageAudio} from './audio.js';
import {attachTouchPad} from './touch-pad.js';
import {ITEMS,ITEM_ORDER,NOTES,SEALS,SAVE_KEY,SPAWN,freshProgress,parseProgress,VillageNavigation,PursuerAI,clamp,distance} from './gameplay.js';

const $=s=>document.querySelector(s),canvas=$('#game-canvas');
const testMode=new URLSearchParams(location.search).get('test')==='1';
const keys=new Set(),touch={x:0,z:0,lookX:0,lookY:0,running:false,crouching:false};
const coarsePointer=matchMedia('(pointer:coarse)'),portraitScreen=matchMedia('(orientation:portrait)');
let orientationBlocked=coarsePointer.matches&&portraitScreen.matches,resetPads=()=>{};
let mode='title',started=false,settingsReturn='title',journalReturn='playing',ready=false;
let progress=freshProgress(),savedInMemory=null,selected='kagura_bell',stamina=1,exhausted=false,bellCooldown=0;
let subtitleUntil=0,toastUntil=0,time=0,renderTime=0,focused=null,lastState='',projectiles=[],dropped=[];
const player={...SPAWN,yaw:0,pitch:0,flashlight:true,running:false,crouching:false,moving:false};
const audio=new VillageAudio();
let settings={difficulty:'normal',brightness:1.25,volume:.55,sensitivity:1,reduceMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,quality:matchMedia('(pointer:coarse)').matches?'low':'standard'};
try{const s=JSON.parse(localStorage.getItem('kuchi-kagura-settings-v1'));if(s){for(const k of ['brightness','volume','sensitivity'])if(Number.isFinite(s[k]))settings[k]=clamp(s[k],k==='volume'?0:.5,k==='volume'?1:2);if(['normal','gentle'].includes(s.difficulty))settings.difficulty=s.difficulty;if(['standard','low'].includes(s.quality))settings.quality=s.quality;if(typeof s.reduceMotion==='boolean')settings.reduceMotion=s.reduceMotion;}}catch{}
let renderer,scene,camera,world,nav,controller,enemy,flashlight,moon;
let reactionProp=null;
function setReactionProp(item){
  if(reactionProp){reactionProp.removeFromParent();reactionProp=null;}
  if(!item)return;
  reactionProp=makeOffering(item);reactionProp.userData.bone=ITEMS[item].kind==='memory'?'MEMORY_PROP_CTRL':ITEMS[item].kind==='food'?'FOOD_PROP_CTRL':'BELL_PROP_CTRL';
  reactionProp.scale.setScalar(.7);reactionProp.visible=false;scene.add(reactionProp);
}
function updateReactionProp(){
  if(!reactionProp)return;controller.model.updateMatrixWorld(true);
  const name=reactionProp.userData.bone,bone=controller.model.getObjectByName(name);
  bone.getWorldPosition(reactionProp.position);bone.getWorldQuaternion(reactionProp.quaternion);
  reactionProp.visible=(controller.propScales?.[name]??0)>.1;
}
function showError(error){ready=false;setMode('error');$('#error-message').textContent=error.message;console.error(error);}
function setMode(next){
  mode=next;keys.clear();resetPads();player.running=player.moving=false;
  for(const id of ['title','pause','settings','journal','inventory','end','error'])$('#'+id+'-screen').hidden=!(next===id||id==='pause'&&next==='paused'||id==='end'&&['dead','won'].includes(next));
  $('#hud').hidden=!started||['title','dead','won','error'].includes(next);
  $('#hud').inert=next!=='playing'||orientationBlocked;
  $('#inventory-toggle').setAttribute('aria-expanded',String(next==='inventory'));
  audio.setPaused(next!=='playing'||orientationBlocked);
  if(next!=='playing'&&document.pointerLockElement===canvas)document.exitPointerLock();
  if(next==='playing')$('#look-hint').hidden=document.pointerLockElement===canvas||matchMedia('(pointer:coarse)').matches;
  if(next==='title')updateContinue();
  const focus={paused:'#resume',journal:'#close-journal',inventory:'#close-inventory',settings:'#close-settings',dead:'#retry',won:'#retry',title:'#start'}[next];
  if(focus)$(focus).focus({preventScroll:true});
  document.body.dataset.mode=next;
}
function readSave(){try{return parseProgress(localStorage.getItem(SAVE_KEY))||savedInMemory;}catch{return savedInMemory;}}
function save(){
  savedInMemory=structuredClone(progress);
  try{localStorage.setItem(SAVE_KEY,JSON.stringify(progress));$('#save-status').textContent='拾得時に自動保存 · 記憶は残っています';}
  catch{$('#save-status').textContent='このブラウザでは保存できません · この画面を閉じるまで記憶を保持';}
}
function updateContinue(){$('#continue').hidden=!ready||!readSave();}
function subtitle(text,seconds=5){$('#subtitle').textContent=text;subtitleUntil=time+seconds;}
function toast(text,seconds=4){$('#toast').textContent=text;toastUntil=time+seconds;}
function objective(){return progress.key?'境の鍵を持って、南の門へ戻る':progress.unlocked?'祭壇から境の鍵を受け取る':progress.seals.length===3?'北の社へ、三枚の札を返す':'三枚の鎮め札を探す — 屋敷・井戸・蔵';}
function refreshHUD(){
  $('#objective').textContent=objective();$('#seal-count').textContent=`${progress.seals.length} / 3`;
  $('#seal-progress').setAttribute('aria-label',`鎮め札 ${progress.seals.length} / 3`);
  [...$('#seal-progress').querySelectorAll('span')].forEach((s,i)=>s.classList.toggle('found',progress.seals.includes(SEALS[i])));
  for(const b of document.querySelectorAll('#inventory button, #mobile-inventory button')){const item=b.dataset.item,count=progress.inventory[item];b.classList.toggle('empty',!count);b.classList.toggle('selected',item===selected);b.setAttribute('aria-pressed',String(item===selected));b.querySelector('.item-count').textContent=count?item==='kagura_bell'?'∞':count:'—';b.setAttribute('aria-label',`${ITEMS[item].name} ${count?item==='kagura_bell'?'所持':count+'個':'未所持'}`);if(b.parentElement.id==='mobile-inventory')b.disabled=!count;}
  refreshSelected();
}
function refreshSelected(){
  const count=progress.inventory[selected],owned=count>0,bell=selected==='kagura_bell';
  $('#selected-hint').textContent=!owned?`${ITEMS[selected].name}を探す`:bell?bellCooldown>0?`鈴の余韻 · あと ${Math.ceil(bellCooldown)} 秒`:'R ／ G で鳴らす · 手に持ったまま':`G で ${ITEMS[selected].name}を手向ける · 怪異の近くへ`;
  $('#touch-selected').textContent=owned?ITEMS[selected].short:'選ぶ';
  $('#touch-offer-label').textContent=bell?'鈴を鳴らす':'手向ける';
  $('#touch-offer-hint').textContent=!owned?'未所持':bell?bellCooldown>0?`あと ${Math.ceil(bellCooldown)} 秒`:'何度でも':`${ITEMS[selected].short} × ${count}`;
  $('#touch-offer').disabled=!owned||(bell&&bellCooldown>0);
  $('#touch-offer').setAttribute('aria-label',owned?bell?'神楽鈴を鳴らす':`${ITEMS[selected].name}を手向ける`:'品物を選んでください');
}
function synchronizeEntities(){
  for(const e of world.entities){
    if(e.type==='key')e.object.visible=progress.unlocked&&!progress.key;
    else if(e.type==='altar'||e.type==='gate')e.object.visible=true;
    else e.object.visible=!progress.collected.includes(e.id);
  }
}
function clearProjectiles(){for(const p of projectiles)p.object.removeFromParent();for(const e of dropped)e.object.removeFromParent();projectiles=[];dropped=[];}
function addDropped(data,object=null){
  const o=object||makeOffering(data.item);o.position.set(data.x,.08,data.z);scene.add(o);
  const e={...data,type:'dropped',y:.08,object:o};dropped.push(e);return e;
}
function begin(continuing=false,lock=true){
  if(!ready||orientationBlocked)return;
  progress=continuing?(readSave()||freshProgress()):freshProgress();
  // Reject checkpoints made inaccessible by an older save or changed map.
  if(!nav.free(progress.checkpoint))progress.checkpoint={...SPAWN};
  Object.assign(player,progress.checkpoint,{yaw:0,pitch:0,flashlight:true,running:false,crouching:false,moving:false});
  started=true;stamina=1;exhausted=false;bellCooldown=0;time=progress.elapsed;touch.running=touch.crouching=false;
  audio.resetClock();
  refreshTouch();$('#torch-toggle').setAttribute('aria-pressed','true');
  clearProjectiles();setReactionProp(null);for(const d of progress.dropped)addDropped(d);
  enemy.reset();controller.play('idle',{fade:0});selected=progress.inventory.kagura_bell?'kagura_bell':ITEM_ORDER.find(k=>progress.inventory[k])||'kagura_bell';
  synchronizeEntities();refreshHUD();setMode('playing');updateCamera(0);save();
  subtitle(continuing?'灯りは、まだ消えていない。':'南の門は閉ざされている。入口の置き手紙を読もう。',7);
  audio.start().catch(()=>toast('音を再生できませんでした。設定から音量を確認してください。'));
  if(lock)requestLook();
}
function requestLook(){
  if(matchMedia('(pointer:coarse)').matches||!canvas.requestPointerLock)return;
  try{const promise=canvas.requestPointerLock();promise?.catch(()=>{$('#look-hint').hidden=false;});}catch{$('#look-hint').hidden=false;}
}
function pause(){if(mode==='playing'){save();setMode('paused');}}
function resume(){setMode('playing');requestLook();}
function returnTitle(){if(started&&mode!=='won')save();started=false;setMode('title');$('#danger-shade').style.opacity=0;}
function openJournal(){journalReturn=mode==='paused'?'paused':'playing';drawJournal();setMode('journal');}
function openSettings(){settingsReturn=mode==='title'?'title':'paused';setMode('settings');}
function openInventory(){if(mode!=='playing')return;refreshHUD();setMode('inventory');}
function updateOrientation(){
  orientationBlocked=coarsePointer.matches&&portraitScreen.matches;
  $('#orientation-screen').hidden=!orientationBlocked;
  $('#hud').inert=mode!=='playing'||orientationBlocked;
  for(const element of document.querySelectorAll('.screen:not(#orientation-screen)'))element.inert=orientationBlocked;
  audio.setPaused(mode!=='playing'||orientationBlocked);
  keys.clear();resetPads();player.running=player.moving=false;
  if(orientationBlocked&&mode==='playing')save();
}
async function requestLandscape(){
  try{
    if(!document.fullscreenElement){
      if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();
      else document.documentElement.webkitRequestFullscreen?.();
    }
    if(screen.orientation?.lock)await screen.orientation.lock('landscape');
  }catch{/* Rotation remains manual on browsers that do not support locking. */}
}
function drawJournal(){
  const list=$('#notes-list');list.replaceChildren();
  if(!progress.notes.length){const p=document.createElement('p');p.className='empty-notes';p.textContent='まだ、誰の言葉も拾っていない。入口の置き手紙を探そう。';list.append(p);}
  for(const key of [...progress.notes].reverse()){
    const n=NOTES[key],d=document.createElement('details'),s=document.createElement('summary'),small=document.createElement('small'),p=document.createElement('p');d.className='note-entry';d.open=key===progress.notes.at(-1);s.textContent=n.title;small.textContent=n.place;s.append(small);p.textContent=n.text;d.append(s,p);list.append(d);
  }
  $('#journal-objective').textContent=objective()+`\n手向けた思い出 ${progress.memories.length} / 3`;
  const c=$('#village-map').getContext('2d'),px=x=>180+x*5.7,pz=z=>225+z*5.7;
  c.clearRect(0,0,360,440);c.fillStyle='#1c2a21';c.fillRect(0,0,360,440);
  c.strokeStyle='#415244';c.lineWidth=12;c.beginPath();c.moveTo(px(0),pz(31));c.lineTo(px(0),pz(-27));c.stroke();
  c.lineWidth=7;for(const z of [16,11,-7]){c.beginPath();c.moveTo(px(-12),pz(z));c.lineTo(px(13),pz(z));c.stroke();}
  c.textAlign='center';c.font='13px "Yu Mincho",serif';
  for(const [label,x,z,w,d] of [['旧家',-10,11,7,7],['炊事小屋',10,16,7,7],['蔵',11,-7,7,7],['社',0,-27,9,6],['井戸',-8,-8,2,2],['境の門',0,32,5,1]]){
    c.fillStyle='#778365';c.fillRect(px(x-w/2),pz(z-d/2),w*5.7,d*5.7);c.fillStyle='#d4cfb1';c.fillText(label,px(x),pz(z)-d*3.1-9);
  }
  c.fillStyle='#cfb57e';c.beginPath();c.arc(px(player.x),pz(player.z),4,0,Math.PI*2);c.fill();
  c.strokeStyle='#ceb480';c.lineWidth=1.5;c.beginPath();c.moveTo(px(player.x),pz(player.z));c.lineTo(px(player.x)-Math.sin(player.yaw)*12,pz(player.z)-Math.cos(player.yaw)*12);c.stroke();
  c.fillStyle='#a9b493';c.font='12px serif';c.fillText('北',324,28);c.beginPath();c.moveTo(324,40);c.lineTo(324,61);c.stroke();c.fillText('● 現在地',70,420);
}
function interact(){
  if(mode!=='playing')return;findFocus();const e=focused;if(!e)return;
  if(e.type==='gate'){
    if(progress.key)finish(true);else subtitle('門は固く閉ざされている。三枚の札を、北の社へ返そう。');return;
  }
  if(e.type==='altar'){
    if(progress.seals.length<3){subtitle(`祭壇には三枚の札が必要だ。残り ${3-progress.seals.length} 枚。`);return;}
    progress.unlocked=true;progress.checkpoint={x:0,z:-23};audio.bell();synchronizeEntities();save();refreshHUD();subtitle('札が収まり、縄がほどける。祭壇に、境の鍵が現れた。',7);return;
  }
  if(e.type==='key'){progress.key=true;progress.collected.push(e.id);save();synchronizeEntities();refreshHUD();audio.pickup();subtitle('境の鍵を受け取った。南の門へ戻ろう。',7);return;}
  if(e.type==='note'){
    if(!progress.notes.includes(e.note))progress.notes.push(e.note);
    if(!progress.collected.includes(e.id))progress.collected.push(e.id);
    save();synchronizeEntities();audio.pickup();openJournal();return;
  }
  if(e.type==='dropped'){
    progress.inventory[e.item]++;progress.dropped=progress.dropped.filter(d=>d.id!==e.id);e.object.removeFromParent();dropped=dropped.filter(d=>d!==e);toast(`${ITEMS[e.item].name}を拾い直した`);
  }else if(e.type==='item'){
    progress.inventory[e.item]+=e.amount||1;progress.collected.push(e.id);selected=e.item;
    toast(`${ITEMS[e.item].name}を拾った${e.amount?' × '+e.amount:''}`);
    if(e.item==='kagura_bell')subtitle('鈴を鳴らせば、あの足音は止まる。Rで鳴らす。',6);
  }else if(e.type==='seal'){
    progress.seals.push(e.id);progress.collected.push(e.id);toast(`${e.place}の鎮め札を拾った — ${progress.seals.length} / 3`);
    if(progress.seals.length===3)subtitle('三枚の札が揃った。北の社へ返そう。',7);
  }
  synchronizeEntities();refreshHUD();audio.pickup();save();
}
function toggleTorch(){if(mode!=='playing')return;player.flashlight=!player.flashlight;$('#torch-toggle').setAttribute('aria-pressed',String(player.flashlight));}
function ring(){
  if(mode!=='playing')return;
  if(!progress.inventory.kagura_bell){toast('神楽鈴を持っていない。入口の供物台を探そう。');return;}
  if(bellCooldown>0){toast(`鈴の余韻が残っている。あと ${Math.ceil(bellCooldown)} 秒。`,2);return;}
  bellCooldown=12;audio.bell();
  if(enemy.offer('kagura_bell',player))subtitle('鈴の音に、あれは舞い始めた。今のうちに離れよう。',5);
  else{enemy.hears(player,2);subtitle('霧の奥へ、鈴の音が沈んでいく。',3);}
  refreshHUD();
}
function offer(){
  if(mode!=='playing')return;
  if(selected==='kagura_bell'){ring();return;}
  if(!progress.inventory[selected]){toast(`${ITEMS[selected].name}を持っていない。`);return;}
  if(projectiles.length>=3)return;
  progress.inventory[selected]--;refreshHUD();
  const object=makeOffering(selected);object.position.set(player.x,player.crouching?.8:1.3,player.z);
  const forward=new THREE.Vector3();camera.getWorldDirection(forward);forward.y=clamp(forward.y,-.2,.65);
  const velocity=forward.multiplyScalar(6.3);velocity.y+=2.0;
  const id=`drop_${Math.round(time*1000)}_${progress.dropped.length}`;
  progress.dropped.push({id,item:selected,x:player.x,z:player.z});
  scene.add(object);projectiles.push({id,item:selected,object,velocity,age:0});save();audio.throw();
}
function tickProjectiles(dt){
  for(const p of [...projectiles]){
    const previous={x:p.object.position.x,z:p.object.position.z};p.age+=dt;p.velocity.y-=9.8*dt;p.object.position.addScaledVector(p.velocity,dt);p.object.rotation.y+=dt*3;
    if(!nav.free(p.object.position,0)||!nav.lineClear(previous,p.object.position,0,p.object.position.y)){p.object.position.x=previous.x;p.object.position.z=previous.z;p.velocity.x=p.velocity.z=0;}
    if(p.object.position.y<=.1||p.age>2){
      const pos={x:p.object.position.x,z:p.object.position.z};
      if(enemy.offer(p.item,pos)){
        progress.dropped=progress.dropped.filter(d=>d.id!==p.id);
        p.object.removeFromParent();
        if(ITEMS[p.item].kind==='memory'&&!progress.memories.includes(p.item))progress.memories.push(p.item);
        subtitle(ITEMS[p.item].kind==='memory'?'拾い上げた記憶を見つめ、あれはしゃがみ込んだ。':'空腹が、追うことを忘れさせた。',4);save();
      }else{
        const data={id:p.id,item:p.item,...pos};progress.dropped=progress.dropped.map(d=>d.id===p.id?data:d);addDropped(data,p.object);toast('品物は地面に残っている。Eで拾い直せる。');save();enemy.hears(pos,.65);
      }
      projectiles=projectiles.filter(x=>x!==p);
    }
  }
}
function findFocus(){
  const forward=new THREE.Vector3();camera.getWorldDirection(forward);let best=Infinity;focused=null;
  for(const e of [...world.entities,...dropped]){
    if(!e.object.visible||e.type==='altar'&&progress.unlocked)continue;
    const d=distance(e,player);if(d>2.5||!nav.lineClear(player,e,0,1))continue;
    const dir=new THREE.Vector3(e.x-player.x,e.y+.12-camera.position.y,e.z-player.z).normalize(),dot=dir.dot(forward);
    if(dot<.8&&!(d<1.3&&dot>.25))continue;
    const score=d+(1-dot)*2;if(score<best){focused=e;best=score;}
  }
  $('#interaction').hidden=!focused;$('#crosshair').classList.toggle('active',Boolean(focused));
  $('#touch-interact').disabled=!focused;
  $('#touch-interact').textContent=!focused?'調べる':focused.type==='note'?'読む':['item','dropped','seal','key'].includes(focused.type)?'拾う':focused.type==='altar'?'札を納める':progress.key?'門を開く':'調べる';
  if(focused){const e=focused;$('#interaction-text').textContent=e.type==='note'?NOTES[e.note].title+'を読む':e.type==='item'||e.type==='dropped'?ITEMS[e.item].name+'を拾う':e.type==='seal'?'鎮め札を拾う':e.type==='altar'?'祭壇へ札を納める':e.type==='key'?'境の鍵を受け取る':progress.key?'境の門を開ける':'境の門を調べる';}
}
function updateCamera(dt){
  const targetHeight=player.crouching?1.05:1.65,bob=settings.reduceMotion?0:player.moving?Math.sin(time*(player.running?14:9))*(player.running?.034:.016):Math.sin(time*1.4)*.003;
  const height=dt?THREE.MathUtils.lerp(camera.position.y,targetHeight+Math.abs(bob),1-Math.exp(-dt*11)):targetHeight;
  camera.position.set(player.x,height,player.z);camera.rotation.order='YXZ';camera.rotation.set(player.pitch,player.yaw,settings.reduceMotion?0:bob*.16);
  flashlight.visible=player.flashlight;$('#torch-toggle').setAttribute('aria-pressed',String(player.flashlight));
}
function finish(won){
  if(mode!=='playing')return;save();
  const trueEnding=progress.memories.length===3;
  $('#end-eyebrow').textContent=won?trueEnding?'結び — 送り神楽':'終幕 — 境を越えて':'記憶は、まだ終わらない。';
  $('#end-title').textContent=won?trueEnding?'おかえり。':'霧の外へ':'帰れなかった。';
  $('#end-story').textContent=won?trueEnding?'写真。花のかんざし。小さな草履。\n三つの記憶を抱き、あの人は社へ帰った。\n\n夜明けの山に、鈴の音がひとつ。\n今度は、誰の足音も追ってこない。':'鍵は、境の門を開いた。\n振り返ると、村はもう見えなかった。\n\n霧の向こうで、誰かがまだ、\n帰らないものを探している。':'背後で、白い袖が揺れた。\n最後に拾った記憶を頼りに、\nもう一度、あの村を歩こう。';
  const minutes=Math.floor(progress.elapsed/60),seconds=Math.floor(progress.elapsed%60);
  $('#end-stats').textContent=`探索 ${minutes}分${seconds}秒 · 札 ${progress.seals.length}/3 · 手向けた思い出 ${progress.memories.length}/3`;
  $('#retry').firstChild.textContent=won?'もう一度、村へ入る ':'記憶からやり直す ';
  if(won){savedInMemory=null;try{localStorage.removeItem(SAVE_KEY);}catch{}}else audio.catch();
  setMode(won?'won':'dead');
}
function simulate(dt){
  if(mode!=='playing'||orientationBlocked)return;time+=dt;progress.elapsed+=dt;bellCooldown=Math.max(0,bellCooldown-dt);
  let side=(keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0)+touch.x,forward=(keys.has('KeyW')||keys.has('ArrowUp')?1:0)-(keys.has('KeyS')||keys.has('ArrowDown')?1:0)-touch.z;
  if(keys.has('ArrowLeft'))player.yaw+=dt*1.6;if(keys.has('ArrowRight'))player.yaw-=dt*1.6;
  player.yaw-=touch.lookX*dt*1.9*settings.sensitivity;
  player.pitch=clamp(player.pitch-touch.lookY*dt*1.5*settings.sensitivity,-1.25,1.1);
  player.crouching=touch.crouching||keys.has('ControlLeft')||keys.has('ControlRight');
  const magnitude=Math.hypot(side,forward);if(magnitude>1){side/=magnitude;forward/=magnitude;}
  player.moving=magnitude>.08;player.running=player.moving&&!player.crouching&&!exhausted&&stamina>.02&&(touch.running||keys.has('ShiftLeft')||keys.has('ShiftRight'));
  stamina=clamp(stamina+dt*(player.running?-.17:player.crouching?.13:.105),0,1);if(stamina<=.02)exhausted=true;if(stamina>.28)exhausted=false;
  const speed=player.crouching?1.45:player.running?4.8:2.7;
  nav.move(player,(Math.cos(player.yaw)*side-Math.sin(player.yaw)*forward)*speed*dt,(-Math.sin(player.yaw)*side-Math.cos(player.yaw)*forward)*speed*dt);
  updateCamera(dt);tickProjectiles(dt);enemy.update(dt,player);controller.update(dt);
  controller.model.position.set(enemy.position.x,0,enemy.position.z);
  controller.model.rotation.y=THREE.MathUtils.lerp(controller.model.rotation.y,controller.model.rotation.y+Math.atan2(Math.sin(enemy.angle-controller.model.rotation.y),Math.cos(enemy.angle-controller.model.rotation.y)),1-Math.exp(-dt*7));
  updateReactionProp();
  findFocus();$('#stamina-fill').style.width=stamina*100+'%';$('#posture').textContent=player.crouching?'息をひそめる':player.running?'走る':exhausted?'息を整える':'歩く';
  $('#heading').textContent=['北','西','南','東'][((Math.round(player.yaw/(Math.PI/2))%4)+4)%4];
  $('#location').textContent=player.z>22?'境の門':player.z<-19?'山の社':player.x<-5&&player.z>4?'旧家':player.x>5&&player.z>9?'炊事小屋':player.x<-5&&player.z<-3?'井戸':player.x>5&&player.z<-3?'穀蔵':'村の小径';
  if(subtitleUntil<time)$('#subtitle').textContent='';if(toastUntil<time)$('#toast').textContent='';
  const d=distance(enemy.position,player);$('#danger-shade').style.opacity=enemy.state==='chase'?clamp(1-d/18,.08,.55):0;
  refreshSelected();
  const rightX=Math.cos(player.yaw),rightZ=-Math.sin(player.yaw),pan=((enemy.position.x-player.x)*rightX+(enemy.position.z-player.z)*rightZ)/Math.max(1,d);
  audio.update({running:player.running,moving:player.moving,crouching:player.crouching,enemyDistance:d,enemyPan:pan,state:enemy.state,time});
}
function applySettings(){
  if(!renderer)return;renderer.toneMappingExposure=settings.brightness;renderer.setPixelRatio(Math.min(devicePixelRatio,settings.quality==='low'?1:1.5));renderer.shadowMap.enabled=settings.quality!=='low';
  audio.setVolume(settings.volume);if(enemy)enemy.difficulty=settings.difficulty;
}
function wireUI(){
  for(const id of ['inventory','mobile-inventory'])ITEM_ORDER.forEach((item,index)=>{const b=document.createElement('button');b.dataset.item=item;b.innerHTML=`<kbd>${index+1}</kbd><span class="item-glyph">${ITEMS[item].glyph}</span><span class="item-name">${id==='inventory'?ITEMS[item].short:ITEMS[item].name}</span><span class="item-count">—</span>`;b.addEventListener('click',()=>{selected=item;refreshHUD();if(mode==='inventory')resume();});$('#'+id).append(b);});
  const actions={'#start':()=>begin(false),'#continue':()=>begin(true),'#resume':resume,'#pause-toggle':pause,'#return-title':returnTitle,'#end-return':returnTitle,'#retry':()=>begin(mode!=='won'),'#journal-toggle':openJournal,'#pause-journal':openJournal,'#close-journal':()=>{setMode(journalReturn);if(mode==='playing')requestLook();},'#title-settings':openSettings,'#pause-settings':openSettings,'#close-settings':()=>setMode(settingsReturn),'#torch-toggle':toggleTorch,'#touch-interact':interact,'#touch-offer':offer,'#inventory-toggle':openInventory,'#close-inventory':resume,'#touch-fullscreen':requestLandscape,'#rotate-fullscreen':requestLandscape,'#reload':()=>location.reload()};
  for(const [selector,handler] of Object.entries(actions))$(selector).addEventListener('click',handler);
  for(const key of Object.keys(settings)){
    const element=$('#'+({reduceMotion:'reduce-motion'}[key]||key));if(!element)continue;
    if(element.type==='checkbox')element.checked=settings[key];else element.value=settings[key];
    element.addEventListener('input',()=>{settings[key]=element.type==='checkbox'?element.checked:element.type==='range'?Number(element.value):element.value;applySettings();try{localStorage.setItem('kuchi-kagura-settings-v1',JSON.stringify(settings));}catch{}});
  }
  $('#touch-walk').addEventListener('click',()=>{touch.running=touch.crouching=false;refreshTouch();});
  $('#touch-run').addEventListener('click',()=>{touch.running=!touch.running;touch.crouching=false;refreshTouch();});
  $('#touch-crouch').addEventListener('click',()=>{touch.crouching=!touch.crouching;touch.running=false;refreshTouch();});
}
function refreshTouch(){$('#touch-walk').setAttribute('aria-pressed',String(!touch.running&&!touch.crouching));$('#touch-run').setAttribute('aria-pressed',String(touch.running));$('#touch-crouch').setAttribute('aria-pressed',String(touch.crouching));}
function wireInput(){
  addEventListener('keydown',e=>{
    if(e.code==='Escape'){
      if(mode==='playing')pause();else if(mode==='paused'||mode==='inventory')resume();else if(mode==='journal')setMode(journalReturn);else if(mode==='settings')setMode(settingsReturn);return;
    }
    if(e.code==='Tab'&&['playing','journal'].includes(mode)){e.preventDefault();if(e.repeat)return;if(mode==='journal')setMode(journalReturn);else openJournal();return;}
    if(mode!=='playing'||orientationBlocked)return;
    if(['Space','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','ControlLeft','ControlRight'].includes(e.code))e.preventDefault();keys.add(e.code);if(e.repeat)return;
    if(e.code==='KeyE')interact();if(e.code==='KeyF')toggleTorch();if(e.code==='KeyG')offer();if(e.code==='KeyR')ring();if(e.code==='KeyP')pause();
    if(e.code==='KeyC'){touch.crouching=!touch.crouching;touch.running=false;refreshTouch();}
    if(/^Digit[1-6]$/.test(e.code)){selected=ITEM_ORDER[Number(e.code.slice(-1))-1];refreshHUD();}
  });
  addEventListener('keyup',e=>keys.delete(e.code));
  addEventListener('blur',()=>{keys.clear();resetPads();if(mode==='playing')pause();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&mode==='playing')pause();});
  let wasLocked=false,drag=null;
  document.addEventListener('pointerlockchange',()=>{const locked=document.pointerLockElement===canvas;if(wasLocked&&!locked&&mode==='playing')pause();wasLocked=locked;$('#look-hint').hidden=locked;});
  document.addEventListener('pointerlockerror',()=>{$('#look-hint').hidden=false;});
  const look=(x,y)=>{player.yaw-=x*.0022*settings.sensitivity;player.pitch=clamp(player.pitch-y*.0022*settings.sensitivity,-1.25,1.1);updateCamera(0);};
  document.addEventListener('mousemove',e=>{if(mode==='playing'&&document.pointerLockElement===canvas)look(e.movementX,e.movementY);});
  canvas.addEventListener('pointerdown',e=>{
    if(mode!=='playing')return;
    if(document.pointerLockElement===canvas){if(e.button===0)offer();return;}
    if(e.pointerType==='touch')return;
    drag={id:e.pointerId,x:e.clientX,y:e.clientY,moved:false,touch:e.pointerType==='touch'};canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.id||mode!=='playing')return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>1)drag.moved=true;look(dx,dy);drag.x=e.clientX;drag.y=e.clientY;});
  canvas.addEventListener('pointerup',()=>{if(drag&&!drag.moved&&!drag.touch)requestLook();drag=null;});canvas.addEventListener('pointercancel',()=>drag=null);
  const canUse=()=>mode==='playing'&&!orientationBlocked;
  const resetMove=attachTouchPad($('#joystick'),canUse,(x,z)=>{touch.x=x;touch.z=z;});
  const resetLook=attachTouchPad($('#look-pad'),canUse,(x,y)=>{touch.lookX=x;touch.lookY=y;});
  resetPads=()=>{resetMove();resetLook();};
  coarsePointer.addEventListener('change',updateOrientation);portraitScreen.addEventListener('change',updateOrientation);
  updateOrientation();
  // Keep keyboard focus inside active modal dialogs, with Escape as the exit.
  document.addEventListener('keydown',e=>{if(e.code!=='Tab'||mode==='playing')return;const dialog=document.querySelector('.overlay:not([hidden])');if(!dialog)return;const elements=[...dialog.querySelectorAll('button,input,select,summary,a[href]')].filter(x=>!x.disabled&&x.offsetParent!==null);if(!elements.length)return;const first=elements[0],last=elements.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});
}
async function boot(){
  try{
    renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    scene=new THREE.Scene();scene.background=new THREE.Color(0x172727);scene.fog=new THREE.FogExp2(0x172727,.023);
    camera=new THREE.PerspectiveCamera(68,innerWidth/innerHeight,.045,170);scene.add(camera);
    scene.add(new THREE.HemisphereLight(0xa2bfc0,0x434631,1.35));moon=new THREE.DirectionalLight(0xb9ced0,2.7);moon.position.set(-24,42,-35);moon.castShadow=true;moon.shadow.mapSize.set(1024,1024);Object.assign(moon.shadow.camera,{left:-32,right:32,top:32,bottom:-32,near:.5,far:100});moon.shadow.normalBias=.035;scene.add(moon);
    flashlight=new THREE.SpotLight(0xffefc4,42,22,.39,.65,1.4);flashlight.position.set(.18,-.12,0);flashlight.target.position.set(.05,-.08,-8);camera.add(flashlight,flashlight.target);
    world=createVillage(scene);nav=new VillageNavigation(world.obstacles);wireUI();wireInput();applySettings();
    controller=await KuchikaguraController.load();controller.showReactionProps=false;controller.model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});scene.add(controller.model);
    enemy=new PursuerAI(nav,{difficulty:settings.difficulty,onState:state=>{
      controller.play(state);setReactionProp(['lament','feed','ritual'].includes(state)?enemy?.reactionItem:null);
      if(mode==='playing'&&state==='chase')subtitle('足音が、こちらへ近づいてくる。',3);
      else if(mode==='playing'&&state==='search'&&lastState==='chase')subtitle('追う足音が止まった。灯りを消し、身を隠そう。',4);lastState=state;
    },onCatch:()=>finish(false),onMemory:()=>{toast(`手向けた思い出 — ${progress.memories.length} / 3`);save();}});
    controller.model.position.set(0,0,-19);
    ready=true;document.body.dataset.ready='true';$('#start').disabled=false;$('#loading-status').textContent='探索の目安 10〜15分 · 自動保存';updateContinue();refreshHUD();
    addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);updateOrientation();});
    const clock=new THREE.Clock();
    renderer.setAnimationLoop(()=>{
      const dt=Math.min(clock.getDelta(),.05);renderTime+=dt;
      if(mode==='playing'){if(!testMode)simulate(dt);}
      else if(mode==='title'||mode==='settings'&&!started){camera.position.set(5.5,2.3,26);camera.lookAt(-1+Math.sin(renderTime*.06)*.4,1.8,-8);flashlight.visible=false;controller.update(dt);}
      world.update(renderTime);renderer.render(scene,camera);
    });
    if(testMode)window.kuchiGame={get mode(){return mode;},player,enemy,nav,world,controller,renderer,camera,audio,
      snapshot:()=>structuredClone({mode,progress,player,enemy:{state:enemy.state,position:enemy.position,timer:enemy.timer},stamina,bellCooldown,focused:focused?.id,projectiles:projectiles.length,dropped:dropped.map(d=>({id:d.id,item:d.item,x:d.x,z:d.z}))}),
      advance(seconds){for(let t=0;t<seconds;t+=.05)simulate(Math.min(.05,seconds-t));renderer.render(scene,camera);},
      teleport(x,z,yaw=0,pitch=0){if(!nav.free({x,z}))throw new Error('Test position intersects scenery');Object.assign(player,{x,z,yaw,pitch});updateCamera(0);findFocus();},
      aim(id){const e=[...world.entities,...dropped].find(e=>e.id===id);if(!e)throw new Error('Unknown target '+id);player.yaw=Math.atan2(-(e.x-player.x),-(e.z-player.z));player.pitch=Math.atan2(e.y+.12-camera.position.y,distance(e,player));updateCamera(0);findFocus();},
      get progress(){return progress;},
    };
  }catch(e){showError(e);}
}
boot();
