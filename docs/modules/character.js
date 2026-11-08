const NS = 'http://www.w3.org/2000/svg';
const allocated = new Set();
export function namespaceSvg(markup, requested) {
  let prefix = requested.replace(/[^a-zA-Z0-9_-]/g, '-');
  while (allocated.has(prefix)) prefix += '-copy';
  allocated.add(prefix);
  const documentSvg = new DOMParser().parseFromString(markup, 'image/svg+xml');
  if (documentSvg.querySelector('parsererror')) throw new Error('Invalid SVG');
  for (const node of documentSvg.querySelectorAll('[id]')) node.id = prefix + '--' + node.id;
  for (const node of documentSvg.querySelectorAll('*')) {
    for (const attribute of [...node.attributes]) {
      let value = attribute.value.replace(/url\(#([^)]*)\)/g, (_, id) => 'url(#' + prefix + '--' + id + ')');
      if (attribute.localName === 'href' && value.startsWith('#')) value = '#' + prefix + '--' + value.slice(1);
      node.setAttribute(attribute.name, value);
    }
  }
  return {markup: new XMLSerializer().serializeToString(documentSvg), prefix,
    release() { allocated.delete(prefix); }};
}
export function createActor(element) {
  const views = [...element.querySelectorAll('[data-view]')].filter(node => node.parentElement === element);
  // Studio addSvg copies SVG children, so view groups are direct children of its returned g.
  const transforms = new Map([...element.querySelectorAll('[data-part]')].map(node => [node, node.getAttribute('transform')]));
  let disposed = false;
  function render({view = 'front', expression = 'default', time = 0, pose = 'idle', anchors = false} = {}) {
    if (disposed) return;
    const active = views.find(node => node.dataset.view === view);
    if (!active) throw new Error('Unsupported view ' + view);
    for (const node of views) node.setAttribute('visibility', node === active ? 'visible' : 'hidden');
    for (const [node, transform] of transforms) {
      if (transform !== null) node.setAttribute('transform', transform);
    }
    for (const state of active.querySelectorAll('[data-expression]')) {
      state.setAttribute('visibility', state.dataset.expression === expression ? 'visible' : 'hidden');
    }
    const closure = Math.max(0, 1 - Math.abs(((time % 3) - 1.5) / 0.12));
    for (const state of active.querySelectorAll('[data-expression]')) {
      for (const eye of state.querySelectorAll('[data-blink-pivot]')) {
        const [x, y] = eye.dataset.blinkPivot.split(' ').map(Number);
        const sy = state.dataset.closedEyes === 'true' ? 1 : 1 - .96 * closure;
        eye.setAttribute('transform', 'translate(' + x + ' ' + y + ') scale(1 ' + sy + ') translate(' + -x + ' ' + -y + ')');
      }
    }
    if (pose === 'arm-review') {
      const arm = active.querySelector('[data-part="upper-arm-L"]');
      const angle = 25 * Math.sin(Math.PI * Math.min(6, Math.max(0, time)) / 3);
      if (arm) arm.setAttribute('transform', transforms.get(arm) + ' rotate(' + angle + ')');
    }
    element.querySelector('[data-debug]')?.remove();
    if (anchors) {
      const debug = document.createElementNS(NS, 'g');
      debug.dataset.debug = 'true';
      element.append(debug);
      for (const part of active.querySelectorAll('[data-part]')) {
        const matrix = element.getScreenCTM().inverse().multiply(part.getScreenCTM());
        const point = new DOMPoint(0, 0).matrixTransform(matrix);
        const dot = document.createElementNS(NS, 'circle');
        for (const [key, value] of Object.entries({cx: point.x, cy: point.y, r: 4, fill: '#f04970'})) dot.setAttribute(key, value);
        debug.append(dot);
      }
    }
  }
  return {render, reset() {render();}, dispose() {if (!disposed) element.remove(); disposed = true;}};
}
