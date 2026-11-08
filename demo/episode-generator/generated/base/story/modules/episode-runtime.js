// Demo helper module. Only uses the existing Animation Code Contract v1.
export function createEpisode(context, config, evaluate) {
  const parsed = new DOMParser().parseFromString(context.assetText(config.assetId), 'image/svg+xml');
  const prefix = context.sceneId + '-actor-';
  for (const node of parsed.querySelectorAll('[id]')) node.id = prefix + node.id;
  for (const node of parsed.querySelectorAll('*')) {
    for (const attribute of [...node.attributes]) {
      let value = attribute.value.replace(/url\(#([^)]+)\)/g, (_, id) => 'url(#' + prefix + id + ')');
      if (attribute.localName === 'href' && value.startsWith('#')) value = '#' + prefix + value.slice(1);
      node.setAttribute(attribute.name, value);
    }
  }
  const actor = context.addSvg(new XMLSerializer().serializeToString(parsed));
  const nodes = new Map(Object.entries(config.rig.joints).map(([key, binding]) => {
    const node = actor.querySelector('#' + prefix + binding.nodeId);
    if (!node) throw Error('Missing rig joint ' + key);
    return [key, {node, base: node.getAttribute('transform') || '', pivot: binding.pivot}];
  }));
  let disposed = false;
  function seek(time) {
    if (disposed) return;
    const t = Math.max(0, Math.min(config.duration, time));
    const offsets = evaluate(t, config.duration);
    for (const key of Object.keys(offsets)) {
      if (!nodes.has(key) || !Number.isFinite(offsets[key])) throw Error('Invalid adapter joint/angle ' + key);
    }
    for (const [key, {node, base, pivot}] of nodes) {
      const angle = (config.pose.rotations[key] || 0) + (offsets[key] || 0);
      node.setAttribute('transform', base + ' rotate(' + angle + ' ' + pivot.join(' ') + ')');
    }
    for (const id of config.expressionNodes) {
      const node = actor.querySelector('#' + prefix + id);
      if (!node) throw Error('Missing expression node ' + id);
      node.setAttribute('visibility', id === config.expression.nodeId ? 'visible' : 'hidden');
    }
  }
  seek(0);
  return {duration: config.duration, seek, reset() {seek(0);},
    dispose() {if (!disposed) actor.remove(); disposed = true;}};
}
