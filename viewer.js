import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {KuchikaguraController, STATES} from './character-controller.js';

const $ = selector => document.querySelector(selector);
const descriptions = {
  idle:['待機','息を潜め、首を傾けたままわずかに揺れる。'],
  walk:['巡回','長い腕を垂らし、村の道を静かに歩く。'],
  alert:['警戒','物音に立ち止まり、人の気配へ首を向ける。'],
  chase:['追跡','上体を傾け、長い腕を振って追いすがる。'],
  search:['捜索','周囲を見回し、片手を伸ばして気配を探る。'],
  lament:['嘆く','記憶の品を拾って見つめ、しゃがみ込んで嘆く。'],
  feed:['食らう','食べ物を急いで拾い、震える手で乱暴に口へ運ぶ。'],
  ritual:['神楽','鈴の音に足を止め、ゆがんだ祭祀の動作を繰り返す。']
};
const canvas=$('#stage');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.25;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();
scene.background=new THREE.Color(0x101f1c);
scene.fog=new THREE.FogExp2(0x101f1c,.067);
const camera=new THREE.PerspectiveCamera(38,innerWidth/innerHeight,.05,70);
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;controls.minDistance=1.4;controls.maxDistance=8;
controls.maxPolarAngle=Math.PI*.51;
function resetCamera(){camera.position.set(2.5,1.65,4.6);controls.target.set(.33,1.03,0);controls.update();}
resetCamera();
const hemi=new THREE.HemisphereLight(0xc2d2c0,0x283027,1.1);scene.add(hemi);
const key=new THREE.DirectionalLight(0xdde5cd,3.1);key.position.set(-3,5,4);key.castShadow=true;
key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-3;key.shadow.camera.right=3;key.shadow.camera.top=3;key.shadow.camera.bottom=-3;key.shadow.normalBias=.025;scene.add(key);
const rim=new THREE.DirectionalLight(0x719fa2,1.9);rim.position.set(2,3,-3);scene.add(rim);
const warm=new THREE.PointLight(0xffb878,18,7,2);warm.position.set(-1.5,1.4,1);scene.add(warm);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(60,60),new THREE.MeshStandardMaterial({color:0x1b2920,roughness:1}));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
function box(w,h,d,color,x,y,z){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:.94}));mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);return mesh;}
for(let i=0;i<15;i++){const z=.65-i*.6;box(1.35,.045,.46,0x455147,.025*Math.sin(i*8),.022,z);}
function torii(z,s){for(const x of [-.95,.95])box(.16*s,2.65*s,.16*s,0x4f352a,x*s,1.325*s,z);box(2.6*s,.19*s,.23*s,0x634032,0,2.6*s,z);box(2.3*s,.12*s,.18*s,0x59372b,0,2.25*s,z);}
torii(-3.0,1);torii(-7.3,.9);
for(let i=0;i<24;i++){const x=(i%2 ? 1 : -1)*(2.5+(i%5)*.6),z=-1.5-Math.floor(i/2)*1.2;box(.12,5+(i%4),.12,0x18231c,x,2.5,z);}
for(const x of [-1.6,1.6]){box(.12,.9,.12,0x42473a,x,.45,-1.1);box(.37,.38,.37,0x544c38,x,1.04,-1.1);box(.49,.09,.49,0x302c23,x,1.28,-1.1);const light=new THREE.PointLight(0xe6a566,5,3);light.position.set(x,1.1,-1.1);scene.add(light);}
let controller;
const clock=new THREE.Clock();
const buttons=[...document.querySelectorAll('button[data-state]')];
buttons.forEach(button=>button.disabled=true);
function onState(name){
  buttons.forEach(b=>{const active=b.dataset.state===name;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  $('#state-title').textContent=descriptions[name][0];$('#state-description').textContent=descriptions[name][1];
  $('#timeline').max=controller.duration;
}
try{
  controller=await KuchikaguraController.load();
  controller.model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
  scene.add(controller.model);controller.onStateChange=onState;onState('idle');
  const bounds=new THREE.Box3().setFromObject(controller.model,true),size=bounds.getSize(new THREE.Vector3());
  let triangles=0,meshes=0;
  controller.model.traverse(o=>{if(o.isMesh){meshes++;triangles+=(o.geometry.index?.count ?? o.geometry.attributes.position.count)/3;}});
  $('#stats').textContent=`${Math.round(triangles).toLocaleString()} triangles\n${size.y.toFixed(2)} m / ${meshes} material primitives\n1 × 1024² embedded texture\n8 skeletal animation clips\nIn-place / forward +Z / metres`;
  $('#status').textContent='GLB読込完了';document.body.dataset.ready='true';
  buttons.forEach(button=>{button.disabled=false;button.addEventListener('click',()=>controller.play(button.dataset.state));});
  $('#pause').addEventListener('click',()=>{controller.setPaused(!controller.paused);$('#pause').textContent=controller.paused?'▶':'Ⅱ';$('#pause').setAttribute('aria-label',controller.paused?'再生を再開':'再生を一時停止');});
  $('#timeline').addEventListener('input',()=>{controller.setPaused(true);$('#pause').textContent='▶';controller.seek(Number($('#timeline').value));});
  $('#replay').addEventListener('click',()=>{controller.setPaused(false);$('#pause').textContent='Ⅱ';controller.play(controller.state);});
  $('#speed').addEventListener('change',()=>controller.speed=Number($('#speed').value));
  $('#offer').addEventListener('click',()=>{controller.setPaused(false);$('#pause').textContent='Ⅱ';controller.reactToItem($('#item').value);$('#offering-result').textContent=`${$('#item').selectedOptions[0].textContent} → ${descriptions[controller.state][0]}`;});
  // Reusable controller is also exposed for embedding and browser verification.
  window.kuchiPreview={controller,scene,camera,renderer,states:STATES};
}catch(error){console.error(error);$('#status').textContent='読み込み失敗';$('#load-error').textContent=error.message;$('#missing').hidden=false;}
$('#fog').addEventListener('change',e=>scene.fog=e.target.checked?new THREE.FogExp2(0x101f1c,.067):null);
$('#studio').addEventListener('change',e=>{hemi.intensity=e.target.checked?2.3:1.1;key.intensity=e.target.checked?4:3.1;renderer.toneMappingExposure=e.target.checked?1.5:1.25;});
$('#reset-camera').addEventListener('click',resetCamera);
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
renderer.setAnimationLoop(()=>{const delta=clock.getDelta();if(controller){controller.update(delta);if($('#rotate').checked)controller.model.rotation.y+=delta*.18;$('#timeline').value=controller.action.time;$('#time').textContent=`${controller.action.time.toFixed(1)} / ${controller.duration.toFixed(1)}`;}controls.update();renderer.render(scene,camera);});
