import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

function random(seed=7281){return ()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};}
const rng=random();
const materials={};
function surface(kind,color){
  const canvas=document.createElement('canvas');canvas.width=canvas.height=512;
  const c=canvas.getContext('2d');c.fillStyle=color;c.fillRect(0,0,512,512);
  for(let i=0;i<12000;i++){
    const v=Math.floor(rng()*50);c.fillStyle=`rgba(${v},${v},${v},${rng()*.17})`;
    c.fillRect(rng()*512,rng()*512,kind==='wood'?1:2,kind==='wood'?rng()*80:2);
  }
  c.strokeStyle='rgba(8,12,9,.35)';c.lineWidth=2;
  if(kind==='wood')for(let x=0;x<512;x+=64){c.beginPath();c.moveTo(x,0);c.lineTo(x,512);c.stroke();}
  if(kind==='roof')for(let y=0;y<512;y+=40){c.beginPath();c.moveTo(0,y);c.lineTo(512,y);c.stroke();for(let x=0;x<512;x+=64){c.beginPath();c.moveTo(x+(y%80?32:0),y);c.lineTo(x+(y%80?32:0),y+40);c.stroke();}}
  if(kind==='stone')for(let i=0;i<40;i++){c.beginPath();let x=rng()*512,y=rng()*512;c.moveTo(x,y);c.lineTo(x+45,y+25);c.lineTo(x+26,y+62);c.stroke();}
  const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;map.wrapS=map.wrapT=THREE.RepeatWrapping;map.anisotropy=4;
  return new THREE.MeshStandardMaterial({map,roughness:.94});
}
function writing(lines){
  const canvas=document.createElement('canvas');canvas.width=256;canvas.height=512;const c=canvas.getContext('2d');
  c.fillStyle='#cfbba0';c.fillRect(0,0,256,512);c.fillStyle='#473a31';c.textAlign='center';c.font='46px "Noto Serif CJK JP",serif';
  [...lines].forEach((ch,i)=>c.fillText(ch,128,95+i*90));
  const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;return tex;
}
export function makeOffering(type){
  const g=new THREE.Group(),ivory=new THREE.MeshStandardMaterial({color:0xd6cbb6,roughness:.9}),red=new THREE.MeshStandardMaterial({color:0x864634,roughness:.8});
  const add=(geo,mat,x=0,y=0,z=0)=>{const m=new THREE.Mesh(geo,mat);m.position.set(x,y,z);g.add(m);return m;};
  if(type==='photograph'){
    add(new THREE.BoxGeometry(.22,.013,.29),ivory);
    const c=document.createElement('canvas');c.width=128;c.height=180;const ctx=c.getContext('2d');ctx.fillStyle='#817b63';ctx.fillRect(0,0,128,180);
    ctx.fillStyle='#393e36';ctx.beginPath();ctx.moveTo(0,130);ctx.lineTo(30,52);ctx.lineTo(70,112);ctx.lineTo(128,48);ctx.lineTo(128,180);ctx.lineTo(0,180);ctx.fill();
    ctx.fillStyle='#b6ac8b';ctx.beginPath();ctx.arc(48,83,13,0,Math.PI*2);ctx.fill();ctx.fillRect(34,100,30,54);ctx.beginPath();ctx.arc(84,116,8,0,Math.PI*2);ctx.fill();ctx.fillRect(74,126,20,38);
    const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;const p=add(new THREE.PlaneGeometry(.19,.25),new THREE.MeshBasicMaterial({map:tex}));p.rotation.x=-Math.PI/2;p.position.y=.008;
  }else if(type==='hairpin'){
    const stem=add(new THREE.CylinderGeometry(.012,.012,.3,6),ivory);stem.rotation.z=Math.PI/2;
    for(let i=0;i<5;i++)add(new THREE.SphereGeometry(.033,6,4),red,-.14+Math.cos(i*1.256)*.03,.025,Math.sin(i*1.256)*.03);
  }else if(type==='child_sandals'){
    for(const x of [-.09,.09]){const m=add(new THREE.BoxGeometry(.11,.035,.22),ivory,x);const strap=add(new THREE.TorusGeometry(.04,.012,4,8,Math.PI),red,x,.03);strap.rotation.x=-Math.PI/2;m.rotation.y=x;}
  }else if(type==='onigiri'){
    const shape=new THREE.Shape();shape.moveTo(-.11,0);shape.lineTo(0,.19);shape.lineTo(.11,0);shape.closePath();
    const m=add(new THREE.ExtrudeGeometry(shape,{depth:.1,bevelEnabled:true,bevelSize:.02,bevelThickness:.015,bevelSegments:1,steps:1}),ivory,0,0,-.05);
    add(new THREE.BoxGeometry(.095,.09,.105),new THREE.MeshStandardMaterial({color:0x17271a}),0,.045);
    m.rotation.x=-.2;
  }else if(type==='dango'){
    const stick=add(new THREE.CylinderGeometry(.009,.009,.38,5),ivory);stick.rotation.z=Math.PI/2;
    [0xe2b3a4,0xd7cfaa,0x8ba479].forEach((color,i)=>add(new THREE.SphereGeometry(.052,8,6),new THREE.MeshStandardMaterial({color}),-.08+i*.11,.06));
  }else if(type==='kagura_bell'){
    add(new THREE.CylinderGeometry(.016,.022,.29,8),red,0,.14);
    const brass=new THREE.MeshStandardMaterial({color:0xad9a5d,metalness:.65,roughness:.3});
    for(let i=0;i<6;i++)add(new THREE.SphereGeometry(.038,8,6),brass,Math.cos(i*1.047)*.065,.29,Math.sin(i*1.047)*.065);
  }
  return g;
}
export function createVillage(scene){
  const obstacles=[],entities=[],animated=[],lights=[],landmarks=[];
  materials.wood=surface('wood','#504538');materials.darkWood=surface('wood','#322e28');materials.roof=surface('roof','#333c3b');materials.stone=surface('stone','#697064');materials.earth=surface('earth','#3e4431');
  materials.paper=new THREE.MeshStandardMaterial({color:0xc6ba97,roughness:1,side:THREE.DoubleSide});
  materials.red=new THREE.MeshStandardMaterial({color:0x6d2e23,roughness:.85});
  materials.window=new THREE.MeshStandardMaterial({color:0x998366,emissive:0xd19a50,emissiveIntensity:.28,roughness:.85});
  const glow=new THREE.MeshBasicMaterial({color:0xe8b878}),grassmat=new THREE.MeshStandardMaterial({color:0x354334,roughness:1,side:THREE.DoubleSide});
  function mesh(geo,mat,x,y,z,parent=scene){const o=new THREE.Mesh(geo,mat);o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;}
  function box(w,h,d,mat,x,y,z,parent=scene){return mesh(new THREE.BoxGeometry(w,h,d),mat,x,y,z,parent);}
  function block(x,z,w,d,height=3){obstacles.push({minX:x-w/2,maxX:x+w/2,minZ:z-d/2,maxZ:z+d/2,height});}
  function localBlock(group,x,z,w,d){const p=new THREE.Vector3(x,0,z).applyMatrix4(group.matrixWorld);const rotated=Math.abs(Math.sin(group.rotation.y))>.5;block(p.x,p.z,rotated?d:w,rotated?w:d);}
  const ground=mesh(new THREE.PlaneGeometry(240,240),materials.earth,0,-.05,0);ground.rotation.x=-Math.PI/2;ground.material.map.repeat.set(70,70);
  // Irregular flagstones share geometry and material to keep the scene light.
  const stones=[];
  for(let z=33;z>-30;z-=.82)for(let x=-1.2;x<1.5;x+=.8)stones.push([x+(rng()-.5)*.18,.004,z+(rng()-.5)*.16,.67+rng()*.13,.73+rng()*.13]);
  for(const z of [16,11,-7])for(let x=-13;x<14;x+=.85)stones.push([x,.004,z+(rng()-.5)*.1,.73,.7]);
  const stoneMesh=new THREE.InstancedMesh(new THREE.BoxGeometry(1,.06,1),materials.stone,stones.length),dummy=new THREE.Object3D();
  stones.forEach((s,i)=>{dummy.position.set(s[0],s[1],s[2]);dummy.scale.set(s[3],1,s[4]);dummy.rotation.y=(rng()-.5)*.14;dummy.updateMatrix();stoneMesh.setMatrixAt(i,dummy.matrix);stoneMesh.setColorAt(i,new THREE.Color().setRGB(.5+rng()*.18,.54+rng()*.18,.48+rng()*.18));});stoneMesh.receiveShadow=true;scene.add(stoneMesh);
  function roof(group,w,d,height=2){
    const shape=new THREE.Shape();shape.moveTo(-w/2,0);shape.lineTo(0,height);shape.lineTo(w/2,0);shape.closePath();
    const top=mesh(new THREE.ExtrudeGeometry(shape,{depth:d,bevelEnabled:false}),materials.roof,0,3,-d/2,group);
    box(w+.3,.12,.3,materials.darkWood,0,3,d/2,group);box(w+.3,.12,.3,materials.darkWood,0,3,-d/2,group);
    box(.16,.16,d+.2,materials.darkWood,0,3+height,0,group);return top;
  }
  function house(x,z,rotation,label,shrine=false){
    const g=new THREE.Group();g.position.set(x,0,z);g.rotation.y=rotation;scene.add(g);g.updateMatrixWorld(true);
    const w=shrine?9:7,d=6.5;
    box(w,.16,d,materials.wood,0,.08,0,g);roof(g,w+1,d+1.4,shrine?2.6:1.9);
    box(w,2.9,.18,materials.darkWood,0,1.55,-d/2,g);localBlock(g,0,-d/2,w,.18);
    for(const side of [-1,1]){box(.18,2.9,d,materials.wood,side*w/2,1.55,0,g);localBlock(g,side*w/2,0,.18,d);}
    for(const side of [-1,1]){
      const span=(w-1.7)/2,xx=side*(.85+span/2);
      box(span,2.6,.18,materials.wood,xx,1.4,d/2,g);localBlock(g,xx,d/2,span,.18);
      box(span-.5,1.3,.035,materials.window,xx,1.7,d/2+.1,g);
      for(let i=-2;i<=2;i++)box(.045,1.32,.055,materials.darkWood,xx+i*(span-.5)/5,1.7,d/2+.14,g);
      box(span-.5,.04,.05,materials.darkWood,xx,1.7,d/2+.14,g);
    }
    box(1.7,.33,.2,materials.darkWood,0,2.8,d/2,g);
    box(w+.6,.08,1.2,materials.wood,0,.12,d/2+.55,g);
    for(let xx=-w/2;xx<=w/2;xx+=w/2)for(const zz of [-d/2,d/2])box(.17,3.0,.17,materials.darkWood,xx,1.5,zz,g);
    const tatami=new THREE.MeshStandardMaterial({color:0x7a7756,roughness:1});
    for(let xx=-2;xx<3;xx+=1.5)for(let zz=-2;zz<2;zz+=2)box(1.43,.02,1.93,tatami,xx,.18,zz,g);
    box(1.4,.46,.85,materials.darkWood,-1,.4,-.2,g);
    const sign=mesh(new THREE.PlaneGeometry(.38,.85),new THREE.MeshStandardMaterial({map:writing(label),roughness:1}),w/2-.42,1.5,d/2+.15,g);
    const light=new THREE.PointLight(0xe3b277,9,9,2);light.position.set(x,1.9,z);scene.add(light);lights.push(light);
    landmarks.push({name:label,x,z});return g;
  }
  house(-10,11,Math.PI/2,'旧家');house(10,16,-Math.PI/2,'炊事');house(11,-7,-Math.PI/2,'穀蔵');house(0,-27,0,'奉納',true);
  // Closed silhouettes flank the playable houses.
  for(const [x,z] of [[-12,24],[12,3],[-12,-20]]){
    const g=new THREE.Group();g.position.set(x,0,z);scene.add(g);box(7,3,6,materials.darkWood,0,1.5,0,g);roof(g,8,7);block(x,z,7,6);
    for(let i=-1;i<=1;i++)box(.8,1.1,.07,materials.window,i*1.7,1.6,3.03,g);
  }
  function torii(z,w=6,h=5){
    for(const x of [-w/2,w/2]){mesh(new THREE.CylinderGeometry(.2,.26,h,10),materials.red,x,h/2,z);block(x,z,.5,.5);mesh(new THREE.CylinderGeometry(.32,.38,.42,8),materials.stone,x,.21,z);}
    box(w+1.5,.32,.45,materials.red,0,h,z);box(w+.6,.19,.35,materials.darkWood,0,h-.85,z);box(.15,.72,.15,materials.red,0,h-.45,z);
    const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(-w/2,h-.95,z),new THREE.Vector3(0,h-1.28,z),new THREE.Vector3(w/2,h-.95,z)]);
    mesh(new THREE.TubeGeometry(curve,12,.045,5,false),materials.wood,0,0,0);
    for(const x of [-1.5,-.5,.5,1.5]){const s=mesh(new THREE.PlaneGeometry(.14,.4),materials.paper,x,h-1.52,z);s.rotation.z=x*.12;}
  }
  torii(28.2,6,4.9);torii(-20.5,5.5,4.8);
  function lantern(x,z,lit=true){
    box(.32,.8,.32,materials.stone,x,.4,z);box(.7,.16,.7,materials.stone,x,.86,z);
    for(const dx of [-.24,.24])for(const dz of [-.24,.24])box(.08,.66,.08,materials.wood,x+dx,1.25,z+dz);
    box(.48,.43,.49,lit?glow:materials.paper,x,1.27,z);
    const cap=mesh(new THREE.ConeGeometry(.66,.35,4),materials.stone,x,1.75,z);cap.rotation.y=Math.PI/4;
    block(x,z,.68,.68,1.8);
    if(lit){const light=new THREE.PointLight(0xffb567,11,8.5,2);light.position.set(x,1.45,z);scene.add(light);lights.push(light);}
  }
  for(const [x,z] of [[-3.7,25],[3.7,13],[-3.7,1],[3.7,-11],[-3.7,-22],[3.7,-22]])lantern(x,z);
  // The well is a stone ring, rather than a solid cylinder.
  const well=new THREE.Group();well.position.set(-8,0,-8);scene.add(well);
  const ring=mesh(new THREE.TorusGeometry(1.1,.25,6,16),materials.stone,0,.65,0,well);ring.rotation.x=Math.PI/2;
  for(let i=0;i<14;i++){const a=i*Math.PI*2/14;box(.48,.6,.42,materials.stone,Math.sin(a),.3,Math.cos(a),well);}
  for(const x of [-1.5,1.5])box(.16,2.7,.16,materials.wood,x,1.35,0,well);
  box(3.5,.16,.2,materials.wood,0,2.7,0,well);const rope=mesh(new THREE.CylinderGeometry(.025,.025,2.1,5),materials.wood,0,1.6,0,well);
  const water=mesh(new THREE.CircleGeometry(.89,24),new THREE.MeshStandardMaterial({color:0x182e29,metalness:.6,roughness:.17}),0,.07,0,well);water.rotation.x=-Math.PI/2;block(-8,-8,2.5,2.5,.9);landmarks.push({name:'井戸',x:-8,z:-8});
  // Boundary fences allow an unobstructed path through the village.
  for(const side of [-1,1])for(let z=-30;z<35;z+=2.2){box(.12,1.1,.12,materials.wood,side*22,.55,z);box(.08,.1,2.2,materials.wood,side*22,.4,z);box(.08,.1,2.2,materials.wood,side*22,.85,z);}
  for(const x of [-14,14]){box(22,2.5,.32,materials.darkWood,x,1.25,33.9);block(x,33.9,22,.32);}
  box(5.6,2.6,.2,materials.darkWood,0,1.3,33.85);block(0,33.85,5.6,.2);
  const gate=box(4.6,2.3,.04,materials.wood,0,1.3,33.69);
  for(let x=-2;x<2.4;x+=.35)box(.05,2.3,.06,materials.darkWood,x,1.3,33.6);
  // Cedar trunks, crowns and ground plants are instanced.
  const treeCount=200,trunks=new THREE.InstancedMesh(new THREE.CylinderGeometry(.12,.29,1,6),materials.darkWood,treeCount),crowns=new THREE.InstancedMesh(new THREE.ConeGeometry(1,1,7),new THREE.MeshStandardMaterial({color:0x263e32,roughness:1}),treeCount*3);
  for(let i=0;i<treeCount;i++){
    const side=i%2?1:-1,x=side*(25+rng()*28),z=-55+rng()*112,h=8+rng()*9;
    dummy.position.set(x,h/2,z);dummy.scale.set(1,h,1);dummy.rotation.set(0,rng()*Math.PI,0);dummy.updateMatrix();trunks.setMatrixAt(i,dummy.matrix);
    for(let j=0;j<3;j++){dummy.position.set(x,h*(.43+j*.18),z);dummy.scale.set(3.5-j*.7,6-j,3.5-j*.7);dummy.updateMatrix();crowns.setMatrixAt(i*3+j,dummy.matrix);}
  }scene.add(trunks,crowns);
  const bladeGeometry=new THREE.BufferGeometry();
  bladeGeometry.setAttribute('position',new THREE.Float32BufferAttribute([-.09,0,0,-.02,.5,.015,.015,0,0, .01,0,.02,.08,.35,.025,.055,0,.02, -.05,0,-.01,-.12,.3,-.03,-.025,0,-.01],3));bladeGeometry.computeVertexNormals();
  const grass=new THREE.InstancedMesh(bladeGeometry,grassmat,800);
  const footprints=[[-10,11,7,7],[10,16,7,7],[11,-7,7,7],[0,-27,10,7],[-12,24,7,6],[12,3,7,6],[-12,-20,7,6]];
  for(let i=0;i<800;i++){
    let x,z;do{x=(rng()-.5)*42;z=(rng()-.5)*65;}while(Math.abs(x)<2.1||footprints.some(([cx,cz,w,d])=>Math.abs(x-cx)<w/2+.5&&Math.abs(z-cz)<d/2+.5));
    dummy.position.set(x,.05,z);dummy.scale.setScalar(.5+rng());dummy.rotation.set(0,rng()*Math.PI,0);dummy.updateMatrix();grass.setMatrixAt(i,dummy.matrix);
  }scene.add(grass);
  for(let i=0;i<16;i++){const m=mesh(new THREE.ConeGeometry(20+rng()*25,18+rng()*28,5),new THREE.MeshBasicMaterial({color:0x192a2b}),Math.sin(i*.65)*92,7,-64-Math.cos(i*.65)*14);m.rotation.y=rng();}
  // Moon and a sparse star field remain visible above the mist.
  mesh(new THREE.SphereGeometry(2.3,20,16),new THREE.MeshBasicMaterial({color:0xcecdb5,fog:false}),-29,49,-80);
  const starPositions=[];for(let i=0;i<350;i++)starPositions.push((rng()-.5)*230,40+rng()*60,(rng()-.5)*220);
  const starGeo=new THREE.BufferGeometry();starGeo.setAttribute('position',new THREE.Float32BufferAttribute(starPositions,3));scene.add(new THREE.Points(starGeo,new THREE.PointsMaterial({color:0xa5b6b2,size:.15,fog:false,transparent:true,opacity:.55})));
  function entity(id,type,x,y,z,data={}){
    const g=new THREE.Group();g.position.set(x,y,z);scene.add(g);
    const e={id,type,x,y,z,object:g,...data};entities.push(e);
    if(type==='item')g.add(makeOffering(data.item));
    if(type==='seal'){
      const p=mesh(new THREE.PlaneGeometry(.22,.45),new THREE.MeshStandardMaterial({map:writing('鎮魂'),side:THREE.DoubleSide,emissive:0x695322,emissiveIntensity:.18}),0,.06,0,g);p.rotation.x=-Math.PI/2;
      box(.26,.015,.49,materials.wood,0,.01,0,g);
    }
    if(type==='note'){const p=mesh(new THREE.PlaneGeometry(.35,.26),new THREE.MeshStandardMaterial({map:writing('覚書'),side:THREE.DoubleSide}),0,.02,0,g);p.rotation.x=-Math.PI/2;}
    if(['item','seal','note'].includes(type)){
      const halo=mesh(new THREE.TorusGeometry(.21,.012,4,20),new THREE.MeshBasicMaterial({color:0xd4ba7a,transparent:true,opacity:.48}),0,.3,0,g);halo.rotation.x=-Math.PI/2;halo.castShadow=false;animated.push({halo,base:.3});
    }
    return e;
  }
  // A low roadside offering table introduces the two survival tools.
  box(1.4,.65,.65,materials.wood,2.7,.325,29.5);block(2.7,29.5,1.4,.65,.7);
  entity('bell','item',2.4,.67,29.5,{item:'kagura_bell'});entity('rice_start','item',3,.67,29.5,{item:'onigiri',amount:2});
  entity('note_village','note',1.9,.08,31,{note:'village'});
  entity('photo','item',-11,.65,10.8,{item:'photograph'});
  entity('seal_house','seal',-12,.2,9.1,{place:'旧家'});entity('note_diary','note',-11,.65,11.3,{note:'diary'});
  entity('rice_kitchen','item',9,.65,16,{item:'onigiri',amount:2});entity('dango_kitchen','item',10,.2,14,{item:'dango',amount:2});entity('note_food','note',9,.65,16.5,{note:'food'});
  entity('hairpin','item',-9.4,.09,-5.9,{item:'hairpin'});entity('seal_well','seal',-8,.09,-5.9,{place:'井戸'});
  entity('sandals','item',10,.2,-8.8,{item:'child_sandals'});entity('seal_store','seal',12,.2,-8.8,{place:'蔵'});
  box(1.8,.78,.9,materials.red,0,.5,-28);block(0,-28,1.8,.9,.9);
  entity('altar','altar',0,.9,-27.5);entity('note_ritual','note',-1.1,.2,-25.5,{note:'ritual'});
  const keyEntity=entity('boundary_key','key',.2,.94,-27.7);keyEntity.object.visible=false;
  const brass=new THREE.MeshStandardMaterial({color:0xceb777,metalness:.7,roughness:.4});const keyring=mesh(new THREE.TorusGeometry(.065,.012,5,12),brass,0,0,0,keyEntity.object);box(.025,.014,.16,brass,0,0,.1,keyEntity.object);box(.07,.014,.025,brass,.025,0,.15,keyEntity.object);keyring.rotation.x=-Math.PI/2;
  for(const x of [-.69,.69]){
    mesh(new THREE.CylinderGeometry(.045,.05,.24,8),materials.paper,x,1.01,-28);
    mesh(new THREE.SphereGeometry(.018,6,4),glow,x,1.15,-28);
    mesh(new THREE.CylinderGeometry(.09,.055,.05,8),brass,x,.9,-28);
  }
  mesh(new THREE.SphereGeometry(.08,8,6),materials.paper,-.35,.98,-28.15);
  mesh(new THREE.CylinderGeometry(.034,.045,.1,8),materials.paper,-.35,1.06,-28.15);
  entity('gate','gate',0,1.2,33.5,{object:gate});
  const motesGeo=new THREE.BufferGeometry(),motes=[];for(let i=0;i<80;i++)motes.push((rng()-.5)*35,.5+rng()*3,(rng()-.5)*55);
  motesGeo.setAttribute('position',new THREE.Float32BufferAttribute(motes,3));const moteCloud=new THREE.Points(motesGeo,new THREE.PointsMaterial({color:0x98a88a,size:.035,transparent:true,opacity:.6}));scene.add(moteCloud);
  // Batch static architecture by material. Pickups and moving pieces stay separate.
  scene.updateMatrixWorld(true);
  const liveRoots=new Set(entities.map(e=>e.object)),batches=new Map();
  scene.traverse(o=>{
    if(!o.isMesh||o.isInstancedMesh||Array.isArray(o.material))return;
    let p=o;while(p){if(liveRoots.has(p))return;p=p.parent;}
    if(!batches.has(o.material))batches.set(o.material,[]);batches.get(o.material).push(o);
  });
  for(const [mat,objects] of batches){
    const geometries=objects.map(o=>o.geometry.clone().applyMatrix4(o.matrixWorld));
    const merged=mergeGeometries(geometries,false);
    if(merged){const batch=new THREE.Mesh(merged,mat);batch.castShadow=true;batch.receiveShadow=true;scene.add(batch);for(const o of objects)o.removeFromParent();}
    geometries.forEach(g=>g.dispose());
  }
  return {obstacles,entities,landmarks,lights,materials,
    update(t){for(const a of animated){a.halo.position.y=a.base+Math.sin(t*1.8+a.halo.parent.position.x)*.035;a.halo.material.opacity=.32+Math.sin(t*2)*.1;}moteCloud.rotation.y=Math.sin(t*.015)*.03;},
  };
}
