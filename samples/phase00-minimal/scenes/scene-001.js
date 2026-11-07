export function createScene(context) {
  const art = context.svg('<svg xmlns="http://www.w3.org/2000/svg"><rect width="720" height="1280" fill="#173b40"/><circle id="phase00-dot" cx="100" cy="640" r="42" fill="#ffd68a"/></svg>');
  const dot = art.querySelector('#phase00-dot');
  const timeline = context.timeline();
  timeline.fromTo(dot, {x: 0}, {x: 480, duration: 3, ease: 'none'}, 0);
  return {
    duration: 3,
    seek(time) { timeline.time(time, true); },
    reset() { timeline.pause(0); },
    dispose() { timeline.kill(); }
  };
}
