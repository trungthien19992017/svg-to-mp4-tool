// Original v1 scene adapter: every moving property is reconstructed from local time.
// No clocks, timers, network, external assets or accumulated simulation state.
const NS='http://www.w3.org/2000/svg';
function node(parent,tag,attrs){const el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);parent.append(el);return el;}
const fraction=x=>x-Math.floor(x);

export function createCozyScene(context,mood){
  const {gsap,sceneId}=context;
  // Namespace gradient IDs because all scene SVGs share one document.
  let background=context.assetText('cabin');
  for(const id of ['sky','water','wood','glow'])background=background.replaceAll(`id="${id}"`,`id="${sceneId}-${id}"`).replaceAll(`url(#${id})`,`url(#${sceneId}-${id})`);
  context.addSvg(background);
  const rainLayer=node(context.canvas,'g',{'stroke':'#c2e0df','stroke-width':1.3,'opacity':.33});
  const drops=Array.from({length:65},()=>({el:node(rainLayer,'line',{}),x:context.random()*720,phase:context.random(),speed:190+context.random()*160,length:12+context.random()*17}));
  const waterLayer=node(context.canvas,'g',{'fill':'none','stroke':'#abcac2','stroke-width':1.4});
  const ripples=Array.from({length:13},()=>({el:node(waterLayer,'ellipse',{}),x:380+context.random()*320,y:990+context.random()*270,phase:context.random()}));
  const may=context.character('may',{x:196,y:684,scale:1.02});
  const bong=context.character('bong',{x:490,y:910,scale:.88});
  const book=context.addSvg(context.assetText('book'),{x:204,y:701,scale:.75});
  const cup=context.addSvg(context.assetText('cup'),{x:329,y:742,scale:.7});
  context.addSvg(context.assetText('doodles'));
  const steam=node(context.canvas,'g',{'fill':'none','stroke':'#fff0d7','stroke-width':3,'stroke-linecap':'round'});
  const wisps=[-10,5,18].map(x=>node(steam,'path',{d:`M${329+x} 708q-12-13 0-25t0-26` }));
  const title=node(context.canvas,'g',{});
  node(title,'rect',{x:40,y:69,width:640,height:112,rx:24,fill:'#173b40',opacity:.86});
  const label=node(title,'text',{x:360,y:110,'text-anchor':'middle',fill:'#d4dbbc','font-family':'Segoe UI, Arial, sans-serif','font-size':15,'letter-spacing':4});label.textContent='MÂY & BÔNG / EPISODE 01';
  const caption=node(title,'text',{x:360,y:150,'text-anchor':'middle',fill:'#fff0d5','font-family':'Segoe UI, Arial, sans-serif','font-size':26});
  caption.textContent={read:'Một trang sách. Một ngày mưa.',share:'Chia nhau một chút ấm áp.',rest:'Bình yên ở ngay đây.'}[mood];
  const footer=node(context.canvas,'text',{x:365,y:1208,'text-anchor':'middle',fill:'#d4e4d8','font-family':'Segoe UI, Arial, sans-serif','font-size':18});footer.textContent='rừng cứ mưa · mình cứ thong thả';
  const eyelids=may.querySelector('#eyes');
  const timeline=context.timeline();
  timeline.fromTo(eyelids,{scaleY:1},{scaleY:.08,duration:.12,repeat:1,yoyo:true,transformOrigin:'50% 50%',ease:'sine.inOut'},1.5);
  const blink=bong.querySelector('#head');
  function seek(time){
    const t=Math.max(0,Math.min(5,time));timeline.time(t,true);
    const breath=Math.sin(t*Math.PI*.65);
    gsap.set(may.querySelector('#body'),{scaleY:1+.012*breath,transformOrigin:'50% 100%'});
    gsap.set(blink,{y:Math.sin(t*1.8)*1.1});
    gsap.set(may.querySelector('#tail'),{rotation:Math.sin(t*1.1)*1.8,transformOrigin:'10% 70%'});
    gsap.set(book,{rotation:mood==='read'?Math.sin(t*.7)*1.2:0,opacity:mood==='rest'?.8:1});
    const sharing=mood==='share'?Math.sin(Math.PI*t/5):0;
    gsap.set(cup,{x:329-sharing*32,y:742-sharing*38});
    gsap.set(steam,{x:-sharing*32,y:-sharing*38});
    for(const drop of drops){const y=fraction(drop.phase+t*drop.speed/1280)*1280;const x=drop.x-y*.045;drop.el.setAttribute('x1',x);drop.el.setAttribute('x2',x-1.5);drop.el.setAttribute('y1',y);drop.el.setAttribute('y2',y+drop.length);}
    for(const ripple of ripples){const age=fraction(ripple.phase+t*.52);ripple.el.setAttribute('cx',ripple.x);ripple.el.setAttribute('cy',ripple.y);ripple.el.setAttribute('rx',3+age*30);ripple.el.setAttribute('ry',1+age*7);ripple.el.setAttribute('opacity',.5*(1-age));}
    wisps.forEach((w,i)=>{const phase=fraction(t*.36+i/3);w.setAttribute('transform',`translate(${Math.sin(t*1.5+i)*3} ${-phase*15})`);w.setAttribute('opacity',.25+.55*Math.sin(phase*Math.PI));});
    title.setAttribute('opacity',String(Math.min(1,t/.7)));
    footer.setAttribute('opacity',String(.65+.15*Math.sin(t*.8)));
    // Camera is kept at identity so portrait composition and text remain stable.
  }
  seek(0);
  return {duration:5,seek,reset(){seek(0);},dispose(){timeline.kill();}};
}
