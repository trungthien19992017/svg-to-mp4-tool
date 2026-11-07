export function createScene(context) {
  const {gsap}=context;
  context.addSvg(context.assetText('forest'));
  const cat=context.character('may',{id:'hero',x:100,y:450,scale:1});
  const star=context.addSvg(context.assetText('star'),{id:'lost-star',x:760,y:260,scale:.7});
  const caption=context.addSvg('<svg xmlns="http://www.w3.org/2000/svg"><text x="640" y="80" text-anchor="middle" fill="#fff0cf" font-family="Segoe UI, Arial" font-size="28">Mây đi theo ánh sáng, tìm thấy ngôi sao buồn.</text></svg>');
  const timeline=context.timeline();
  timeline.fromTo(caption,{opacity:0},{opacity:1,duration:1},0);
  timeline.fromTo(cat.querySelector('#eyes'),{scaleY:1},{scaleY:.1,transformOrigin:'center',duration:.12,yoyo:true,repeat:1},2);
timeline.set(cat,{x:420},0);
  timeline.fromTo(cat,{x:420},{x:660,duration:6,ease:'sine.inOut'},0);
  timeline.fromTo(star,{x:760,y:360},{x:810,y:460,duration:5,ease:'sine.inOut'},0);
  timeline.fromTo(star,{rotation:-10},{rotation:10,duration:1,yoyo:true,repeat:5},0);
  timeline.fromTo(context.camera,{scale:1.07,x:-30},{scale:1.17,x:-100,duration:8},0);
  return {duration:9,seek(time){timeline.time(time,true);},reset(){timeline.pause(0);},dispose(){timeline.kill();}};
}
