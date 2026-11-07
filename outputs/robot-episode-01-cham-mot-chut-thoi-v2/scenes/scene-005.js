function createProps(context, OFFSET) {
  const NS = 'http://www.w3.org/2000/svg';
  let seed = 20261107;
  const R = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const sm = (t, lo, hi) => { const x = Math.min(1, Math.max(0, (t - lo) / (hi - lo))); return x * x * (3 - 2 * x); };
  const mk = (parent, tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };
  const f1 = v => v.toFixed(1);
  let B, F, rain, curtL, curtR, plant, lampGlow, tint, bulbs = [];
  const streaks = [], drops = [], wisps = [], blobs = [];
  return {
    back() {
      B = context.addSvg(context.assetText('layer-back'));
      rain = B.querySelector('#rain'); curtL = B.querySelector('#curtL'); curtR = B.querySelector('#curtR'); plant = B.querySelector('#plant');
      bulbs = [...B.querySelectorAll('.bulb')];
      const dg = B.querySelector('#drops');
      for (let i = 0; i < 28; i++) { const L = 60 + R() * 60; const e = mk(rain, 'line', { x2: f1(-0.1 * L), y2: f1(L), stroke: '#d6e8ee', 'stroke-width': (2 + R() * 2).toFixed(1), 'stroke-linecap': 'round', opacity: (0.35 + R() * 0.5).toFixed(2) }); streaks.push({ e, L, H: 870 + L, x: 115 + i * 32 + R() * 20, v: 750 + R() * 450, p: R() * 2000 }); }
      for (let i = 0; i < 9; i++) { const e = mk(dg, 'path', { d: 'M0 -16C5 -6 7 2 0 8C-7 2 -5 -6 0 -16Z', fill: '#eaf5f8', 'fill-opacity': 0.4 }); drops.push({ e, H: 880, x: 150 + R() * 780, v: 35 + R() * 50, p: R() * 880 }); }
    },
    front() {
      F = context.addSvg(context.assetText('layer-front'));
      lampGlow = F.querySelector('#lampGlow'); tint = F.querySelector('#tint');
      const sg = F.querySelector('#steam'), bg = F.querySelector('#bokeh');
      for (let i = 0; i < 3; i++) wisps.push({ i, e: mk(sg, 'path', { d: 'M0 0C-9 -16 9 -30 0 -48', fill: 'none', stroke: '#fff7ea', 'stroke-width': 5, 'stroke-linecap': 'round' }) });
      const cols = ['#ffd9a0', '#ffb8c8', '#fff1c8', '#ffc98f'];
      for (let i = 0; i < 16; i++) blobs.push({ i, e: mk(bg, 'circle', { r: (14 + R() * 34).toFixed(0), fill: cols[i % 4], opacity: 0 }), x: 80 + R() * 920, y: 900 + R() * 800, p: R() * 500, s: 8 + R() * 14 });
    },
    update(time) {
      const g = OFFSET + time, warm = sm(g, 17, 24), bk = sm(g, 24.5, 27);
      rain.setAttribute('opacity', (0.6 * (1 - 0.4 * sm(g, 24, 30))).toFixed(3));
      for (const s of streaks) { const y = ((g * s.v + s.p) % s.H) - s.L; s.e.setAttribute('transform', 'translate(' + f1(s.x - 0.1 * y) + ',' + f1(288 + y) + ')'); }
      for (const d of drops) { const c = (g * d.v + d.p) % d.H; d.e.setAttribute('transform', 'translate(' + f1(d.x + 2 * Math.sin(g * 1.3 + d.p)) + ',' + f1(300 + c) + ')'); }
      curtL.setAttribute('transform', 'rotate(' + (0.5 * Math.sin(g * 0.6)).toFixed(3) + ' 60 236)');
      curtR.setAttribute('transform', 'rotate(' + (0.5 * Math.sin(g * 0.6 + 1.6)).toFixed(3) + ' 1020 236)');
      plant.setAttribute('transform', 'rotate(' + (2 * Math.sin(g * 0.9)).toFixed(3) + ' 200 1100)');
      bulbs.forEach((b, i) => b.setAttribute('opacity', ((0.5 + 0.5 * warm) * (0.6 + 0.4 * Math.sin(g * 2.1 + i * 1.7))).toFixed(3)));
      lampGlow.setAttribute('opacity', (0.3 + 0.7 * warm).toFixed(3));
      tint.setAttribute('opacity', (0.1 * warm).toFixed(3));
      wisps.forEach(w => { const ph = (g * 0.5 + w.i / 3) % 1; w.e.setAttribute('transform', 'translate(' + f1(96 + (w.i - 1) * 12 + 5 * Math.sin(g * 1.6 + w.i)) + ',' + f1(1322 - ph * 90) + ')'); w.e.setAttribute('opacity', (0.55 * Math.sin(Math.PI * ph)).toFixed(3)); });
      blobs.forEach(b => { const ph = (g * b.s + b.p) % 700; b.e.setAttribute('transform', 'translate(' + f1(b.x + 30 * Math.sin(g * 0.4 + b.i)) + ',' + f1(b.y - ph) + ')'); b.e.setAttribute('opacity', (bk * (0.14 + 0.1 * Math.sin(g * 1.1 + b.i)) * Math.sin(Math.PI * ph / 700)).toFixed(3)); });
    }
  };
}

export function createScene(context) {
  const {gsap} = context;
  const OFFSET = 24;
  context.addSvg(context.assetText('room'));
  const props = createProps(context, OFFSET);
  props.back();
  const female = context.character('female', {id:'female-actor',x:110,y:870,scale:1.35});
  const male = context.character('male', {id:'male-actor',x:380,y:870,scale:1.35});
  props.front();
  const F = id => female.querySelector('#'+id);
  const M = id => male.querySelector('#'+id);
  const t = context.timeline();
  const rot = (el,from,to,start,duration,ease='power2.inOut',origin='50% 50%') => t.fromTo(el,{rotation:from,transformOrigin:origin},{rotation:to,duration,ease,transformOrigin:origin,immediateRender:false},start);
  const move = (el,from,to,start,duration,ease='power2.inOut') => t.fromTo(el,from,{...to,duration,ease,immediateRender:false},start);
  const blink = (el,at) => t.fromTo(el,{scaleY:1,transformOrigin:'50% 50%'},{scaleY:.12,duration:.12,yoyo:true,repeat:1,transformOrigin:'50% 50%',immediateRender:false},at);
  const expressionTracks=[];
  function expressions(actor, prefix, sequence) {
    const nodes=[...actor.querySelectorAll('.'+prefix+'-expr')];
    nodes.forEach(n=>{n.style.display='';n.style.opacity='0';});
    expressionTracks.push({nodes,sequence});
  }
  function applyExpressions(time) {
    for(const {nodes,sequence} of expressionTracks){
      let active=sequence[0][1], previous=null, transition=-1;
      for(let i=1;i<sequence.length;i++) if(time>=sequence[i][0]) {
        previous=sequence[i-1][1];active=sequence[i][1];transition=sequence[i][0];
      }
      const fade=transition>=0?Math.min(1,(time-transition)/.12):1;
      nodes.forEach(n=>{
        n.style.opacity=String(n.dataset.e===active?fade:(n.dataset.e===previous?1-fade:0));
      });
    }
  }

  // Continuity from scene 004 at local time 7.000.
  gsap.set(F('f-head'), {rotation:-3,transformOrigin:'50% 75%'}, 0);
  gsap.set(F('f-root'), {x:-9,y:8}, 0);
  gsap.set(F('f-arm-right'), {x:29,y:-2,rotation:-8,transformOrigin:'50% 0%'}, 0);
  gsap.set(M('m-head'), {rotation:-6,transformOrigin:'50% 75%'}, 0);
  gsap.set(M('m-arm-left'), {x:-29,y:-2,rotation:8,transformOrigin:'50% 0%'}, 0);
  gsap.set(context.camera, {scale:1.075,x:-35,y:-18}, 0);
  expressions(female,'f',[[0,'satisfied'],[1.8,'happy'],[4.5,'satisfied']]);
  expressions(male,'m',[[0,'satisfied'],[1.5,'happy'],[4.4,'satisfied']]);
  // Keep both hand transforms fixed from scene 004 (including shoulder rotations).

  rot(F('f-head'),-3,-11,1.1,1.1,'sine.inOut','50% 75%');
  rot(M('m-head'),-6,7,1.0,1.1,'sine.inOut','50% 75%');
  // ba trái tim bay lên giữa hai cái đầu
  [[478,2.3,1.1],[420,2.8,.65],[536,3.1,.65]].forEach(([hx,st,sc])=>{
    const h=context.addSvg(context.assetText('heart'),{x:hx,y:1190,scale:.4});
    gsap.set(h,{opacity:0,y:1190,scale:.4,transformOrigin:'50% 50%'});
    t.fromTo(h,{opacity:0,y:1190,scale:.4,transformOrigin:'50% 50%'},{opacity:1,y:1060,scale:sc,duration:1.1,ease:'power2.out',transformOrigin:'50% 50%',immediateRender:false},st);
    t.fromTo(h,{opacity:1,y:1060},{opacity:0,y:940,duration:1.2,ease:'power1.in',immediateRender:false},st+1.3);
  });
  move(context.camera,{scale:1.075,x:-35,y:-18},{scale:1,x:0,y:0},2.0,3.7,'sine.inOut');
  const FF = 'Segoe UI, Noto Sans, Arial, sans-serif';
  const ending=context.addSvg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920"><rect x="90" y="620" width="900" height="250" rx="56" fill="#1d2b36" fill-opacity=".58"/><text x="540" y="705" font-size="42" text-anchor="middle" fill="#fff7e9" font-family="'+FF+'">Đôi khi, hạnh phúc chỉ cách nhau</text><text x="540" y="775" font-size="48" font-weight="700" text-anchor="middle" fill="#fff7e9" font-family="'+FF+'">một cái chạm.</text><path transform="translate(512 800) scale(.56)" d="M50 88C35 74 8 55 8 32C8 10 36 8 50 29C64 8 92 10 92 32C92 55 65 74 50 88Z" fill="#fca1b7"/></svg>');
  gsap.set(ending,{opacity:0});
  move(ending,{opacity:0},{opacity:1},3.4,.9,'sine.out');
  return {duration:6,seek(time){t.time(time,true);applyExpressions(time);props.update(time);},reset(){t.pause(0);},dispose(){t.kill();}};
}
