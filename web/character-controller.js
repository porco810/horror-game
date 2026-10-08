import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export const STATES = ['idle', 'walk', 'alert', 'chase', 'search', 'lament', 'feed', 'ritual'];
export const LOOPING = new Set(['idle', 'walk', 'chase', 'search', 'ritual']);
export const ITEM_REACTIONS = Object.freeze({photograph:'lament', hairpin:'lament', child_sandals:'lament', onigiri:'feed', dango:'feed', kagura_bell:'ritual'});

export class KuchikaguraController {
  static async load(url = './assets/models/kuchikagura.glb') {
    // Read the complete response before parsing; avoid a streamed FileLoader
    // request being reported as aborted by recent Chromium after consumption.
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Model request failed: HTTP ${response.status}`);
    const bytes = await response.arrayBuffer();
    const base = new URL('.', new URL(url, window.location.href)).href;
    const gltf = await new GLTFLoader().parseAsync(bytes, base);
    return new KuchikaguraController(gltf);
  }
  constructor(gltf) {
    this.model = gltf.scene;
    this.clips = new Map(gltf.animations.map(clip => [clip.name, clip]));
    for (const name of STATES) if (!this.clips.has(name)) throw new Error(`Missing animation: ${name}`);
    this.mixer = new THREE.AnimationMixer(this.model);
    this.actions = new Map([...this.clips].map(([name,clip]) => [name,this.mixer.clipAction(clip)]));
    this.state = null;
    this.paused = false;
    this.speed = 1;
    this.showReactionProps = true;
    this.onStateChange = () => {};
    this.mixer.addEventListener('finished', event => {
      if (event.action === this.action && !LOOPING.has(this.state)) this.play('idle');
    });
    this.play('idle', {fade:0});
  }
  play(name, {fade = .18} = {}) {
    if (!this.actions.has(name)) throw new Error(`Unknown animation: ${name}`);
    const next = this.actions.get(name);
    if (this.action === next || fade === 0) this.mixer.stopAllAction();
    else if (this.action) this.action.fadeOut(fade);
    next.reset().setEffectiveWeight(1).setEffectiveTimeScale(1);
    next.setLoop(LOOPING.has(name) ? THREE.LoopRepeat : THREE.LoopOnce, LOOPING.has(name) ? Infinity : 1);
    next.clampWhenFinished = true;
    next.paused = this.paused;
    if (fade > 0) next.fadeIn(fade);
    next.play();
    this.action = next;
    this.state = name;
    this.onStateChange(name);
  }
  reactToItem(item) {
    const state = ITEM_REACTIONS[item];
    if (!state) return false;
    this.play(state);
    return true;
  }
  setPaused(paused) { this.paused = paused; this.action.paused = paused; }
  seek(seconds) {
    this.action.time = THREE.MathUtils.clamp(seconds, 0, this.clips.get(this.state).duration - .0001);
    this.mixer.update(0);
    this.model.updateMatrixWorld(true);
  }
  update(delta) {
    this.mixer.update(Math.min(delta,.1) * this.speed);
    this.propScales = {};
    for (const name of ['MEMORY_PROP_CTRL','FOOD_PROP_CTRL','BELL_PROP_CTRL']) {
      const bone=this.model.getObjectByName(name);
      this.propScales[name]=bone?.scale.x ?? .001;
      if (!this.showReactionProps) bone?.scale.setScalar(.001);
    }
  }
  get duration() { return this.clips.get(this.state).duration; }
}
