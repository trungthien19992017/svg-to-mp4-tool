const $ = id => document.getElementById(id);
let token = '', kit, spec, selectionSequence = 0;
const clone = value => structuredClone(value);
function status(text, error = false) {$('status').textContent = text; $('status').classList.toggle('error', error);}
function element(tag, text, cls) {const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node;}
async function api(path, options = {}) {
  const headers = {'X-CSRF-TOKEN': token};
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(path, {...options, headers});
  if (!response.ok) {const error = await response.json().catch(() => ({})); throw Error(error.error || error.title || 'Yêu cầu thất bại: ' + response.status);}
  return response.json();
}
function run(action) {return async event => {
  const button = event?.currentTarget; if (button?.tagName === 'BUTTON') button.disabled = true;
  try {await action();} catch (error) {if(kit)$('kitList').value=kit.id+'@'+kit.version;status(error.message, true);}
  finally {if (button?.tagName === 'BUTTON') button.disabled = false;}
};}
const base = () => '/api/production-kits/' + encodeURIComponent(kit.id) + '/' + encodeURIComponent(kit.version);
const supported = kind => kit.catalogs[kind].filter(item => item.status === 'Supported' || (kit.manifest.testOnly === true && item.status === 'Partial'));
function persist() {
  if (!kit || !spec) return;
  try {localStorage.setItem('episode-draft:' + kit.digest, JSON.stringify(spec)); $('draftStatus').textContent = 'Bản nháp tự lưu trên trình duyệt này. Kit ' + kit.id + ' · v' + kit.version;}
  catch {$('draftStatus').textContent = 'Không lưu được bản nháp trên trình duyệt. Hãy dùng Lưu kịch bản JSON.';}
}
function firstActor() {
  const motion = supported('motions').find(m => supported('poses').some(p => p.id === m.startPose) && supported('poses').some(p => p.id === m.endPose));
  if (!supported('poses').length || !supported('characters').length || !supported('expressions').length) throw Error('Kit chưa đủ character, pose và expression Supported để tạo cảnh.');
  return {id:'actor-1', character:supported('characters')[0].id, pose:motion?.startPose || supported('poses')[0].id, expression:supported('expressions')[0].id, motion:motion?.id || '', x:0, y:0, scale:1};
}
function freshScene() {
  const actor = firstActor(); const motion = supported('motions').find(m => m.id === actor.motion);
  const ids = new Set(spec?.scenes.map(s => s.id) || []); let n = 1; while (ids.has('scene-' + n)) n++;
  return {id:'scene-' + n, name:'Cảnh ' + n, duration:motion?.duration || 4, caption:'', actors:[actor], transition:{type:'cut', duration:0}};
}
function validateShape(value) {
  if (!value || value.schemaVersion !== 'episode-1' || typeof value.id !== 'string' || typeof value.title !== 'string' || !Array.isArray(value.scenes) || value.scenes.length < 1 || value.scenes.length > 80) throw Error('JSON cần episode-1, id, title và 1–80 scenes.');
  for (const scene of value.scenes) {
    if (!scene || typeof scene.id !== 'string' || !Number.isFinite(scene.duration) || !Array.isArray(scene.actors) || scene.actors.length < 1 || scene.actors.length > 8) throw Error('Mỗi cảnh cần id, duration và 1–8 actors.');
    for (const actor of scene.actors) if (!actor || ['id','character','pose','expression','motion'].some(k => typeof actor[k] !== 'string')) throw Error('Actor cần id, character, pose, expression và motion.');
  }
  return value;
}
async function listKits(selected = '') {
  const records = await api('/api/production-kits'); const options = [element('option', 'Chọn Production Kit…')]; options[0].value = '';
  for (const record of records) {const option = element('option', record.title + ' · v' + record.version + (record.demo ? ' · MINH HỌA' : '')); option.value = record.id + '@' + record.version; options.push(option);}
  $('kitList').replaceChildren(...options); $('kitList').value = selected;
}
async function selectKit(id, version, importedSpec) {
  const selection = ++selectionSequence;
  const nextKit = await api('/api/production-kits/' + encodeURIComponent(id) + '/' + encodeURIComponent(version));
  if (selection !== selectionSequence) return;
  for(const kind of ['characters','poses','expressions'])if(!nextKit.catalogs[kind].some(c=>c.status==='Supported'||(nextKit.manifest.testOnly===true&&c.status==='Partial')))throw Error('Kit chưa có '+kind+' phù hợp. Hãy hoàn thiện catalog trước khi tạo tập.');
  if (importedSpec && importedSpec.kitDigest && importedSpec.kitDigest !== nextKit.digest) throw Error('Hash kit trong kịch bản không khớp. Không tự đổi dependency.');
  persist(); kit = nextKit;
  let restored;
  if (!importedSpec) try {restored = validateShape(JSON.parse(localStorage.getItem('episode-draft:' + kit.digest)));} catch {}
  spec = importedSpec ? clone(importedSpec) : restored || {schemaVersion:'episode-1', kitId:id, kitVersion:version, kitDigest:kit.digest, id:'episode-' + Date.now(), title:'Tập mới', video:clone(kit.manifest.video || {width:720,height:1280,fps:24,format:'mp4'}), scenes:[]};
  if(kit.manifest.testOnly===true)spec.allowExperimental=true;
  if(!spec.scenes.length && kit.manifest.defaultTemplate){const template=kit.catalogs.templates.find(t=>t.id===kit.manifest.defaultTemplate);if(template)spec.scenes=clone(template.scenes);}
  if (!spec.scenes.length) spec.scenes.push(freshScene());
  const options = [element('option', 'Chọn mẫu trong kit…')]; options[0].value = '';
  for (const template of kit.catalogs.templates) {const option = element('option', template.title || template.id); option.value = template.id; options.push(option);}
  $('template').replaceChildren(...options); $('workspace').hidden = false; $('kitList').value = id + '@' + version;
  $('kitSummary').textContent = (kit.manifest.testOnly ? 'KIT THỬ NGHIỆM · Có capability Partial, chưa nghiệm thu production · ' : kit.manifest.demo || kit.manifest.schemaVersion === 'demo-1' ? 'KIT MINH HỌA · ' : '') +
    supported('characters').length + ' nhân vật · ' + supported('poses').length + ' pose · ' + supported('expressions').length + ' biểu cảm · ' + supported('motions').length + (kit.manifest.testOnly ? ' motion cho bản thử' : ' motion Supported');
  $('generate').textContent=kit.manifest.testOnly?'Tạo bản thử & mở Studio →':'Tạo tập & mở Studio →';
  render(); persist(); status(importedSpec ? 'Đã nạp kịch bản. Bạn có thể chỉnh sửa trước khi tạo tập.' : restored ? 'Đã khôi phục bản nháp của kit này.' : 'Kit sẵn sàng. Thêm cảnh hoặc chọn mẫu để bắt đầu.');
  try {localStorage.setItem('episode-last-kit', JSON.stringify({id,version}));} catch {}
}
function label(title, control) {const node = element('label', title); node.append(control); return node;}
function input(title, value, change, type = 'text') {
  const control = element('input'); control.type = type; control.value = value ?? ''; control.addEventListener('input', () => {change(type === 'number' ? Number(control.value) : control.value); persist();});
  if (type === 'number') control.step = 'any'; return label(title, control);
}
function pick(title, records, value, change, optional = false) {
  const control = element('select');
  if (optional) {const option = element('option', 'Không sử dụng'); option.value = ''; control.append(option);}
  for (const record of records) {const option = element('option', record.label || record.title || record.id); option.value = record.id; control.append(option);}
  if (value && !records.some(r => r.id === value)) {const option = element('option', value + ' · chưa Supported / không tồn tại'); option.value = value; control.append(option);}
  control.value = value || ''; control.addEventListener('change', () => {change(control.value); persist();}); return label(title, control);
}
function button(title, action, cls) {const node = element('button', title, cls); node.addEventListener('click', run(action)); return node;}
function render() {
  $('title').value = spec.title; $('episodeId').value = spec.id;
  const v = spec.video || kit.manifest.video || {width:720,height:1280,fps:24,format:'mp4'}; spec.video = clone(v);
  $('video').value = v.width === 720 && v.height === 1280 ? 'portrait' : v.width === 1280 && v.height === 720 ? 'landscape' : v.width === 1080 && v.height === 1080 ? 'square' : 'custom';
  $('scenes').replaceChildren();
  spec.scenes.forEach((scene, index) => {
    const card = element('article', undefined, 'scene'); const heading = element('div', undefined, 'scene-heading');
    const actions = element('div', undefined, 'controls');
    if (index > 0) actions.append(button('↑', () => {const previous = spec.scenes[index-1]; spec.scenes[index-1] = scene; spec.scenes[index] = previous; render(); persist();}));
    if (index < spec.scenes.length-1) actions.append(button('↓', () => {const next = spec.scenes[index+1]; spec.scenes[index+1] = scene; spec.scenes[index] = next; render(); persist();}));
    actions.append(button('Nhân bản cảnh', () => {if(spec.scenes.length >= 80) throw Error('Tối đa 80 cảnh.'); const ids = new Set(spec.scenes.map(s=>s.id));let n=1;while(ids.has('scene-'+n))n++;const copy=clone(scene);copy.id='scene-'+n;spec.scenes.splice(index+1,0,copy);render();persist();}), button('Xóa cảnh', () => {if (spec.scenes.length <= 1) throw Error('Giữ ít nhất một cảnh.'); spec.scenes.splice(index,1); render(); persist();}, 'danger'));
    heading.append(element('h3', 'Cảnh ' + (index+1)), actions); card.append(heading);
    const fields = element('div', undefined, 'fields');
    fields.append(input('Tên cảnh', scene.name || scene.id, value => scene.name=value), input('Mã cảnh', scene.id, value => scene.id=value), input('Thời lượng (giây)', scene.duration, value => scene.duration=value, 'number')); card.append(fields);
    scene.actors.forEach((actor, ai) => {
      const panel = element('div', undefined, 'actor'), fields = element('div', undefined, 'actor-fields');
      fields.append(pick('Nhân vật', supported('characters'), actor.character, value=>actor.character=value),
        pick('Biểu cảm', supported('expressions'), actor.expression, value=>actor.expression=value),
        pick('Chuyển động (trống = giữ pose)', supported('motions'), actor.motion, value=>{actor.motion=value;if(value)actor.pose=supported('motions').find(m=>m.id===value).startPose;render();}, true),
        pick('Pose bắt đầu', supported('poses'), actor.pose, value=>actor.pose=value));
      const placement = element('div', undefined, 'placement');
      placement.append(input('Vị trí X', actor.x ?? 0, value=>actor.x=value, 'number'), input('Vị trí Y', actor.y ?? 0, value=>actor.y=value, 'number'), input('Tỷ lệ', actor.scale ?? 1, value=>actor.scale=value, 'number'),
        button('Bỏ nhân vật ' + (ai+1), () => {if(scene.actors.length<=1)throw Error('Giữ ít nhất một nhân vật.');scene.actors.splice(ai,1);render();persist();}));
      panel.append(fields, placement); card.append(panel);
    });
    card.append(button('＋ Thêm nhân vật', () => {if(scene.actors.length>=8)throw Error('Tối đa 8 nhân vật/cảnh.');const actor=firstActor();let n=1;while(scene.actors.some(a=>a.id==='actor-'+n))n++;actor.id='actor-'+n;scene.actors.push(actor);render();persist();}));
    const extra = element('div', undefined, 'fields scene-extra');
    extra.append(input('Chữ hiện trên video (tùy chọn)', scene.caption || '', value=>scene.caption=value),
      pick('Bối cảnh', supported('environments'), scene.environment || '', value=>scene.environment=value, true),
      pick('Âm thanh', supported('audio'), scene.audio || '', value=>scene.audio=value, true)); card.append(extra);
    const transitions = element('div', undefined, 'fields scene-extra');
    transitions.append(pick('Chuyển cảnh đi ra', [{id:'cut',label:'Cắt cảnh'},{id:'fade',label:'Mờ chồng'},{id:'slide',label:'Trượt'}], scene.transition?.type || 'cut', value=>{scene.transition={type:value,duration:value==='cut'?0:.5};render();}),
      input('Thời gian chồng cảnh', scene.transition?.duration ?? 0, value=>{scene.transition ||= {type:'cut'};scene.transition.duration=value;}, 'number'),
      input('Âm lượng (0–1)', scene.volume ?? .4, value=>scene.volume=value, 'number')); card.append(transitions);
    if(index===spec.scenes.length-1)card.append(element('p','Cảnh cuối cần chuyển cảnh “Cắt cảnh”.','muted small'));
    $('scenes').append(card);
  });
}
function download(name, text, mime = 'application/json') {const url=URL.createObjectURL(new Blob([text],{type:mime}));const link=element('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function importKit(file) {
  if (!file || file.size > 64000000) throw Error('Chọn Kit ZIP không quá 64 MB.');
  status('Đang kiểm tra kit và module…'); const body=new FormData();body.append('file',file);
  const result=await api('/api/production-kits/import',{method:'POST',body});
  if(result.kind==='story'){status('Đây là Story ZIP. Đã nhập đúng luồng; đang mở Storyboard…');location.assign('/?project='+encodeURIComponent(result.project.id));return;}
  await listKits(result.id+'@'+result.version);await selectKit(result.id,result.version);
  if(result.converted)status(result.message);
}
$('importKit').onclick=()=>$('kitFile').click();$('kitFile').onchange=run(async()=>{try{await importKit($('kitFile').files[0]);}finally{$('kitFile').value='';}});
$('sampleKit').onclick=run(async()=>{const response=await fetch('/episodes/production-kit-demo.zip');if(!response.ok)throw Error('Không tìm thấy kit minh họa.');await importKit(new File([await response.blob()],'production-kit-demo.zip'));});
$('kitList').onchange=run(async()=>{const [id,version]=$('kitList').value.split('@');if(id)await selectKit(id,version);});
$('title').oninput=()=>{spec.title=$('title').value;persist();};$('episodeId').oninput=()=>{spec.id=$('episodeId').value;persist();};
$('video').onchange=()=>{const dims={portrait:[720,1280],landscape:[1280,720],square:[1080,1080]}[$('video').value];if(dims)spec.video={...spec.video,width:dims[0],height:dims[1],format:'mp4'};persist();};
$('addScene').onclick=run(()=>{if(spec.scenes.length>=80)throw Error('Tối đa 80 cảnh.');spec.scenes.push(freshScene());render();persist();});
$('applyTemplate').onclick=run(()=>{const template=kit.catalogs.templates.find(t=>t.id===$('template').value);if(!template)throw Error('Chọn mẫu trước.');const next={...clone(spec),scenes:clone(template.scenes)};validateShape(next);spec=next;render();persist();status('Đã áp dụng mẫu. Bạn có thể chỉnh từng cảnh.');});
$('loadJson').onclick=()=>$('jsonFile').click();$('jsonFile').onchange=run(async()=>{try{const file=$('jsonFile').files[0];if(!file||file.size>1000000)throw Error('JSON tối đa 1 MB.');const value=validateShape(JSON.parse(await file.text()));await selectKit(value.kitId,value.kitVersion,value);}finally{$('jsonFile').value='';}});
$('downloadJson').onclick=run(()=>{validateShape(spec);download((spec.id||'episode')+'.json',JSON.stringify(spec,null,2));status('Đã xuất kịch bản JSON.');});
$('copyBrief').onclick=run(async()=>{const response=await fetch(base()+'/brief');if(!response.ok)throw Error('Không lấy được hướng dẫn.');const text=await response.text();try{await navigator.clipboard.writeText(text);status('Đã sao chép. Dán vào cuộc trò chuyện cùng ý tưởng của bạn; sau đó nhập JSON được soạn vào đây.');}catch{download('episode-ai-brief.txt',text,'text/plain');status('Đã tải hướng dẫn cho AI thành file văn bản.');}});
$('clone').onclick=run(async()=>{const id=$('previous').value;if(!id)throw Error('Chọn tập đã tạo.');const previous=validateShape(await api('/api/production-kits/recipes/'+encodeURIComponent(id)));previous.id='episode-'+Date.now();previous.title+=' — bản mới';await selectKit(previous.kitId,previous.kitVersion,previous);});
$('generate').onclick=run(async()=>{validateShape(spec);persist();status('Đang kiểm tra và tạo project…');const project=await api(base()+'/episodes',{method:'POST',body:JSON.stringify(spec)});location.assign('/?project='+encodeURIComponent(project.id));});
try {
  token=(await api('/api/session')).token;await listKits();
  const stories=await api('/api/stories');for(const story of stories.filter(s=>s.files?.includes('metadata/episode.json'))){const option=element('option',story.title);option.value=story.id;$('previous').append(option);}
  status('Nhập Production Kit của bạn, hoặc chọn kit minh họa để bắt đầu.');
  let last;try{last=JSON.parse(localStorage.getItem('episode-last-kit'));}catch{}
  const requestedKit=new URLSearchParams(location.search).get('kit');
  if(requestedKit && [...$('kitList').options].some(o=>o.value===requestedKit)){const [id,version]=requestedKit.split('@');await selectKit(id,version);}
  else if(last && [...$('kitList').options].some(o=>o.value===last.id+'@'+last.version))await selectKit(last.id,last.version);
} catch(error) {status(error.message,true);}
