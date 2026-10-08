// Original, synthesized environmental audio; no external media or tracking.
export class VillageAudio {
  constructor(){this.volume=.55;this.context=null;this.nextStep=0;this.nextEnemyStep=0;this.nextHeart=0;this.muted=false;}
  resetClock(){this.nextStep=this.nextEnemyStep=this.nextHeart=0;}
  async start(){
    if(!this.context){
      const ctx=this.context=new (window.AudioContext||window.webkitAudioContext)();
      this.master=ctx.createGain();this.master.gain.value=this.volume;this.master.connect(ctx.destination);
      const buffer=ctx.createBuffer(1,ctx.sampleRate*3,ctx.sampleRate),data=buffer.getChannelData(0);let b=0;
      for(let i=0;i<data.length;i++){b=(b+(Math.random()*2-1)*.04)/1.025;data[i]=b;}
      const wind=ctx.createBufferSource();wind.buffer=buffer;wind.loop=true;
      const filter=ctx.createBiquadFilter();filter.type='lowpass';filter.frequency.value=420;
      const windGain=ctx.createGain();windGain.gain.value=.32;wind.connect(filter).connect(windGain).connect(this.master);wind.start();
      this.drone=ctx.createOscillator();this.drone.type='sine';this.drone.frequency.value=48;
      this.droneGain=ctx.createGain();this.droneGain.gain.value=.025;this.drone.connect(this.droneGain).connect(this.master);this.drone.start();
      this.enemyGain=ctx.createGain();this.enemyGain.gain.value=0;
      this.enemyPan=ctx.createStereoPanner();this.enemyOsc=ctx.createOscillator();this.enemyOsc.type='triangle';this.enemyOsc.frequency.value=136;
      this.enemyOsc.connect(this.enemyGain).connect(this.enemyPan).connect(this.master);this.enemyOsc.start();
    }
    if(this.context.state==='suspended')await this.context.resume();
  }
  setVolume(value){this.volume=value;if(this.master)this.master.gain.setTargetAtTime(this.muted?0:value,this.context.currentTime,.1);}
  setPaused(paused){this.muted=paused;this.setVolume(this.volume);}
  tone(frequency,duration,gain=.1,type='sine',pan=0){
    const c=this.context;if(!c||c.state!=='running')return;
    const osc=c.createOscillator(),env=c.createGain(),p=c.createStereoPanner(),t=c.currentTime;
    osc.type=type;osc.frequency.value=frequency;env.gain.setValueAtTime(0,t);env.gain.linearRampToValueAtTime(gain,t+.008);env.gain.exponentialRampToValueAtTime(.0001,t+duration);p.pan.value=pan;
    osc.connect(env).connect(p).connect(this.master);osc.start(t);osc.stop(t+duration+.02);
  }
  bell(){[880,1320,1760,2370].forEach((f,i)=>this.tone(f,1.6-i*.18,.12/(i+1)));}
  pickup(){this.tone(590,.18,.07);this.tone(790,.35,.045);}
  throw(){this.tone(150,.18,.045,'triangle');}
  catch(){this.tone(57,1.8,.2,'sawtooth');this.tone(91,1.7,.1);}
  update({running,moving,crouching,enemyDistance,enemyPan,state,time}){
    if(!this.context||this.muted)return;
    if(moving&&time>this.nextStep){this.tone(80+Math.random()*30,.15,crouching?.035:.085,'triangle');this.nextStep=time+(running?.28:.48);}
    const near=Math.max(0,1-enemyDistance/15),chasing=state==='chase';
    if(near>.05&&['walk','chase','search'].includes(state)&&time>this.nextEnemyStep){this.tone(chasing?93:116,.21,near*.13,'triangle',enemyPan);this.nextEnemyStep=time+(chasing?.34:.66);}
    this.enemyPan.pan.setTargetAtTime(Math.max(-1,Math.min(1,enemyPan)),this.context.currentTime,.1);
    this.enemyGain.gain.setTargetAtTime(near*(state==='lament'?.08:.024),this.context.currentTime,.25);
    this.enemyOsc.frequency.setTargetAtTime(state==='lament'?194:state==='ritual'?218:136,this.context.currentTime,.2);
    this.droneGain.gain.setTargetAtTime(chasing?.08:.025,this.context.currentTime,.25);
    if(near>.4&&time>this.nextHeart){this.tone(52,.2,.1*near);this.tone(67,.16,.07*near);this.nextHeart=time+(chasing?.56:1.2);}
  }
}
