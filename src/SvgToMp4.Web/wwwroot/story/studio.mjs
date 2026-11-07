import {buildTimeline,audioState} from './timeline.mjs';
const $=id=>document.getElementById(id),frame=$('storyFrame');
let token,project,plan,selected=0,currentFile='',draftFiles={},dirty=false,editorChanged=false,titleChanged=false,outputChanged=false,playing=false,playhead=0,lastTick=0,frameToken='',ready=false,pending=false,latestTime=0,messageId=0,fileRequest=0,thumbs=new Map(),audio=[],dragIndex=-1;
const terminal=s=>['Succeeded','Completed','Failed','Cancelled'].includes(s);
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);if(error)$('errorConsole').textContent=text;}
function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
function markDirty(){dirty=true;$('dirtyLabel').textContent='Chưa lưu';$('dirtyLabel').className='dirty';}
async function api(url,options={}){
    const headers={'X-CSRF-TOKEN':token||''};if(!(options.body instanceof FormData))headers['Content-Type']='application/json';
    const response=await fetch(url,{...options,headers:{...headers,...options.headers}});
    if(!response.ok){const data=await response.json().catch(()=>null);throw Error(data?.error||data?.title||`Yêu cầu thất bại (${response.status})`);}
    return response.json();
}
function cacheEditor(){if(!currentFile||!editorChanged)return;if(currentFile==='story.json'){try{project.manifest=JSON.parse($('codeEditor').value);}catch{throw Error('story.json chưa phải JSON hợp lệ.');}}else draftFiles[currentFile]=$('codeEditor').value;editorChanged=false;}
async function fileText(path){if(path==='story.json')return JSON.stringify(project.manifest,null,2);if(path in draftFiles)return draftFiles[path];const response=await fetch(`/api/stories/${project.id}/files/${path.split('/').map(encodeURIComponent).join('/')}?revision=${project.revision}`);if(!response.ok)throw Error('Không đọc được file '+path);return response.text();}
async function selectFile(path){cacheEditor();const request=++fileRequest;currentFile=path;$('fileList').value=path;const source=await fileText(path);if(request!==fileRequest)return;$('codeEditor').value=source;editorChanged=false;}
function seconds(t){const minutes=Math.floor(t/60),seconds=(t%60).toFixed(3).padStart(6,'0');return `${String(minutes).padStart(2,'0')}:${seconds}`;}
function rebuild(){plan=buildTimeline(project.manifest);project.manifest.duration=plan.duration;if(currentFile==='story.json'&&!editorChanged)$('codeEditor').value=JSON.stringify(project.manifest,null,2);$('sceneCount').textContent=plan.scenes.length+' cảnh';$('durationLabel').textContent=seconds(plan.duration);$('scrubber').max=plan.duration;renderScenes();renderTracks();}
function outputOptions(){const short=Number($('resolution').value),aspect=$('aspect').value;return {width:aspect==='portrait'?short:aspect==='square'?short:Math.round(short*16/9/2)*2,height:aspect==='landscape'?short:aspect==='square'?short:Math.round(short*16/9/2)*2,fps:Number($('fps').value),crf:Number($('crf').value),preset:project?.manifest.render?.preset||'veryfast'};}
function renderScenes(){
    $('scenes').replaceChildren();
    plan.scenes.forEach((scene,index)=>{
        const card=el('article',undefined,'scene-card'+(index===selected?' active':''));card.draggable=true;
        const image=el('img');image.alt=scene.name||scene.id;if(thumbs.has(scene.id))image.src=thumbs.get(scene.id);card.append(image,el('strong',`${index+1}. ${scene.name||scene.id}`),el('small',`${scene.duration}s · ${scene.transition.type}`));
        card.addEventListener('click',()=>chooseScene(index));
        card.addEventListener('dragstart',()=>{dragIndex=index;});card.addEventListener('dragover',e=>e.preventDefault());
        card.addEventListener('drop',e=>{e.preventDefault();if(dragIndex<0||dragIndex===index)return;cacheEditor();const scenes=project.manifest.scenes;const [moved]=scenes.splice(dragIndex,1);scenes.splice(index,0,moved);scenes.at(-1).transition={type:'cut',duration:0};selected=index;markDirty();rebuild();status('Đã đổi thứ tự. Lưu & áp dụng để cập nhật preview; cảnh cuối dùng Cut.');});
        $('scenes').append(card);
    });
}
function renderTracks(){
    $('sceneTrack').replaceChildren();$('audioTrack').replaceChildren();
    plan.scenes.forEach((scene,index)=>{const clip=el('button',`${scene.name||scene.id} · ${scene.duration}s${scene.overlap?' / '+scene.transition.type+' '+scene.overlap+'s':''}`,'clip');clip.style.left=scene.start/plan.duration*100+'%';clip.style.width=scene.duration/plan.duration*100+'%';clip.addEventListener('click',()=>chooseScene(index));$('sceneTrack').append(clip);});
    for(const track of project.manifest.audio||[]){const state=audioState(track,plan,0);const clip=el('span',track.name||track.assetId,'clip');clip.style.left=state.start/plan.duration*100+'%';clip.style.width=Math.min(track.duration,plan.duration-state.start)/plan.duration*100+'%';$('audioTrack').append(clip);}
}
async function chooseScene(index){selected=Math.max(0,Math.min(plan.scenes.length-1,index));const scene=plan.scenes[selected];renderScenes();$('sceneDuration').value=scene.duration;$('transitionType').value=scene.transition.type;$('transitionType').disabled=selected===plan.scenes.length-1;$('transitionDuration').value=scene.overlap;$('transitionDuration').disabled=selected===plan.scenes.length-1;await selectFile(scene.source);seek(scene.start);}
function setupAudio(){
    for(const entry of audio)entry.node.pause();audio=[];
    for(const track of project.manifest.audio||[]){const asset=(project.manifest.assets||[]).find(a=>a.id===track.assetId);const node=new Audio(`/api/stories/${project.id}/files/${asset.path}?revision=${project.revision}`);node.preload='auto';audio.push({track,node});}
}
function syncAudio(force=false){
    for(const {track,node} of audio){const state=audioState(track,plan,playhead);node.volume=Math.min(1,state.volume);if(force||Math.abs(node.currentTime-state.position)>.15)try{node.currentTime=state.position;}catch{}
        if(playing&&state.active&&$('audioEnabled').checked)node.play().catch(()=>status('Trình duyệt chưa cho phát âm thanh. Bấm Phát lại hoặc kiểm tra quyền âm thanh.'));else node.pause();}
}
function mountPreview(){
    pause();ready=false;pending=false;frameToken=crypto.randomUUID();
    frame.src=`http://127.0.0.1:5189/story/runtime.html?bundle=${encodeURIComponent(`/story/bundle/${project.id}/${project.revision}/`)}&token=${frameToken}`;
    frame.hidden=false;$('emptyPreview').hidden=true;
    status('Đang nạp cảnh và assets…');
    const waiting=frameToken;setTimeout(()=>{if(!ready&&frameToken===waiting)status('Preview chưa sẵn sàng. Xem Error Console; nếu thiếu GSAP hãy chạy setup.ps1, rồi tải lại project.',true);},30000);
    setupAudio();
}
function seek(time){playhead=Math.max(0,Math.min(plan?.duration||0,Number(time)||0));latestTime=playhead;$('scrubber').value=playhead;$('timeLabel').textContent=`${seconds(playhead)} / ${seconds(plan?.duration||0)}`;syncAudio(true);dispatchSeek();}
function dispatchSeek(){if(!ready||pending)return;pending=true;frame.contentWindow.postMessage({channel:'svg-story-v1',token:frameToken,command:'seek',time:latestTime,id:++messageId},'*');}
function pause(){playing=false;$('playStory').textContent='▶ Phát';for(const entry of audio)entry.node.pause();}
function tick(now){if(!playing)return;const elapsed=(now-lastTick)/1000;lastTick=now;playhead=Math.min(plan.duration,playhead+elapsed);latestTime=playhead;$('scrubber').value=playhead;$('timeLabel').textContent=`${seconds(playhead)} / ${seconds(plan.duration)}`;syncAudio();dispatchSeek();if(playhead>=plan.duration)pause();else requestAnimationFrame(tick);}
function play(){if(!project||!ready){status('Preview chưa sẵn sàng.',true);return;}if(playing){pause();return;}if(playhead>=plan.duration)seek(0);playing=true;lastTick=performance.now();$('playStory').textContent='Ⅱ Dừng';syncAudio(true);requestAnimationFrame(tick);}
addEventListener('message',event=>{
    const data=event.data;if(event.source!==frame.contentWindow||event.origin!=='null'||data?.channel!=='svg-story-v1'||data.token!==frameToken)return;
    if(data.type==='error'){pending=false;pause();status(String(data.message||'Scene lỗi').slice(0,2000),true);}
    if(data.type==='warning')$('errorConsole').textContent=String(data.message||'').slice(0,2000);
    if(data.type==='ready'){
        ready=true;status('Preview sẵn sàng. Space để phát/dừng; có thể seek trực tiếp bất kỳ thời điểm.');
        $('layers').replaceChildren(...(Array.isArray(data.layers)?data.layers:[]).slice(0,200).filter(layer=>layer&&typeof layer.id==='string').map(layer=>el('div',`${layer.scene} / ${layer.id} · ${layer.tag}`)));
        for(const item of (Array.isArray(data.thumbnails)?data.thumbnails:[]).slice(0,80)){if(item&&typeof item.id==='string'&&typeof item.svg==='string'&&item.svg.length<1_000_000){if(thumbs.has(item.id))URL.revokeObjectURL(thumbs.get(item.id));thumbs.set(item.id,URL.createObjectURL(new Blob([item.svg],{type:'image/svg+xml'})));}}
        renderScenes();seek(playhead);
    }
    if(data.type==='frame'){pending=false;if(Math.abs(data.time-latestTime)>.0001)dispatchSeek();}
});
async function listProjects(){const projects=await api('/api/stories');$('projectList').replaceChildren(el('option','Mở project đã lưu…'));$('projectList').firstChild.value='';for(const item of projects){const option=el('option',item.title);option.value=item.id;$('projectList').append(option);}if(project)$('projectList').value=project.id;}
async function loadProject(data){
    project=data;draftFiles={};currentFile='';dirty=false;editorChanged=false;titleChanged=false;outputChanged=false;thumbs.forEach(url=>URL.revokeObjectURL(url));thumbs=new Map();selected=0;
    $('storyTitle').value=project.manifest.title;$('revisionLabel').textContent='REV '+project.revision.slice(0,8);$('dirtyLabel').textContent='Đã lưu';$('dirtyLabel').className='';
    const video={...project.manifest.video,...project.manifest.render};$('fps').value=video.fps;$('crf').value=video.crf??18;$('aspect').value=video.width===video.height?'square':video.width>video.height?'landscape':'portrait';$('resolution').value=String(Math.min(video.width,video.height)>=2160?2160:Math.min(video.width,video.height)>=1080?1080:720);
    $('exportStory').href=`/api/stories/${project.id}/export`;$('exportStory').hidden=false;
    $('fileList').replaceChildren(...project.files.filter(f=>/\.(js|json|svg|html|css)$/.test(f)).map(f=>{const option=el('option',f);option.value=f;return option;}));
    $('assets').replaceChildren(...(project.manifest.characters||[]).map(a=>el('div',`Nhân vật: ${a.id} → ${a.assetId}`,'asset-row')),...(project.manifest.assets||[]).map(a=>{const row=el('div',`${a.id} · ${a.path}`,'asset-row');if(/\.(svg|js|css|html|json)$/.test(a.path))row.addEventListener('click',run(()=>selectFile(a.path)));return row;}));
    rebuild();await chooseScene(0);mountPreview();await listProjects();
}
async function save(){
    if(!project)throw Error('Chưa có project. Import ZIP hoặc tạo từ code.');cacheEditor();if(titleChanged)project.manifest.title=$('storyTitle').value;if(outputChanged){project.manifest.render=outputOptions();project.manifest.video.fps=Number($('fps').value);}
    const oldTime=playhead;const result=await api(`/api/stories/${project.id}?revision=${project.revision}`,{method:'PUT',body:JSON.stringify({manifest:project.manifest,files:draftFiles})});
    await loadProject(result);seek(Math.min(oldTime,plan.duration));return result;
}
async function importZip(file){if(!file)return;if(file.size>64000000)throw Error('ZIP tối đa 64 MB.');const form=new FormData();form.append('file',file);status('Đang kiểm tra ZIP và manifest…');await loadProject(await api('/api/stories/import',{method:'POST',body:form}));}
const run=action=>async()=>{try{await action();}catch(error){status(error.message,true);}};
$('importStory').addEventListener('click',()=>$('zipInput').click());$('zipInput').addEventListener('change',run(()=>importZip($('zipInput').files[0])));
$('importCode').addEventListener('click',()=>$('codeInput').click());
$('codeInput').addEventListener('change',run(async()=>{
    const file=$('codeInput').files[0];if(!file)return;if(file.size>1000000)throw Error('Code trực tiếp tối đa 1 MB; dùng ZIP cho project lớn.');
    const extension=file.name.split('.').pop().toLowerCase(),source=await file.text(),files={},assets=[];
    const scene={id:'scene-001',name:file.name,duration:6,source:'scenes/scene-001.js',transition:{type:'cut'}};
    if(extension==='js')files[scene.source]=source;
    else if(extension==='svg'){
        files['assets/import.svg']=source;assets.push({id:'imported-art',path:'assets/import.svg'});
        files[scene.source]="export function createScene(context){context.addSvg(context.assetText('imported-art'));return {duration:6,seek(t){},reset(){},dispose(){}};}";
    }else if(extension==='html'){
        scene.html='scenes/scene-001.html';files[scene.html]=source;
        files[scene.source]="export function createScene(context){return {duration:6,seek(t){},reset(){},dispose(){}};}";
    }else throw Error('Chỉ nhận module .js theo contract, SVG hoặc HTML/CSS.');
    await loadProject(await api('/api/stories',{method:'POST',body:JSON.stringify({manifest:{schemaVersion:'1.0',projectId:'code-'+Date.now(),title:file.name,video:{width:1280,height:720,fps:30,format:'mp4'},scenes:[scene],assets,characters:[],audio:[]},files})}));
    if(extension==='html')status('Đã import HTML/CSS. Đưa JavaScript/GSAP vào scene module; script tag trong HTML không phải lifecycle được hỗ trợ.');
}));
$('sampleStory').addEventListener('click',run(async()=>{const response=await fetch('/story/samples/lost-star.zip');if(!response.ok)throw Error('Không tìm thấy sample ZIP. Chạy python scripts/create_story_sample.py.');await importZip(new File([await response.blob()],'lost-star.zip',{type:'application/zip'}));}));
$('projectList').addEventListener('change',run(async()=>{if(!$('projectList').value)return;if(dirty&&!confirm('Mở project khác và bỏ thay đổi chưa lưu?'))return;await loadProject(await api('/api/stories/'+$('projectList').value));}));
$('saveStory').addEventListener('click',run(save));$('fileList').addEventListener('change',run(()=>selectFile($('fileList').value)));
$('codeEditor').addEventListener('input',()=>{editorChanged=true;markDirty();});$('storyTitle').addEventListener('input',()=>{titleChanged=true;markDirty();});
$('playStory').addEventListener('click',play);$('restartStory').addEventListener('click',()=>{pause();seek(0);});$('scrubber').addEventListener('input',()=>{pause();seek($('scrubber').value);});
$('backFrame').addEventListener('click',()=>{pause();seek(playhead-1/Number($('fps').value));});$('forwardFrame').addEventListener('click',()=>{pause();seek(playhead+1/Number($('fps').value));});
$('previousScene').addEventListener('click',run(()=>project&&chooseScene(selected-1)));$('nextScene').addEventListener('click',run(()=>project&&chooseScene(selected+1)));
for(const id of ['sceneDuration','transitionType','transitionDuration'])$(id).addEventListener('change',()=>{if(!project)return;try{cacheEditor();const scene=project.manifest.scenes[selected];scene.duration=Number($('sceneDuration').value);scene.transition={type:$('transitionType').value,duration:$('transitionType').value==='cut'?0:Number($('transitionDuration').value)};markDirty();rebuild();}catch(error){status(error.message,true);}});
for(const id of ['resolution','aspect','fps','crf'])$(id).addEventListener('change',()=>{if(project){outputChanged=true;markDirty();}});
$('newStory').addEventListener('click',run(async()=>{
    if(dirty&&!confirm('Tạo project mới và bỏ thay đổi chưa lưu?'))return;
    const source=`export function createScene(context) {\n  const {gsap}=context;\n  const shape=context.addSvg('<svg xmlns="http://www.w3.org/2000/svg"><circle cx="120" cy="360" r="50" fill="#a78bfa"/></svg>');\n  const timeline=context.timeline();\n  timeline.fromTo(shape,{x:0},{x:900,duration:5,ease:'sine.inOut'},0);\n  return {duration:6,seek(t){timeline.time(t,true);},reset(){timeline.pause(0);},dispose(){timeline.kill();}};\n}`;
    await loadProject(await api('/api/stories',{method:'POST',body:JSON.stringify({manifest:{schemaVersion:'1.0',projectId:'story-'+Date.now(),title:'Câu chuyện mới',seed:1,video:{width:1280,height:720,fps:30,format:'mp4'},scenes:[{id:'scene-001',name:'Cảnh đầu tiên',duration:6,source:'scenes/scene-001.js',transition:{type:'cut',duration:0}}],assets:[],characters:[],audio:[]},files:{'scenes/scene-001.js':source}})}));
}));
$('renderStory').addEventListener('click',run(async()=>{
    if(!project)throw Error('Chưa có project.');if(dirty)await save();
    await api(`/api/stories/${project.id}/render`,{method:'POST',body:JSON.stringify(outputOptions())});status('Đã xếp hàng render từ revision cố định. Bạn có thể tiếp tục chỉnh sửa.');await pollJobs();
}));
async function pollJobs(){
    const jobs=(await api('/api/renders')).filter(j=>j.kind==='story');$('storyJobs').replaceChildren();
    for(const job of jobs){const row=el('article',undefined,'story-job');row.append(el('strong',job.name),el('small',`${job.stage} · ${job.framesDone}/${job.framesTotal} frame · ${job.width}×${job.height} / ${job.fps} FPS`));
        if(!terminal(job.state)){const bar=el('progress');bar.max=job.framesTotal;bar.value=job.framesDone;row.append(bar);const cancel=el('button','Hủy');cancel.addEventListener('click',run(async()=>{await api(`/api/renders/${job.id}/cancel`,{method:'POST'});await pollJobs();}));row.append(cancel);}
        if(job.state==='Succeeded'||job.state==='Completed'){const link=el('a','Tải MP4');link.href=`/api/renders/${job.id}/video?download=true`;row.append(link);}
        if(job.error)row.append(el('small',job.error));$('storyJobs').append(row);}
}
addEventListener('keydown',event=>{
    if(event.ctrlKey&&event.key.toLowerCase()==='s'){event.preventDefault();run(save)();return;}
    if(/INPUT|TEXTAREA|SELECT/.test(event.target.tagName)||!project)return;
    if(event.code==='Space'){event.preventDefault();play();}
    if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();const step=event.key==='ArrowLeft'?-1:1;if(event.altKey)run(()=>chooseScene(selected+step))();else{pause();seek(playhead+step/Number($('fps').value));}}
});
try{token=(await api('/api/session')).token;await listProjects();await pollJobs();}catch(error){status(error.message,true);}
setInterval(()=>pollJobs().catch(()=>{}),2000);
