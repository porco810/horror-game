// Each pad owns one pointer, so both thumbs can move independently.
export function attachTouchPad(element, canUse, onChange) {
  const knob = element.querySelector('.pad-knob');
  let pointerId = null;

  function reset() {
    const previous = pointerId;
    pointerId = null;
    if (previous !== null && element.hasPointerCapture(previous)) element.releasePointerCapture(previous);
    knob.style.transform = '';
    element.classList.remove('active');
    onChange(0, 0);
  }

  function move(event) {
    const bounds = element.getBoundingClientRect();
    const radius = (bounds.width - knob.offsetWidth) / 2 - 6;
    const x = (event.clientX - bounds.x - bounds.width / 2) / radius;
    const y = (event.clientY - bounds.y - bounds.height / 2) / radius;
    const length = Math.hypot(x, y);
    const amount = Math.min(1, length);
    const nx = length ? x / length : 0, ny = length ? y / length : 0;
    const strength = Math.max(0, (amount - .12) / .88);
    knob.style.transform = `translate(${nx * amount * radius}px, ${ny * amount * radius}px)`;
    onChange(nx * strength, ny * strength);
  }

  element.addEventListener('pointerdown', event => {
    if (!canUse() || pointerId !== null || event.button !== 0) return;
    event.preventDefault();
    pointerId = event.pointerId;
    element.setPointerCapture(pointerId);
    element.classList.add('active');
    move(event);
  });
  element.addEventListener('pointermove', event => {
    if (event.pointerId === pointerId && canUse()) move(event);
  });
  for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    element.addEventListener(name, event => { if (event.pointerId === pointerId) reset(); });
  }
  return reset;
}
