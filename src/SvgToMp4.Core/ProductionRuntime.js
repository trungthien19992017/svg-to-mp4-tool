// Production helper: same SceneContext contract as Studio. No global runtime changes.
const NS = 'http://www.w3.org/2000/svg';
export function holdPose() {return {};}
export function createEpisodeScene(context, config, adapters) {
  let disposed = false;
  const owned = [];
  function artwork(assetId, id, options = {}) {
    const doc = new DOMParser().parseFromString(context.assetText(assetId), 'image/svg+xml');
    if (doc.querySelector('parsererror')) throw Error('Invalid SVG artwork');
    const prefix = 's' + context.sceneId.length + '-' + context.sceneId + '-a' + id.length + '-' + id + '-';
    for (const node of doc.querySelectorAll('[id]')) node.id = prefix + node.id;
    for (const node of doc.querySelectorAll('*')) {
      for (const attr of [...node.attributes]) {
        let value = attr.value.replace(/url\(#([^)]*)\)/g, (_, key) => 'url(#' + prefix + key + ')');
        if (attr.localName === 'href' && value.startsWith('#')) value = '#' + prefix + value.slice(1);
        if (attr.namespaceURI) node.setAttributeNS(attr.namespaceURI, attr.name, value);
        else node.setAttribute(attr.name, value);
      }
    }
    // addSvg intentionally drops root attributes; move presentation attributes to a group.
    const wrapper = doc.createElementNS(NS, 'g');
    for (const attr of [...doc.documentElement.attributes]) {
      if (!['viewBox','width','height','xmlns','id'].includes(attr.name) && !attr.name.startsWith('xmlns:')) wrapper.setAttribute(attr.name, attr.value);
    }
    for (const node of [...doc.documentElement.childNodes]) wrapper.append(node);
    doc.documentElement.append(wrapper);
    const node = context.addSvg(new XMLSerializer().serializeToString(doc), options);
    owned.push(node); return {node, prefix};
  }
  if (config.background) artwork(config.background, 'environment');
  const actors = config.actors.map((actor, index) => {
    const {node, prefix} = artwork(actor.assetId, 'actor-' + index + '-' + actor.id, {x: actor.x, y: actor.y, scale: actor.scale});
    const joints = new Map(Object.entries(config.rig.joints).map(([key, binding]) => {
      const target = node.querySelector('#' + prefix + binding.nodeId);
      if (!target) throw Error('Missing rig joint ' + key);
      return [key, {target, base: target.getAttribute('transform') || '', pivot: binding.pivot}];
    }));
    return {actor, node, prefix, joints, evaluate: adapters[index]};
  });
  if (config.foreground) artwork(config.foreground, 'foreground');
  if (config.caption) {
    const label = document.createElementNS(NS, 'text');
    for (const [key, value] of Object.entries({x: context.width / 2, y: context.height - 65, 'text-anchor':'middle', fill:'#ffffff', 'font-size':26, 'font-family':'sans-serif', 'paint-order':'stroke', stroke:'#142639', 'stroke-width':5})) label.setAttribute(key, value);
    label.textContent = config.caption; context.canvas.append(label); owned.push(label);
  }
  function seek(time) {
    if (disposed) return;
    const t = Math.max(0, Math.min(config.duration, time));
    for (const {actor, node, prefix, joints, evaluate} of actors) {
      const offsets = evaluate(t / config.duration * actor.motionDuration, actor.motionDuration);
      if (!offsets || typeof offsets !== 'object' || Array.isArray(offsets)) throw Error('Adapter must return joint angles');
      for (const [key, value] of Object.entries(offsets)) if (!joints.has(key) || !Number.isFinite(value)) throw Error('Invalid adapter joint/angle ' + key);
      for (const [key, {target, base, pivot}] of joints) {
        const angle = (actor.pose.rotations[key] || 0) + (offsets[key] || 0);
        target.setAttribute('transform', base + ' rotate(' + angle + ' ' + pivot.join(' ') + ')');
      }
      for (const id of actor.expressionNodes || config.expressionNodes) {
        const target = node.querySelector('#' + prefix + id);
        // Unsupported/unavailable expressions may have no artwork in this rig.
        if (target) target.setAttribute('visibility', id === actor.expression.nodeId ? 'visible' : 'hidden');
      }
    }
  }
  seek(0);
  return {duration: config.duration, seek, reset() {seek(0);}, dispose() {
    if (disposed) return;
    disposed = true; for (const node of owned) node.remove();
  }};
}
