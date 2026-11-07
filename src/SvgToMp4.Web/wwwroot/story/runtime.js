import {buildTimeline,locate,seeded} from './timeline.mjs';
const stage=document.getElementById('stage');
const query=new URLSearchParams(location.search),token=query.get('token')||'';
const nativeFetch=window.fetch.bind(window);
const post=(type,data={})=>parent!==window&&parent.postMessage({channel:'svg-story-v1',token,type,...data},'*');
const textError=e=>String(e?.message||e).split('\n')[0];
const gsap=window.gsap;
const SVG='http://www.w3.org/2000/svg';
let renderer;
function stopAutoplay(){gsap.ticker.sleep();gsap.ticker.wake=()=>{};}
function controlledGsap(){
    const create=gsap.timeline.bind(gsap);
    gsap.timeline=options=>{
        const timeline=create({...options,paused:true});
        for(const method of ['time','totalTime','seek']){
            const original=timeline[method];
            timeline[method]=function(value){return arguments.length?original.call(this,value,true):original.call(this);};
        }
        return timeline;
    };
    stopAutoplay();
    window.fetch=()=>{throw Error('Scene không được gọi network. Dùng context.assets.');};
    for(const key of ['setTimeout','setInterval','requestAnimationFrame'])window[key]=()=>{throw Error(`${key} không được dùng trong scene. Hãy dùng timeline có seek.`);};
    const NativeDate=Date;window.Date=class extends NativeDate{constructor(...args){super(...(args.length?args:[0]));}static now(){return 0;}};
    try{Object.defineProperty(performance,'now',{value:()=>0});}catch{}
    Math.random=()=>{throw Error('Dùng context.random() với seed cố định.');};
    for(const key of ['WebSocket','XMLHttpRequest','Worker','SharedWorker','EventSource','WebTransport','RTCPeerConnection','webkitRTCPeerConnection'])window[key]=function(){throw Error(`${key} bị tắt trong scene.`);};
    window.open=()=>{throw Error('Scene không được mở cửa sổ mới.');};
}
function svgMarkup(markup){
    const doc=new DOMParser().parseFromString(markup,'image/svg+xml');
    if(doc.querySelector('parsererror')||doc.documentElement.localName!=='svg')throw Error('Asset SVG không hợp lệ.');
    if(doc.querySelector('script,foreignObject')||[...doc.querySelectorAll('*')].some(e=>[...e.attributes].some(a=>a.name.toLowerCase().startsWith('on'))))throw Error('SVG asset chứa active content.');
    return doc.documentElement;
}
export class StoryRenderer {
    constructor(manifest,bundle){this.manifest=manifest;this.bundle=bundle;this.timeline=buildTimeline(manifest);this.instances=[];this.assets=new Map();this.time=0;}
    url(path){
        const url=new URL(path,this.bundle);
        if(url.origin!==this.bundle.origin||!url.pathname.startsWith(this.bundle.pathname)||/[?#]/.test(path))throw Error('Asset nằm ngoài project.');
        return url.href;
    }
    async initialize(){
        const {width,height}=this.manifest.video;stage.style.width=width+'px';stage.style.height=height+'px';
        stage.replaceChildren();
        for(const asset of this.manifest.assets||[]){
            const response=await nativeFetch(this.url(asset.path));if(!response.ok)throw Error(`Thiếu asset: ${asset.path}`);
            this.assets.set(asset.id,{...asset,bytes:await response.arrayBuffer()});
        }
        for(const asset of this.assets.values())if(/\.(woff2|ttf)$/i.test(asset.path)){
            const font=new FontFace(asset.family||asset.id,asset.bytes);await font.load();document.fonts.add(font);
        }
        controlledGsap();
        for(const scene of this.timeline.scenes){
            const root=document.createElement('section');root.className='story-scene';root.dataset.scene=scene.id;
            const cameraRoot=document.createElement('div');cameraRoot.className='story-camera';root.append(cameraRoot);stage.append(root);
            const canvas=document.createElementNS(SVG,'svg');canvas.classList.add('story-vector');canvas.setAttribute('viewBox',`0 0 ${width} ${height}`);cameraRoot.append(canvas);
            const camera={x:0,y:0,scale:1,rotation:0};let follow=null;
            const assetText=id=>{const a=this.assets.get(id);if(!a)throw Error(`${scene.id}: thiếu asset ${id}`);return new TextDecoder().decode(a.bytes);};
            const addSvg=(markup,options={})=>{
                const svg=svgMarkup(markup),group=document.createElementNS(SVG,'g');
                if(options.id)group.id=options.id;
                for(const child of [...svg.childNodes])group.append(document.importNode(child,true));
                (options.parent||canvas).append(group);
                gsap.set(group,{x:options.x||0,y:options.y||0,scale:options.scale??1,transformOrigin:'center center'});return group;
            };
            const context={root:cameraRoot,sceneRoot:root,canvas,gsap,width,height,duration:scene.duration,sceneId:scene.id,
                random:seeded((this.manifest.seed||1)+this.instances.length*1009),
                noise:index=>seeded((this.manifest.seed||1)+Number(index)*1009)(),
                camera,assetText,assetUrl:id=>{const a=this.assets.get(id);if(!a)throw Error(`Thiếu asset ${id}`);return this.url(a.path);},
                addSvg,svg:markup=>addSvg(markup),timeline:(options={})=>{const {nested,...vars}=options;const timeline=gsap.timeline({...vars,paused:true});if(nested)timeline.paused(false);return timeline;},
                follow:target=>{follow=target;},
                stroke:target=>{for(const p of (typeof target==='string'?cameraRoot.querySelectorAll(target):[target])){const length=p.getTotalLength();p.style.strokeDasharray=`${length} ${length}`;p.style.strokeDashoffset=length;}return target;},
                character:(id,options={})=>{
                    const character=(this.manifest.characters||[]).find(c=>c.id===id);if(!character)throw Error(`Nhân vật chưa khai báo: ${id}`);
                    const node=addSvg(assetText(character.assetId),options);node.dataset.character=id;
                    if(!character.parts?.length)post('warning',{message:`${scene.id}: nhân vật ${id} chưa khai báo rig parts. Có thể animate toàn bộ nhân vật; chưa xác nhận điều khiển từng bộ phận.`});
                    return node;
                }
            };
            try{
                if(scene.css){const style=document.createElement('style');style.textContent=await(await nativeFetch(this.url(scene.css))).text();root.append(style);}
                if(scene.html){const template=document.createElement('div');template.innerHTML=await(await nativeFetch(this.url(scene.html))).text();cameraRoot.append(template);}
                const module=await import(this.url(scene.source));
                const scope=gsap.context(()=>{},cameraRoot);
                let pending;scope.add(()=>{pending=module.createScene(context);});
                const implementation=await pending;
                if(!implementation||!['seek','reset','dispose'].every(k=>typeof implementation[k]==='function')||!Number.isFinite(implementation.duration)||implementation.duration<=0)throw Error('Scene cần duration, seek, reset và dispose theo contract v1.');
                const apply=t=>{
                    implementation.seek(t*implementation.duration/scene.duration);
                    let x=camera.x,y=camera.y;
                    if(follow){const box=follow.getBBox();x=width/2-(box.x+box.width/2+Number(gsap.getProperty(follow,'x')));y=height/2-(box.y+box.height/2+Number(gsap.getProperty(follow,'y')));}
                    cameraRoot.style.transform=`translate(${x}px,${y}px) rotate(${camera.rotation}deg) scale(${camera.scale})`;
                    for(const svg of cameraRoot.querySelectorAll('svg')){svg.pauseAnimations();svg.setCurrentTime(t);}
                    for(const animation of cameraRoot.getAnimations({subtree:true})){animation.pause();animation.currentTime=t*1000;}
                    stopAutoplay();
                };
                this.instances.push({scene,root,implementation,scope,apply});
            }catch(error){throw Error(`${scene.id}: ${textError(error)}`);}
        }
        await document.fonts.ready;
        await Promise.all([...stage.querySelectorAll('img')].map(image=>image.decode()));
        this.seek(0);this.resize();
        addEventListener('resize',()=>this.resize());
        return this;
    }
    resize(){const v=this.manifest.video,scale=Math.min(innerWidth/v.width,innerHeight/v.height);stage.style.transform=`translate(${(innerWidth-v.width*scale)/2}px,${(innerHeight-v.height*scale)/2}px) scale(${scale})`;}
    seek(time){
        this.time=Math.min(this.timeline.duration,Math.max(0,Number(time)||0));
        const active=locate(this.timeline,this.time);
        for(const item of this.instances){item.root.style.visibility='hidden';item.root.style.opacity='1';item.root.style.transform='none';}
        for(const {scene,local} of active){
            const item=this.instances.find(i=>i.scene.id===scene.id);item.root.style.visibility='visible';
            try{item.apply(local);}catch(error){throw Error(`${scene.id} @ ${local.toFixed(3)}s: ${textError(error)}`);}
        }
        if(active.length===2){
            const outgoing=active[0].scene,incoming=active[1].scene;
            const value=(this.time-incoming.start)/Math.max(.000001,outgoing.overlap);
            const a=this.instances.find(i=>i.scene.id===outgoing.id).root,b=this.instances.find(i=>i.scene.id===incoming.id).root;
            if(outgoing.transition.type==='fade')b.style.opacity=String(value);
            if(outgoing.transition.type==='slide'){a.style.transform=`translateX(${-value*100}%)`;b.style.transform=`translateX(${(1-value)*100}%)`;}
        }
        // Force style/layout completion. Screenshot waits for compositor; no guessed sleep.
        stage.getBoundingClientRect();return {time:this.time,scenes:active.map(a=>a.scene.id)};
    }
    async readyFrame(time){this.seek(time);await document.fonts.ready;return this.seek(time);}
    layers(){return [...stage.querySelectorAll('[id]')].slice(0,200).map(e=>({id:e.id,tag:e.localName,scene:e.closest('[data-scene]')?.dataset.scene}));}
    thumbnails(){
        const previous=this.time;const result=[];
        for(const item of this.instances){this.seek(item.scene.start+Math.min(1,item.scene.duration/2));const svg=item.root.querySelector('svg');if(svg)result.push({id:item.scene.id,svg:new XMLSerializer().serializeToString(svg)});}
        this.seek(previous);return result;
    }
    dispose(){for(const item of this.instances){try{item.implementation.dispose();item.scope.revert();}catch{}}gsap.globalTimeline.clear();stage.replaceChildren();}
}
async function boot(){
    if(parent===window&&location.hostname!=='story.invalid')throw Error('Preview cần được mở từ Story Studio, không chạy độc lập trong origin của ứng dụng.');
    if(!gsap)throw Error('Chưa cài GSAP. Chạy setup.ps1 để tải thư viện local.');
    if(window.MotionPathPlugin)gsap.registerPlugin(window.MotionPathPlugin);
    if(window.MorphSVGPlugin)gsap.registerPlugin(window.MorphSVGPlugin);
    const bundle=new URL(query.get('bundle')||'/bundle/',location.href);
    if(bundle.origin!==location.origin)throw Error('Bundle phải nằm trong cùng renderer origin.');
    const response=await nativeFetch(new URL('story.json',bundle));if(!response.ok)throw Error('Không đọc được story.json.');
    renderer=await new StoryRenderer(await response.json(),bundle).initialize();
    window.storyRenderer=renderer;
    post('ready',{duration:renderer.timeline.duration,layers:renderer.layers(),thumbnails:renderer.thumbnails()});
    return renderer;
}
window.storyReady=boot().catch(error=>{stage.className='runtime-fault';stage.textContent=textError(error);post('error',{message:textError(error)});throw error;});
addEventListener('message',async event=>{
    if(event.source!==parent||event.origin!=='http://127.0.0.1:5188'||event.data?.channel!=='svg-story-v1'||event.data.token!==token)return;
    const {command,id,time}=event.data;
    try{
        await window.storyReady;
        if(command==='seek')post('frame',{id,...await renderer.readyFrame(time)});
        if(command==='dispose')renderer.dispose();
    }catch(error){post('error',{id,message:textError(error)});}
});
