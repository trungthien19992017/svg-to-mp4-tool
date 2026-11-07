export function buildTimeline(manifest){
    let start=0;
    const scenes=manifest.scenes.map((scene,index,array)=>{
        const duration=Number(scene.duration);
        if(!Number.isFinite(duration)||duration<=0)throw Error(`${scene.id}: thời lượng không hợp lệ`);
        const type=scene.transition?.type||'cut';
        if(!['cut','fade','slide'].includes(type))throw Error(`${scene.id}: transition không hỗ trợ`);
        const overlap=type==='cut'?0:Number(scene.transition?.duration??.5);
        if(!Number.isFinite(overlap)||overlap<0||overlap>duration/2||(index<array.length-1&&overlap>Number(array[index+1].duration)/2)||(index===array.length-1&&overlap!==0))throw Error(`${scene.id}: overlap không hợp lệ`);
        const item={...scene,start,end:start+duration,overlap,transition:{type,duration:overlap}};
        start+=duration-overlap;return item;
    });
    return {scenes,duration:start};
}
export function locate(timeline,time){
    const t=Math.min(timeline.duration,Math.max(0,Number(time)||0));
    return timeline.scenes.filter((s,i)=>t>=s.start&&(t<s.end||(t===timeline.duration&&i===timeline.scenes.length-1))).map(s=>({scene:s,local:Math.min(s.duration,t-s.start)}));
}
export function audioState(track,timeline,time){
    const scene=track.sceneId?timeline.scenes.find(s=>s.id===track.sceneId):null;
    const start=(scene?.start||0)+Number(track.start||0),local=time-start,duration=Number(track.duration);
    const inside=local>=0&&local<duration&&time<timeline.duration;
    let gain=Number(track.volume??1);
    if(track.fadeIn)gain*=Math.min(1,Math.max(0,local/track.fadeIn));
    if(track.fadeOut)gain*=Math.min(1,Math.max(0,(duration-local)/track.fadeOut));
    return {active:inside,position:Number(track.offset||0)+Math.max(0,local),volume:inside?gain:0,start};
}
export function seeded(seed=1){let state=(Number(seed)||1)>>>0;return()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};}
