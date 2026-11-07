export function createScene(context) {
  const {gsap}=context;
  context.addSvg(context.assetText('forest'));
  const cat=context.character('may',{id:'hero',x:100,y:450,scale:1});
  const star=context.addSvg(context.assetText('star'),{id:'lost-star',x:760,y:260,scale:.7});
  const caption=context.addSvg('<svg xmlns="http://www.w3.org/2000/svg"><text x="640" y="80" text-anchor="middle" fill="#fff0cf" font-family="Segoe UI, Arial" font-size="28">Ngôi sao trở về bầu trời; Mây vẫy tay chào.</text></svg>');
  const timeline=context.timeline();
  timeline.fromTo(caption,{opacity:0},{opacity:1,duration:1},0);
  timeline.fromTo(cat.querySelector('#eyes'),{scaleY:1},{scaleY:.1,transformOrigin:'center',duration:.12,yoyo:true,repeat:1},2);
timeline.set(cat,{x:650},0);timeline.set(star,{x:1040,y:120,scale:.55},0);
  timeline.fromTo(cat.querySelector('#right-arm'),{rotation:-90},{rotation:-125,transformOrigin:'50% 0',duration:.4,yoyo:true,repeat:15},0);
  timeline.fromTo(star,{rotation:-8},{rotation:8,duration:1,yoyo:true,repeat:7},0);
  timeline.fromTo(context.camera,{scale:1.05,x:0},{scale:1,x:0,duration:8},0);
  return {duration:9,seek(time){timeline.time(time,true);},reset(){timeline.pause(0);},dispose(){timeline.kill();}};
}
