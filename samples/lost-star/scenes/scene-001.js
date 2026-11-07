export function createScene(context) {
  const {gsap}=context;
  context.addSvg(context.assetText('forest'));
  const cat=context.character('may',{id:'hero',x:100,y:450,scale:1});
  const star=context.addSvg(context.assetText('star'),{id:'lost-star',x:760,y:260,scale:.7});
  const caption=context.addSvg('<svg xmlns="http://www.w3.org/2000/svg"><text x="640" y="80" text-anchor="middle" fill="#fff0cf" font-family="Segoe UI, Arial" font-size="28">Mây bắt gặp một ngôi sao rơi trong khu rừng đêm.</text></svg>');
  const timeline=context.timeline();
  timeline.fromTo(caption,{opacity:0},{opacity:1,duration:1},0);
  timeline.fromTo(cat.querySelector('#eyes'),{scaleY:1},{scaleY:.1,transformOrigin:'center',duration:.12,yoyo:true,repeat:1},2);
timeline.fromTo(cat,{x:80},{x:420,duration:7,ease:'none'},0);
  timeline.fromTo(cat.querySelector('#left-arm'),{rotation:-15},{rotation:15,transformOrigin:'50% 0',duration:.5,yoyo:true,repeat:11},0);
  timeline.fromTo(star,{x:930,y:20,rotation:-30,opacity:0},{x:760,y:360,rotation:25,opacity:1,duration:5,ease:'power2.in'},1);
  timeline.fromTo(context.camera,{scale:1,x:0},{scale:1.07,x:-30,duration:8},0);
  return {duration:9,seek(time){timeline.time(time,true);},reset(){timeline.pause(0);},dispose(){timeline.kill();}};
}
