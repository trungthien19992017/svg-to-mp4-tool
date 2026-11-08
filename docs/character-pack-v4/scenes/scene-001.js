import {namespaceSvg, createActor} from '../modules/character.js';
export function createScene(context) {
  if (context.gsap.version !== '3.15.0') throw new Error('GSAP 3.15.0 required');
  const namespaces = [];
  const actors = [];
  for (const [asset, x, scale] of [['male-art', 50, .8], ['female-art', 480, .84]]) {
    const source = namespaceSvg(context.assetText(asset), context.sceneId + '-' + asset);
    namespaces.push(source);
    const group = context.addSvg(source.markup);
    group.setAttribute('transform', 'translate(' + x + ' 60) scale(' + scale + ')');
    actors.push(createActor(group));
  }
  const duration = context.duration;
  const clock = {time: 0};
  const timeline = context.timeline();
  timeline.fromTo(clock, {time: 0}, {time: duration, duration, ease: 'none', immediateRender: false}, 0);
  let disposed = false;
  function seek(time) {
    if (disposed) return;
    const t = Math.min(duration, Math.max(0, Number.isFinite(time) ? time : 0));
    timeline.time(t, true);
    for (const actor of actors) actor.render({time: clock.time, view: 'front', expression: 'default'});
  }
  seek(0);
  return {
    duration, seek,
    reset() {seek(0);},
    dispose() {
      if (disposed) return;
      disposed = true;
      timeline.kill();
      for (const actor of actors) actor.dispose();
      for (const source of namespaces) source.release();
    }
  };
}
