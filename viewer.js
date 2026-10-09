import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {KuchikaguraController, STATES} from './character-controller.js';

const $ = selector => document.querySelector(selector);
const characters = Object.freeze({
  glasses: {label:'眼鏡の追跡者', url:'./assets/models/pursuer_glasses.glb', description:'眼鏡、流れる短髪、白い半袖の制服と緑の首ひも。前傾した姿勢で村を追い歩く。'},
  cropped: {label:'短髪の追跡者', url:'./assets/models/pursuer_cropped.glb', description:'刈り上げた短髪、厚みのある体格、白い半袖の制服と緑の首ひも。低く構え、気配に反応する。'},
  kuchikagura: {label:'旧朽ち神楽', url:'./assets/models/kuchikagura.glb', description:'古い祭祀衣装をまとい、村をさまよう追跡者。手向けたものが、残された記憶を呼び起こす。'}
});
const descriptions = {
  idle:['待機','息を潜め、首を傾けたままわずかに揺れる。'],
  walk:['巡回','腕を垂らし、村の道を静かに歩く。'],
  alert:['警戒','物音に立ち止まり、人の気配へ首を向ける。'],
  chase:['追跡','上体を傾け、腕を振って追いすがる。'],
  search:['捜索','周囲を見回し、片手を伸ばして気配を探る。'],
  lament:['嘆く','記憶の品を拾って見つめ、しゃがみ込んで嘆く。'],
  feed:['食らう','食べ物を急いで拾い、震える手で乱暴に口へ運ぶ。'],
  ritual:['神楽','鈴の音に足を止め、ゆがんだ祭祀の動作を繰り返す。']
};
const canvas=$('#stage');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(38,1,.03,70);
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.minDistance=.38;controls.maxDistance=8;
controls.maxPolarAngle=Math.PI*.51;
let controller=null,character=null,loadGeneration=0;
let modelHeight=2,headPosition=new THREE.Vector3(0,1.7,0);
function resetFacing(){
  $('#rotate').checked=false;
  if(controller){controller.model.rotation.y=0;controller.model.updateMatrixWorld(true);}
}
function setCamera(position,target){
  resetFacing();
  const damping=controls.enableDamping;
  controls.enableDamping=false;controls.update();controls.reset();
  camera.position.copy(position);controls.target.copy(target);controls.update();controls.enableDamping=damping;
}
function resetCamera(){setCamera(new THREE.Vector3(2.4,modelHeight*.71,4.5),new THREE.Vector3(0,modelHeight*.5,0));}
function frontCamera(){setCamera(new THREE.Vector3(0,modelHeight*.6,4.3),new THREE.Vector3(0,modelHeight*.52,0));}
function faceCamera(){
  resetFacing();
  controller?.model.getObjectByName('HEAD_CTRL')?.getWorldPosition(headPosition);
  setCamera(headPosition.clone().add(new THREE.Vector3(0,.02,.86)),headPosition);
}
resetCamera();
function resize(){
  const {width,height}=canvas.getBoundingClientRect();
  camera.aspect=width/Math.max(1,height);camera.updateProjectionMatrix();renderer.setSize(width,height,false);
}
new ResizeObserver(resize).observe(canvas);resize();
const hemi=new THREE.HemisphereLight(0xe6e9ef,0x454b46,2.3);scene.add(hemi);
const key=new THREE.DirectionalLight(0xfff6e6,3.1);key.position.set(-3,5,4);key.castShadow=true;
key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-3;key.shadow.camera.right=3;key.shadow.camera.top=3;key.shadow.camera.bottom=-3;key.shadow.normalBias=.025;scene.add(key);
const rim=new THREE.DirectionalLight(0x9ab9cf,1.9);rim.position.set(2,3,-3);scene.add(rim);
const warm=new THREE.PointLight(0xffb878,18,7,2);warm.position.set(-1.5,1.4,1);scene.add(warm);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(60,60),new THREE.MeshStandardMaterial({color:0x65706b,roughness:1}));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
const village=new THREE.Group();scene.add(village);
function box(w,h,d,color,x,y,z){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:.94}));mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;village.add(mesh);return mesh;}
for(let i=0;i<15;i++){const z=.65-i*.6;box(1.35,.045,.46,0x455147,.025*Math.sin(i*8),.022,z);}
function torii(z,s){for(const x of [-.95,.95])box(.16*s,2.65*s,.16*s,0x4f352a,x*s,1.325*s,z);box(2.6*s,.19*s,.23*s,0x634032,0,2.6*s,z);box(2.3*s,.12*s,.18*s,0x59372b,0,2.25*s,z);}
torii(-3,1);torii(-7.3,.9);
for(let i=0;i<24;i++){const x=(i%2?1:-1)*(2.5+(i%5)*.6),z=-1.5-Math.floor(i/2)*1.2;box(.12,5+(i%4),.12,0x18231c,x,2.5,z);}
for(const x of [-1.6,1.6]){box(.12,.9,.12,0x42473a,x,.45,-1.1);box(.37,.38,.37,0x544c38,x,1.04,-1.1);box(.49,.09,.49,0x302c23,x,1.28,-1.1);const light=new THREE.PointLight(0xe6a566,5,3);light.position.set(x,1.1,-1.1);village.add(light);}
function updateLighting(){
  const studio=$('#studio').checked;
  const background=studio?0x707b78:0x101f1c;
  scene.background=new THREE.Color(background);
  scene.fog=$('#fog').checked?new THREE.FogExp2(background,.067):null;
  village.visible=!studio;
  ground.material.color.setHex(studio?0x65706b:0x1b2920);
  hemi.intensity=studio?2.3:1.1;key.intensity=3.1;
  warm.intensity=studio?0:18;renderer.toneMappingExposure=studio?1.1:1.25;
}
updateLighting();
const buttons=[...document.querySelectorAll('button[data-state]')];
const assetControls=[...buttons,...document.querySelectorAll('#pause,#timeline,#replay,#speed,#offer,#item,#rotate,#front-camera,#face-camera,#reset-camera')];
function enableAssetControls(enabled){assetControls.forEach(control=>control.disabled=!enabled);}
enableAssetControls(false);
function updatePause(){
  $('#pause').textContent=controller?.paused?'▶':'Ⅱ';
  $('#pause').setAttribute('aria-label',controller?.paused?'再生を再開':'再生を一時停止');
}
function onState(name){
  buttons.forEach(b=>{const active=b.dataset.state===name;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  $('#state-title').textContent=descriptions[name][0];$('#state-description').textContent=descriptions[name][1];
  $('#timeline').max=controller.duration;updatePause();
}
function disposeController(old){
  if(!old)return;
  old.onStateChange=()=>{};old.mixer.stopAllAction();old.mixer.uncacheRoot(old.model);
  scene.remove(old.model);
  const geometries=new Set(),materials=new Set(),textures=new Set(),skeletons=new Set();
  old.model.traverse(object=>{
    if(!object.isMesh)return;
    geometries.add(object.geometry);
    for(const material of (Array.isArray(object.material)?object.material:[object.material])){
      if(!material)continue;
      materials.add(material);
      for(const value of Object.values(material))if(value?.isTexture)textures.add(value);
    }
    if(object.skeleton)skeletons.add(object.skeleton);
  });
  skeletons.forEach(skeleton=>skeleton.dispose());
  geometries.forEach(geometry=>geometry.dispose());materials.forEach(material=>material.dispose());
  textures.forEach(texture=>{texture.dispose();texture.source?.data?.close?.();});
}
function showStats(){
  const bounds=new THREE.Box3().setFromObject(controller.model,true);
  modelHeight=bounds.getSize(new THREE.Vector3()).y;
  let triangles=0,meshes=0;
  const textures=new Set(),bones=new Set();
  controller.model.traverse(object=>{
    if(object.isBone)bones.add(object);
    if(!object.isMesh)return;
    meshes++;triangles+=(object.geometry.index?.count??object.geometry.attributes.position.count)/3;
    for(const material of (Array.isArray(object.material)?object.material:[object.material]))
      if(material?.map)textures.add(material.map);
  });
  const sizes=[...textures].map(texture=>{
    const image=texture.image;
    return `${image?.width??image?.naturalWidth??'?'} × ${image?.height??image?.naturalHeight??'?'}`;
  });
  $('#stats').textContent=`${Math.round(triangles).toLocaleString()} triangles\n${modelHeight.toFixed(2)} m / ${meshes} material primitives\n${textures.size} embedded texture${textures.size===1?'':'s'} (${sizes.join(', ')})\n${bones.size} bones / ${controller.clips.size} skeletal animation clips\nIn-place / forward +Z / metres`;
}
async function selectCharacter(id){
  if(!characters[id])id='glasses';
  const generation=++loadGeneration;
  character=id;$('#character').value=id;document.body.dataset.ready='false';
  document.body.dataset.character=id;$('#missing').hidden=true;$('#stats').textContent='読み込み中';
  $('#status').textContent=`${characters[id].label}を読み込み中`;
  $('#character-description').textContent=characters[id].description;
  $('#character-caption').textContent=characters[id].label;
  $('#stage').setAttribute('aria-label',`${characters[id].label}の3Dプレビュー`);
  enableAssetControls(false);disposeController(controller);controller=null;
  buttons.forEach(button=>{button.classList.remove('active');button.setAttribute('aria-pressed','false');});
  $('#offering-result').textContent='記憶の品、食べ物、あるいは鈴の音。';$('#rotate').checked=false;
  const url=new URL(location.href);url.searchParams.set('character',id);history.replaceState(null,'',url);
  $('#studio').checked=id!=='kuchikagura';$('#fog').checked=id==='kuchikagura';updateLighting();
  try{
    const loaded=await KuchikaguraController.load(characters[id].url);
    if(generation!==loadGeneration){disposeController(loaded);return false;}
    controller=loaded;
    controller.model.traverse(object=>{if(object.isMesh){object.castShadow=true;object.receiveShadow=true;}});
    scene.add(controller.model);controller.onStateChange=onState;controller.speed=Number($('#speed').value);
    onState('idle');showStats();resetCamera();
    $('#status').textContent=`${characters[id].label} — GLB読込完了`;
    enableAssetControls(true);document.body.dataset.ready='true';return true;
  }catch(error){
    if(generation!==loadGeneration)return false;
    console.error(error);$('#status').textContent='読み込み失敗';$('#load-error').textContent=error.message;
    $('#missing').hidden=false;document.body.dataset.ready='error';return false;
  }
}
buttons.forEach(button=>button.addEventListener('click',()=>controller?.play(button.dataset.state)));
$('#character').addEventListener('change',event=>selectCharacter(event.target.value));
$('#pause').addEventListener('click',()=>{if(controller){controller.setPaused(!controller.paused);updatePause();}});
$('#timeline').addEventListener('input',()=>{if(controller){controller.setPaused(true);updatePause();controller.seek(Number($('#timeline').value));}});
$('#replay').addEventListener('click',()=>{if(controller){controller.setPaused(false);controller.play(controller.state);}});
$('#speed').addEventListener('change',()=>{if(controller)controller.speed=Number($('#speed').value);});
$('#offer').addEventListener('click',()=>{
  if(!controller)return;
  controller.setPaused(false);controller.reactToItem($('#item').value);
  $('#offering-result').textContent=`${$('#item').selectedOptions[0].textContent} → ${descriptions[controller.state][0]}`;
});
$('#fog').addEventListener('change',updateLighting);$('#studio').addEventListener('change',updateLighting);
$('#front-camera').addEventListener('click',frontCamera);$('#face-camera').addEventListener('click',faceCamera);
$('#reset-camera').addEventListener('click',resetCamera);
// A getter keeps embedding clients on the active model after every selection.
const previewAPI={get controller(){return controller;},get character(){return character;},scene,camera,renderer,controls,states:STATES,characters,selectCharacter};
window.kuchiPreview=previewAPI;window.kuchiPreviewAPI=previewAPI;
const clock=new THREE.Clock();
renderer.setAnimationLoop(()=>{
  const delta=clock.getDelta();
  if(controller){
    controller.update(delta);if($('#rotate').checked)controller.model.rotation.y+=delta*.18;
    $('#timeline').value=controller.action.time;$('#time').textContent=`${controller.action.time.toFixed(1)} / ${controller.duration.toFixed(1)}`;
  }
  controls.update();renderer.render(scene,camera);
});
selectCharacter(new URLSearchParams(location.search).get('character')||'glasses');
