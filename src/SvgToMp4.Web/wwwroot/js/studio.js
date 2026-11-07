'use strict';
const $ = id => document.getElementById(id);
const SAMPLE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800">
  <rect width="600" height="800" fill="#fffdf7"/>
  <circle cx="445" cy="185" r="48" fill="#f2c86e"/>
  <path d="M90 315 Q125 275 166 312 Q183 279 211 308" fill="none" stroke="#9aaea0" stroke-width="5" stroke-linecap="round"/>
  <path d="M105 570 Q300 535 500 570" fill="none" stroke="#8aa67b" stroke-width="5" stroke-linecap="round"/>
  <rect x="182" y="350" width="236" height="210" rx="8" fill="#e6eccc" stroke="#526e54" stroke-width="5"/>
  <path d="M151 362 L300 228 L449 362 Z" fill="#cf795b" stroke="#526e54" stroke-width="5" stroke-linejoin="round"/>
  <path d="M272 558 V448 a28 28 0 0 1 56 0 V558" fill="#d2aa73" stroke="#526e54" stroke-width="5"/>
  <circle cx="313" cy="503" r="4" fill="#526e54"/>
  <rect x="211" y="397" width="39" height="48" rx="3" fill="#fff7db" stroke="#526e54" stroke-width="4"/>
  <path d="M230 398 V444 M212 421 H249" fill="none" stroke="#526e54" stroke-width="3"/>
  <rect x="350" y="397" width="39" height="48" rx="3" fill="#fff7db" stroke="#526e54" stroke-width="4"/>
  <path d="M369 398 V444 M351 421 H388" fill="none" stroke="#526e54" stroke-width="3"/>
  <g transform="translate(118 505)">
    <path d="M0 48 V-45" fill="none" stroke="#7b8760" stroke-width="5"/>
    <ellipse cx="0" cy="-51" rx="32" ry="43" fill="#a3b98c" stroke="#6d8d64" stroke-width="4"/>
  </g>
  <path d="M441 556 Q454 528 464 555 M459 560 Q475 523 490 554" fill="none" stroke="#7d9d6a" stroke-width="4" stroke-linecap="round"/>
  <text x="300" y="645" text-anchor="middle" font-family="Segoe UI, Arial" font-size="22" fill="#526e54">Một nơi để trở về</text>
</svg>`;
const TERMINAL = new Set(['Succeeded','Failed','Cancelled']);
let token, jobs = [], activeId = null, selectedId = null, currentTab = 'original', originalUrl = null, polling = false;
let lastSubmitted = null;
const key = 'net-studio-draft-v1';

function settings() {
    return { duration:Number($('duration').value),hold:Number($('hold').value),aspect:document.querySelector('input[name=aspect]:checked').value,hand:$('hand').value,handScale:Number($('handScale').value),effect:$('effect').value };
}
function signature() { return JSON.stringify({svg:$('svgSource').value,settings:settings()}); }
function userError(message) { return String(message).split('\n')[0].replace(/^Page\.evaluate:\s*(?:Error:\s*)?/, ''); }
function notify(message='') { $('message').textContent = userError(message); $('message').hidden = !message; }
function modeIssue() {
    if(settings().effect!=='doodle') return null;
    const doc=new DOMParser().parseFromString($('svgSource').value,'image/svg+xml');
    if(doc.querySelector('parsererror')||doc.documentElement.localName!=='svg') return {message:'Mã SVG chưa hợp lệ. Vui lòng kiểm tra lại nội dung trước khi render.',canSwitch:false};
    const groups=[...doc.getElementsByTagNameNS(doc.documentElement.namespaceURI,'g')].filter(g=>g.id==='doodles');
    if(!groups.length) return {message:'SVG này chưa có lớp nét doodle. Với file ngôi nhà và SVG thông thường, hãy dùng “Nét trước, màu sau”. Muốn thử doodle trên ảnh nền, bấm “Mẫu doodle”.',canSwitch:true};
    if(groups.length!==1||groups[0].parentElement!==doc.documentElement||groups[0].nextElementSibling) return {message:'Lớp nét doodle cần nằm riêng ở cuối SVG. Chuyển group có id="doodles" thành phần tử con cuối cùng, hoặc dùng “Nét trước, màu sau”.',canSwitch:true};
    return null;
}
function updateModeNotice() {
    const issue=modeIssue();
    $('modeNotice').hidden=!issue;
    $('modeNoticeText').textContent=issue?.message||'';
    $('useWhiteboard').hidden=!issue?.canSwitch;
    $('effect').setAttribute('aria-invalid',String(!!issue));
    if(issue) $('effect').setAttribute('aria-describedby','modeNoticeText');
    else $('effect').removeAttribute('aria-describedby');
    return issue;
}
function setTab(tab) {
    currentTab = tab;
    $('showOriginal').classList.toggle('active',tab==='original');
    $('showVideo').classList.toggle('active',tab==='video');
    $('originalImage').hidden = tab!=='original';
    $('video').hidden = tab!=='video'||!selectedId;
    const active = jobs.find(j=>j.id===activeId);
    $('renderOverlay').hidden = tab!=='video'||!active||TERMINAL.has(active.state);
    $('videoEmpty').hidden = tab!=='video'||!!selectedId||!$('renderOverlay').hidden;
    if(tab==='original') $('video').pause();
    const selected=jobs.find(j=>j.id===selectedId);
    const aspect=tab==='video'&&selected?selected.settings.aspect:settings().aspect;
    $('stage').className=`stage ${aspect}`;
    $('ratioLabel').textContent=aspect==='portrait'?'9:16':'16:9';
    if(tab==='original') $('previewLabel').textContent='SVG gốc · hình màu hoàn chỉnh';
    else if(selected) $('previewLabel').textContent=`${selected.mode==='preview'?'Xem trước':'Bản xuất'} · ${selected.width} × ${selected.height} · ${selected.fps} FPS`;
}
function updateOriginal() {
    const source=$('svgSource').value;
    if(originalUrl) URL.revokeObjectURL(originalUrl);
    originalUrl=URL.createObjectURL(new Blob([source],{type:'image/svg+xml'}));
    $('originalImage').src=originalUrl;
    $('sourceSize').textContent=`${(new Blob([source]).size/1024).toFixed(1)} KB`;
    $('scaleValue').value=`${Math.round(settings().handScale*100)}%`;
    const doodle=settings().effect==='doodle';
    $('recipeTitle').textContent=doodle?'Doodle trên ảnh nền':'Nét trước, màu sau';
    $('recipeDescription').textContent=doodle?'Giữ nguyên nền → vẽ từng nét theo màu gốc → giữ hình hoàn chỉnh.':'Vẽ đường nét → hiện dần màu gốc → giữ hình hoàn chỉnh.';
    const aspect=settings().aspect;
    $('exportSize').textContent=aspect==='portrait'?'1080 × 1920 · 30 FPS':'1920 × 1080 · 30 FPS';
    const stale=lastSubmitted&&signature()!==lastSubmitted;
    $('previewHint').textContent=stale?'Bản vẽ hoặc thiết lập đã thay đổi. Tạo lại bản xem trước để cập nhật.':'Bản xem trước dùng cùng engine, ở 540p / 15 FPS. Bản xuất là 1080p / 30 FPS.';
    $('previewHint').classList.toggle('stale',!!stale);
    updateModeNotice();
    try { localStorage.setItem(key,JSON.stringify({svg:source,name:$('projectName').value,settings:settings()})); } catch {}
    setTab(currentTab);
}
async function api(url, options={}) {
    const response=await fetch(url,{...options,headers:{'Content-Type':'application/json','X-CSRF-TOKEN':token||'',...(options.headers||{})}});
    if(!response.ok){
        const data=await response.json().catch(()=>null);
        throw Error(data?.error||data?.title||`Không thực hiện được yêu cầu (${response.status}).`);
    }
    return response.json();
}
function restore(draft) {
    $('svgSource').value=draft.svg;
    $('projectName').value=draft.name||'Bản vẽ';
    if(draft.settings){
        $('effect').value=draft.settings.effect||'whiteboard';
        for(const id of ['duration','hold','hand','handScale']) if(draft.settings[id]!==undefined) $(id).value=draft.settings[id];
        const radio=document.querySelector(`input[name=aspect][value="${draft.settings.aspect==='landscape'?'landscape':'portrait'}"]`);
        radio.checked=true;
    }
    updateOriginal();
}
async function submit(mode) {
    notify();
    const s=settings();
    if(!token){notify('Chưa kết nối được ứng dụng. Vui lòng tải lại trang.');return;}
    if(!$('svgSource').value.trim()){notify('Bạn hãy nhập hoặc tải lên một SVG.');return;}
    const modeError=updateModeNotice();
    if(modeError){notify(modeError.message);$('effect').focus();return;}
    if(!Number.isFinite(s.duration)||!Number.isFinite(s.hold)||s.duration<3||s.duration>120||s.hold<.5||s.hold>s.duration-1.5){notify('Thời lượng cần từ 3–120 giây. Giữ hình ít nhất 0,5 giây và để lại ít nhất 1,5 giây cho phần vẽ/tô màu.');return;}
    $('previewButton').disabled=$('exportButton').disabled=true;
    try {
        const job=await api('/api/renders',{method:'POST',body:JSON.stringify({svg:$('svgSource').value,name:$('projectName').value,mode,settings:s})});
        activeId=job.id;lastSubmitted=signature();
        jobs=[job,...jobs];renderJobs();setTab('video');updateOriginal();
    }catch(e){notify(e.message);}
    finally{$('previewButton').disabled=$('exportButton').disabled=false;}
}
function element(tag,text,cls) { const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e; }
function action(label,name,id) {const b=element('button',label);b.dataset.action=name;b.dataset.id=id;return b;}
function renderJobs() {
    $('jobCount').textContent=jobs.length;
    if(!jobs.length){$('jobs').replaceChildren(element('div','Chưa có video nào. Bắt đầu với bản vẽ đầu tiên của bạn.','empty-history'));return;}
    const fragment=document.createDocumentFragment();
    for(const j of jobs){
        const row=element('article',undefined,'job');row.append(element('div',j.state==='Succeeded'?'▷':'↗','job-icon'));
        const info=element('div',undefined,'job-info');info.append(element('strong',j.name));
        const when=new Intl.DateTimeFormat('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}).format(new Date(j.createdAt));
        info.append(element('p',`${j.mode==='preview'?'Xem trước':'Bản xuất'} · ${j.width} × ${j.height} · ${j.settings.duration}s · ${when}`));
        if(j.error) info.append(element('p',userError(j.error)));
        if(j.warning) info.append(element('p',j.warning));
        row.append(info);
        const state=element('div',j.stage,'job-state'+(j.state==='Failed'?' failed':''));
        if(!TERMINAL.has(j.state)){const p=element('progress');p.max=j.framesTotal;p.value=j.framesDone;state.append(p);}
        row.append(state);
        const actions=element('div',undefined,'job-actions');
        if(j.state==='Succeeded'){
            actions.append(action('Xem','view',j.id));
            const link=element('a','Tải MP4');link.href=`/api/renders/${j.id}/video?download=true`;actions.append(link);
        }
        if(!TERMINAL.has(j.state)){const cancel=action('Hủy','cancel',j.id);cancel.className='cancel';actions.append(cancel);}
        actions.append(action('Mở lại','restore',j.id));row.append(actions);fragment.append(row);
    }
    const focused=document.activeElement?.dataset?.action?{action:document.activeElement.dataset.action,id:document.activeElement.dataset.id}:null;
    $('jobs').replaceChildren(fragment);
    if(focused) $('jobs').querySelector(`button[data-id="${CSS.escape(focused.id)}"][data-action="${CSS.escape(focused.action)}"]`)?.focus({preventScroll:true});
    const active=jobs.find(j=>j.id===activeId);
    if(active){
        $('overlayStage').textContent=active.stage;
        $('overlayDetail').textContent=active.framesDone?`${active.framesDone} / ${active.framesTotal} khung hình`:'Bạn có thể tiếp tục chỉnh sửa bản vẽ.';
        if(active.state==='Succeeded'){selectVideo(active);activeId=null;}
        else if(TERMINAL.has(active.state)){if(active.error)notify(active.error);activeId=null;}
    }
    setTab(currentTab);
}
function selectVideo(job) {
    selectedId=job.id;$('video').src=`/api/renders/${job.id}/video`;
    $('previewLabel').textContent=`${job.mode==='preview'?'Xem trước':'Bản xuất'} · ${job.width} × ${job.height} · ${job.fps} FPS`;
    $('stage').className=`stage ${job.settings.aspect}`;
    $('ratioLabel').textContent=job.settings.aspect==='portrait'?'9:16':'16:9';
    setTab('video');
}
async function poll() {
    if(polling)return;polling=true;
    try{const latest=(await api('/api/renders')).filter(job=>job.kind!=='story');if(JSON.stringify(latest)!==JSON.stringify(jobs)){jobs=latest;renderJobs();}}catch(e){notify(`Mất kết nối: ${e.message}`);}finally{polling=false;}
}
async function loadFile(file) {
    if(!file)return;
    if(!file.name.toLowerCase().endsWith('.svg')||file.size>20000000){notify('Chỉ nhận file SVG tối đa 20 MB.');return;}
    $('svgSource').value=await file.text();$('projectName').value=file.name.replace(/\.svg$/i,'');notify();setTab('original');updateOriginal();
    const doc=new DOMParser().parseFromString($('svgSource').value,'image/svg+xml');
    $('effect').value=doc.querySelector('g[id="doodles"]')?'doodle':'whiteboard';updateOriginal();
}

function starterDoodles(width,height) {
    return `<g id="doodles" transform="scale(${width/360} ${height/640})" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <!-- Thay các nét mẫu dưới đây bằng doodle của bạn. Thứ tự phần tử là thứ tự vẽ. -->
    <path d="M278 450 C260 430 242 449 278 475 C314 449 296 430 278 450"/>
    <path d="M65 385 C48 367 80 352 65 333 M80 390 C65 370 97 355 82 335"/>
    <path d="M190 270 Q225 235 265 257 Q290 268 300 237" stroke-dasharray="6 6"/>
    <path d="M289 243 L301 236 L303 250"/>
    <path d="M108 206 Q108 219 99 219 Q108 219 108 232 Q108 219 117 219 Q108 219 108 206"/>
  </g>`;
}
$('chooseBackground').addEventListener('click',()=>$('backgroundInput').click());
$('useWhiteboard').addEventListener('click',()=>{$('effect').value='whiteboard';notify();updateOriginal();});
$('backgroundInput').addEventListener('change',async e=>{
    const file=e.target.files[0];if(!file)return;
    try {
        if(!['image/png','image/jpeg'].includes(file.type)||file.size>14000000)throw Error('Chọn ảnh PNG/JPEG tối đa 14 MB.');
        const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('Không đọc được ảnh.'));r.readAsDataURL(file);});
        const img=new Image();img.src=data;await img.decode();
        const w=img.naturalWidth,h=img.naturalHeight;
        if(w*h>25000000)throw Error('Ảnh nền tối đa 25 triệu pixel.');
        if(!confirm('Tạo SVG mới từ ảnh này cùng các nét doodle mẫu? Nội dung đang chỉnh sửa sẽ được thay thế.'))return;
        restore({svg:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}">\n  <image width="${w}" height="${h}" href="${data}"/>\n  ${starterDoodles(w,h)}\n</svg>`,name:file.name.replace(/\.[^.]+$/,''),settings:{...settings(),effect:'doodle',aspect:w>h?'landscape':'portrait',hand:'none'}});
        setTab('original');notify('Đã nhúng ảnh nền. SVG có các nét doodle mẫu; thay các path để vẽ theo ý bạn.');
    }catch(error){notify(error.message);}finally{e.target.value='';}
});
$('loadDoodleSample').addEventListener('click',async()=>{
    if(!confirm('Thay nội dung đang chỉnh sửa bằng mẫu doodle trên ảnh nền?'))return;
    try{const r=await fetch('/samples/doodle.svg');if(!r.ok)throw Error('Không đọc được mẫu.');restore({svg:await r.text(),name:'Doodle bình yên',settings:{...settings(),effect:'doodle',aspect:'portrait',hand:'none'}});setTab('original');notify();}catch(e){notify(e.message);}
});
$('downloadSvg').addEventListener('click',()=>{
    const url=URL.createObjectURL(new Blob([$('svgSource').value],{type:'image/svg+xml'}));
    const link=document.createElement('a');link.href=url;link.download=($('projectName').value||'ban-ve')+'.svg';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$('previewButton').addEventListener('click',()=>submit('preview'));
$('exportButton').addEventListener('click',()=>submit('export'));
$('showOriginal').addEventListener('click',()=>{setTab('original');updateOriginal();});
$('showVideo').addEventListener('click',()=>setTab('video'));
$('newProject').addEventListener('click',()=>{
    if($('svgSource').value.trim()&& !confirm('Tạo bản vẽ mới? Nội dung đang chỉnh sửa sẽ được thay bằng bản trống. Video trong lịch sử vẫn được giữ.'))return;
    restore({svg:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800">\n  \n</svg>',name:'Bản vẽ mới',settings:{...settings(),effect:'whiteboard'}});setTab('original');
});
$('loadSample').addEventListener('click',()=>{
    if($('svgSource').value!==SAMPLE&& !confirm('Thay nội dung đang chỉnh sửa bằng SVG mẫu?'))return;
    restore({svg:SAMPLE,name:'Ngôi nhà nhỏ',settings:{...settings(),effect:'whiteboard'}});setTab('original');notify();
});
let debounce;
for(const id of ['svgSource','projectName','duration','hold','hand','handScale','effect']) $(id).addEventListener('input',()=>{clearTimeout(debounce);debounce=setTimeout(updateOriginal,250);});
for(const radio of document.querySelectorAll('input[name=aspect]'))radio.addEventListener('change',updateOriginal);
$('fileInput').addEventListener('change',e=>loadFile(e.target.files[0]));
$('dropZone').addEventListener('dragover',e=>{e.preventDefault();$('dropZone').classList.add('dragging');});
$('dropZone').addEventListener('dragleave',()=>$('dropZone').classList.remove('dragging'));
$('dropZone').addEventListener('drop',e=>{e.preventDefault();$('dropZone').classList.remove('dragging');loadFile(e.dataTransfer.files[0]);});
$('jobs').addEventListener('click',async e=>{
    const button=e.target.closest('button[data-action]');if(!button)return;
    const job=jobs.find(j=>j.id===button.dataset.id);if(!job)return;
    try{
        if(button.dataset.action==='view')selectVideo(job);
        if(button.dataset.action==='cancel'){await api(`/api/renders/${job.id}/cancel`,{method:'POST'});await poll();}
        if(button.dataset.action==='restore'){
            if($('svgSource').value.trim()&&!confirm('Mở lại bản vẽ này và thay nội dung đang chỉnh sửa?'))return;
            const response=await fetch(`/api/renders/${job.id}/source`);if(!response.ok)throw Error('Không đọc được SVG.');
            restore({svg:await response.text(),name:job.name,settings:job.settings});setTab('original');notify();
        }
    }catch(error){notify(error.message);}
});
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();submit('preview');}});
(async()=>{
    try{const draft=JSON.parse(localStorage.getItem(key)||'null');restore(draft?.svg?draft:{svg:SAMPLE,name:'Ngôi nhà nhỏ'});}catch{restore({svg:SAMPLE,name:'Ngôi nhà nhỏ'});}
    try{token=(await api('/api/session')).token;await poll();}catch(e){notify(e.message);}
    setInterval(poll,1500);
})();
