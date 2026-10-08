// The simulation has no DOM or renderer dependency. Coordinates are metres.
export const ITEMS = Object.freeze({
  photograph: {name:'古い写真', short:'写真', glyph:'▧', reaction:'lament', kind:'memory'},
  hairpin: {name:'花のかんざし', short:'かんざし', glyph:'✣', reaction:'lament', kind:'memory'},
  child_sandals: {name:'子どもの草履', short:'草履', glyph:'♧', reaction:'lament', kind:'memory'},
  onigiri: {name:'おにぎり', short:'握り飯', glyph:'△', reaction:'feed', kind:'food'},
  dango: {name:'三色団子', short:'団子', glyph:'●', reaction:'feed', kind:'food'},
  kagura_bell: {name:'神楽鈴', short:'神楽鈴', glyph:'♧', reaction:'ritual', kind:'bell'},
});
export const ITEM_ORDER = Object.keys(ITEMS);
export const SAVE_KEY = 'kuchi-kagura-game-v1';
export const SPAWN = {x:0,z:31};
export const ENEMY_SPAWN = {x:0,z:-20};
export const PATROL = [{x:0,z:-19},{x:8,z:-8},{x:0,z:6},{x:-8,z:0},{x:0,z:-8}];
export const SEALS = ['seal_house','seal_well','seal_store'];
export const NOTES = {
  village: {title:'境の置き手紙', place:'村の入口', text:'日が落ちたら、この村で名を呼ぶな。\n屋敷、井戸、蔵にある三枚の鎮め札を社へ返せ。そうすれば、境の門は開く。\n\n走る足音と灯りを、あれは覚える。家の陰へ回り、灯りを消し、息を潜めよ。'},
  diary: {title:'母の書きつけ', place:'旧家', text:'祭りの晩、あの子は帰らなかった。\n写真も、花のかんざしも、小さな草履も、そのまま残してある。\n\nあの人は、まだ拾いに来る。\n三つの思い出を手向ければ、道を塞ぐものも、帰り道を思い出すだろうか。'},
  food: {title:'炊き出しの覚え書き', place:'炊事小屋', text:'腹を空かせたものに、供物を投げよ。\n握り飯や団子に気づけば、足を止めて食らう。\n\n遠くへ投げすぎるな。すぐ傍へ手向け、食らうあいだに離れよ。'},
  ritual: {title:'奉納の作法', place:'山の社', text:'鈴を鳴らせば、忘れた舞が始まる。\n舞のあいだは、振り向かずに通れ。鈴は投げず、手に持ったまま鳴らす。\n\n三枚の札を祭壇に納め、境の鍵を受け取れ。鍵を携え、南の門へ戻れ。'},
};
export const clamp = (n,a,b) => Math.max(a,Math.min(b,n));
export const distance = (a,b) => Math.hypot(a.x-b.x,a.z-b.z);
export function freshProgress() {return {version:1,collected:[],notes:[],seals:[],memories:[],dropped:[],inventory:Object.fromEntries(ITEM_ORDER.map(k=>[k,0])),unlocked:false,key:false,checkpoint:{...SPAWN},elapsed:0};}
export function parseProgress(raw) {
  try {
    const p=JSON.parse(raw);
    if(p.version!==1 || !Array.isArray(p.collected) || !Array.isArray(p.seals) || !Array.isArray(p.notes) || !Array.isArray(p.memories))return null;
    const result=freshProgress();
    result.collected=p.collected.filter(x=>typeof x==='string');
    result.notes=[...new Set(p.notes.filter(x=>Object.hasOwn(NOTES,x)))];
    result.seals=[...new Set(p.seals.filter(x=>SEALS.includes(x)))];
    result.memories=[...new Set(p.memories.filter(x=>ITEMS[x]?.kind==='memory'))];
    result.dropped=(Array.isArray(p.dropped)?p.dropped:[]).filter(d=>typeof d.id==='string'&&ITEMS[d.item]&&d.item!=='kagura_bell'&&Number.isFinite(d.x)&&Number.isFinite(d.z)&&Math.abs(d.x)<24&&Math.abs(d.z)<34).slice(0,30);
    for(const k of ITEM_ORDER)result.inventory[k]=clamp(Math.floor(Number(p.inventory?.[k])||0),0,20);
    result.unlocked=Boolean(p.unlocked)&&new Set(result.seals).size===3;
    result.key=Boolean(p.key)&&result.unlocked;
    result.elapsed=Math.max(0,Number(p.elapsed)||0);
    if(Number.isFinite(p.checkpoint?.x)&&Number.isFinite(p.checkpoint?.z)&&Math.abs(p.checkpoint.x)<26&&Math.abs(p.checkpoint.z)<36)result.checkpoint={x:p.checkpoint.x,z:p.checkpoint.z};
    return result;
  }catch{return null;}
}
export class VillageNavigation {
  constructor(obstacles,bounds={minX:-24,maxX:24,minZ:-34,maxZ:34}){
    this.obstacles=obstacles;this.bounds=bounds;this.cell=1;this.width=bounds.maxX-bounds.minX+1;
  }
  free(p,r=.32){
    const b=this.bounds;
    return p.x>b.minX+r&&p.x<b.maxX-r&&p.z>b.minZ+r&&p.z<b.maxZ-r&&!this.obstacles.some(o=>(p.y===undefined||p.y<=(o.height??3))&&p.x>o.minX-r&&p.x<o.maxX+r&&p.z>o.minZ-r&&p.z<o.maxZ+r);
  }
  move(p,dx,dz,r=.32){
    // Swept substeps prevent tunnelling at both sprint and low frame rates.
    const count=Math.max(1,Math.ceil(Math.hypot(dx,dz)/.15));
    for(let i=0;i<count;i++){
      const x={x:p.x+dx/count,z:p.z};if(this.free(x,r))p.x=x.x;
      const z={x:p.x,z:p.z+dz/count};if(this.free(z,r))p.z=z.z;
    }
  }
  lineClear(a,b,margin=0,eyeHeight=0){
    for(const o of this.obstacles){
      if(eyeHeight>(o.height??3))continue;
      let low=0,high=1;
      for(const axis of ['X','Z']){
        const k=axis.toLowerCase(),d=b[k]-a[k],min=o['min'+axis]-margin,max=o['max'+axis]+margin;
        if(Math.abs(d)<1e-8){if(a[k]<min||a[k]>max){low=2;break;}}
        else{let t1=(min-a[k])/d,t2=(max-a[k])/d;if(t1>t2)[t1,t2]=[t2,t1];low=Math.max(low,t1);high=Math.min(high,t2);}
      }
      if(low<=high&&high>0&&low<1)return false;
    }
    return true;
  }
  findPath(start,end){
    if(this.lineClear(start,end,.42))return [{...end}];
    const b=this.bounds;
    const key=p=>`${p.x},${p.z}`,round=p=>({x:Math.round(p.x),z:Math.round(p.z)});
    const origin=round(start),goal=round(end),goalKey=key(goal),open=[origin],came=new Map(),cost=new Map([[key(origin),0]]);
    const score=p=>cost.get(key(p))+distance(p,goal);
    const seen=new Set();let found=null;
    for(let n=0;open.length&&n<2800;n++){
      let best=0;for(let i=1;i<open.length;i++)if(score(open[i])<score(open[best]))best=i;
      const cur=open.splice(best,1)[0],ck=key(cur);if(ck===goalKey){found=cur;break;}seen.add(ck);
      for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]]){
        const next={x:cur.x+dx,z:cur.z+dz},nk=key(next);
        if(next.x<=b.minX||next.x>=b.maxX||next.z<=b.minZ||next.z>=b.maxZ||seen.has(nk)||!this.free(next,.44))continue;
        if(dx&&dz&&(!this.free({x:cur.x+dx,z:cur.z},.44)||!this.free({x:cur.x,z:cur.z+dz},.44)))continue;
        const g=cost.get(ck)+Math.hypot(dx,dz);
        if(g<(cost.get(nk)??Infinity)){came.set(nk,cur);cost.set(nk,g);if(!open.some(p=>key(p)===nk))open.push(next);}
      }
    }
    if(!found)return [];
    const path=[{...end}];let cur=found;
    while(key(cur)!==key(origin)){path.unshift(cur);cur=came.get(key(cur));if(!cur)return [];}
    while(path.length>1&&this.lineClear(start,path[1],.44))path.shift();
    return path;
  }
}
export class PursuerAI {
  constructor(nav,{difficulty='normal',onState=()=>{},onCatch=()=>{},onMemory=()=>{}}={}){
    this.nav=nav;this.onState=onState;this.onCatch=onCatch;this.onMemory=onMemory;this.difficulty=difficulty;
    this.reset();
  }
  reset(){this.position={...ENEMY_SPAWN};this.angle=Math.PI;this.state=null;this.timer=0;this.path=[];this.pathTimer=0;this.patrolIndex=0;this.lastSeen={...SPAWN};this.lost=0;this.grace=7;this.reactionItem=null;this.transition('idle',1.5);}
  transition(state,timer=0){if(this.state===state)return;this.state=state;this.timer=timer;this.path=[];this.pathTimer=0;this.onState(state);}
  hears(position,loudness=1){
    if(this.grace>0||['lament','feed','ritual','chase'].includes(this.state))return;
    if(distance(this.position,position)<loudness*10){this.lastSeen={...position};this.transition('alert',1.3);}
  }
  offer(item,position){
    const def=ITEMS[item];if(!def||distance(this.position,position)>(def.kind==='bell'?20:5)||!this.nav.lineClear(this.position,position))return false;
    this.reactionItem=item;if(this.state===def.reaction)this.state=null;this.transition(def.reaction,def.reaction==='lament'?7.2:def.reaction==='feed'?5.2:7.8);return true;
  }
  walkTo(target,speed,dt){
    this.pathTimer-=dt;
    if(this.pathTimer<=0){this.path=this.nav.findPath(this.position,target);this.pathTimer=.65;}
    let point=this.path[0];
    if(point&&distance(this.position,point)<.23){this.path.shift();point=this.path[0];}
    if(!point)return;
    const d=distance(this.position,point),step=Math.min(speed*dt,d);
    this.angle=Math.atan2(point.x-this.position.x,point.z-this.position.z);
    this.nav.move(this.position,Math.sin(this.angle)*step,Math.cos(this.angle)*step,.4);
  }
  update(dt,player){
    this.grace=Math.max(0,this.grace-dt);this.timer-=dt;
    if(['lament','feed','ritual'].includes(this.state)){
      if(this.timer<=0){if(this.state==='lament')this.onMemory(this.reactionItem);this.reactionItem=null;this.transition('search',3);}
      return;
    }
    const d=distance(this.position,player),clear=this.nav.lineClear(this.position,player,0,1.5);
    const range=(this.difficulty==='gentle'?8:11)+(player.flashlight?3:0)+(player.running?4:0)-(player.crouching?4:0);
    const facing=(Math.sin(this.angle)*(player.x-this.position.x)+Math.cos(this.angle)*(player.z-this.position.z))/Math.max(.01,d);
    const visible=this.grace===0&&clear&&((d<range&&(facing>-.12||d<3))||(player.running&&d<15));
    if(visible){this.lastSeen={x:player.x,z:player.z};this.lost=0;
      if(this.state!=='chase'&&this.state!=='alert')this.transition('alert',1.25);
    }else this.lost+=dt;
    if(this.state==='alert'){
      this.angle=Math.atan2(this.lastSeen.x-this.position.x,this.lastSeen.z-this.position.z);
      if(this.timer<=0)this.transition(visible?'chase':'search',5);
    }else if(this.state==='chase'){
      this.walkTo(this.lastSeen,this.difficulty==='gentle'?2.0:3.05,dt);
      if(this.lost>4.2)this.transition('search',6);
    }else if(this.state==='search'){
      if(distance(this.position,this.lastSeen)>.8)this.walkTo(this.lastSeen,1.45,dt);else this.angle+=dt*.5;
      if(this.timer<=0)this.transition('walk');
    }else if(this.state==='idle'){
      if(this.timer<=0)this.transition('walk');
    }else if(this.state==='walk'){
      const target=PATROL[this.patrolIndex];this.walkTo(target,1.0,dt);
      if(distance(this.position,target)<.8){this.patrolIndex=(this.patrolIndex+1)%PATROL.length;this.transition('idle',1.7);}
    }
    if(this.grace===0&&this.state==='chase'&&d<1.0&&clear)this.onCatch();
  }
}
