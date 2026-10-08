import {test} from 'node:test';
import assert from 'node:assert/strict';
import {VillageNavigation,PursuerAI,freshProgress,parseProgress} from '../web/gameplay.js';

test('swept collision stops a sprint at a wall and permits sliding along it',()=>{
  const nav=new VillageNavigation([{minX:1,maxX:2,minZ:-4,maxZ:4}]);
  const player={x:0,z:0};nav.move(player,12,3);
  assert.ok(player.x<.69);assert.ok(player.z>2.9);assert.ok(nav.free(player));
});
test('navigation routes around buildings without clipping walls or diagonal corners',()=>{
  const nav=new VillageNavigation([{minX:-2,maxX:2,minZ:-3,maxZ:3}]);
  const start={x:0,z:6},end={x:0,z:-6},path=nav.findPath(start,end);
  assert.ok(path.length>3);assert.deepEqual(path.at(-1),end);
  let previous=start;
  for(const p of path){assert.ok(nav.free(p,.4));assert.ok(nav.lineClear(previous,p,.39));previous=p;}
});
test('solid buildings occlude detection while a low offering table permits eye-level sight',()=>{
  const wall=new VillageNavigation([{minX:-1,maxX:1,minZ:-18,maxZ:-17,height:3}]);
  assert.equal(wall.lineClear({x:0,z:-20},{x:0,z:-14},0,1.5),false);
  const table=new VillageNavigation([{minX:-1,maxX:1,minZ:-18,maxZ:-17,height:.7}]);
  assert.equal(table.lineClear({x:0,z:-20},{x:0,z:-14},0,1.5),true);
  assert.equal(table.free({x:0,z:-17.5}),false);
});
test('pursuer alerts, chases visible player, and searches after losing sight',()=>{
  const nav=new VillageNavigation([]),states=[];
  const ai=new PursuerAI(nav,{onState:s=>states.push(s)});ai.grace=0;ai.angle=0;
  const player={x:0,z:-14,flashlight:false,running:false,crouching:false};
  ai.update(.1,player);assert.equal(ai.state,'alert');ai.update(1.4,player);assert.equal(ai.state,'chase');
  ai.angle=Math.PI;player.z=31;for(let i=0;i<60;i++)ai.update(.1,player);
  assert.ok(states.includes('search'));assert.notEqual(ai.state,'chase');
});
test('each offering suppresses capture and returns to search after its real duration',()=>{
  for(const [item,state,duration] of [['photograph','lament',7.2],['hairpin','lament',7.2],['child_sandals','lament',7.2],['onigiri','feed',5.2],['dango','feed',5.2],['kagura_bell','ritual',7.8]]){
    let catches=0,memories=0;const ai=new PursuerAI(new VillageNavigation([]),{onCatch:()=>catches++,onMemory:()=>memories++});ai.grace=0;
    assert.equal(ai.offer(item,{x:0,z:-19}),true);assert.equal(ai.state,state);
    ai.update(duration-.1,{x:0,z:-20,flashlight:true});assert.equal(catches,0);assert.equal(ai.state,state);
    ai.update(.2,{x:0,z:-20,flashlight:true});assert.equal(ai.state,'search');assert.equal(memories,state==='lament'?1:0);
  }
});
test('unreachable offerings fail, leaving AI unchanged',()=>{
  const nav=new VillageNavigation([{minX:-2,maxX:2,minZ:-19,maxZ:-18}]),ai=new PursuerAI(nav);
  assert.equal(ai.offer('photograph',{x:0,z:-16}),false);assert.equal(ai.state,'idle');
  assert.equal(ai.offer('kagura_bell',{x:0,z:25}),false);
});
test('save parsing preserves dropped memories and rejects false quest unlocks',()=>{
  const p=freshProgress();p.inventory.photograph=1;p.dropped=[{id:'drop1',item:'hairpin',x:4,z:5}];p.key=true;p.unlocked=true;
  const loaded=parseProgress(JSON.stringify(p));assert.equal(loaded.key,false);assert.equal(loaded.unlocked,false);assert.deepEqual(loaded.dropped,p.dropped);
  p.seals=['seal_house','seal_well','seal_store'];assert.equal(parseProgress(JSON.stringify(p)).key,true);
  assert.equal(parseProgress('not json'),null);assert.equal(parseProgress('{}'),null);
});
