const $ = selector => document.querySelector(selector);
const state = {catalog:null,motion:null,rigs:null,currentRig:null,currentSvg:null,currentPose:null,currentMotion:null,time:0,playing:false,raf:0,last:0};
const hasArtwork = pose => pose && (pose.status === 'Supported' || pose.status === 'PendingVisualValidation');
const rigIdFor = (character,view) => `robot-${character}-${view}`;
function applyPose(root, rig, angles = {}) {
  for (const node of rig.nodes) {
    const part = root.querySelector(`[data-part="${node.id}"]`);
    if (!part) throw new Error(`Missing approved rig part: ${node.id}`);
    const angle = Number(angles[node.id] || 0);
    part.setAttribute('transform', `translate(${node.mount.join(' ')}) rotate(${angle})`);
  }
}
function lerp(a,b,t){return a+(b-a)*t}
function sampleKeyframes(keyframes,time,duration,loop){
  if (!keyframes.length) return {};
  const t = loop ? ((time % duration)+duration)%duration : Math.max(0,Math.min(duration,time));
  let from=keyframes[0],to=keyframes[keyframes.length-1];
  for(let i=0;i<keyframes.length-1;i++) if(t>=keyframes[i].time && t<=keyframes[i+1].time){from=keyframes[i];to=keyframes[i+1];break}
  const span=to.time-from.time || 1, p=(t-from.time)/span, result={};
  for(const part of new Set([...Object.keys(from.angles),...Object.keys(to.angles)])) result[part]=lerp(from.angles[part]||0,to.angles[part]||0,p);
  return result;
}
function entriesForCharacter(){return state.catalog.poses.filter(p=>p.character===$('#character').value)}
function populatePosePicker(){
  const prior=$('#pose').value;
  const entries=entriesForCharacter();
  $('#pose').innerHTML=entries.map(p=>`<option value="${p.poseId}">${p.poseId} — ${p.status}</option>`).join('');
  $('#pose').value=entries.some(p=>p.poseId===prior)?prior:(entries.find(p=>p.status==='Supported')||entries[0]).poseId;
}
function populateMotionPicker(){
  const character=$('#character').value, prior=$('#motion').value;
  const entries=state.motion.motions.filter(m=>m.character===character);
  $('#motion').innerHTML='<option value="">Static pose</option>'+entries.map(m=>`<option value="${m.motionId}">${m.motionId} — ${m.status}</option>`).join('');
  $('#motion').value=entries.some(m=>m.motionId===prior)?prior:'';
}
async function loadRig(character,view){
  const id=rigIdFor(character,view); if(state.currentRig?.id===id && state.currentSvg?.isConnected) return;
  const rig=state.rigs.rigs.find(item=>item.id===id); if(!rig) throw new Error(`Missing rig metadata for ${id}`);
  const asset=`source-rig/robot-rig-pack/assets/${id}.svg`;
  const [assetText]=await Promise.all([fetch(asset).then(r=>r.text())]);
  $('#stage').innerHTML=assetText; state.currentSvg=$('#stage svg'); state.currentRig=rig;
}
async function render(){
  const character=$('#character').value, poseId=$('#pose').value;
  const pose=state.catalog.poses.find(p=>p.character===character&&p.poseId===poseId);
  state.currentPose=pose; const motion=state.currentMotion;
  $('#poseStatus').textContent=pose.status; $('#poseStatus').className=`status ${pose.status}`;
  $('#notes').textContent=pose.validationNotes;
  if(!hasArtwork(pose)){
    $('#stage').innerHTML=`<div class="unavailable"><strong>${pose.poseId}</strong><p>${pose.validationNotes}</p><p class="warning">No substitute drawing is shown.</p></div>`;
    return;
  }
  await loadRig(character,pose.view);
  const angles=motion ? sampleKeyframes(motion.keyframes,state.time,motion.durationSeconds,motion.loop) : pose.jointAngles;
  applyPose(state.currentSvg,state.currentRig,angles);
}
function setTime(value){
  state.time=Number(value); $('#seek').value=state.time; $('#time').textContent=`${state.time.toFixed(2)} s`; render();
}
function stop(){state.playing=false;cancelAnimationFrame(state.raf);$('#play').textContent='Play';}
function tick(now){
  if(!state.playing)return; const motion=state.currentMotion;
  const elapsed=(now-state.last)/1000; state.last=now;
  let t=state.time+elapsed;
  if(motion.loop) t=t%motion.durationSeconds; else if(t>=motion.durationSeconds){t=motion.durationSeconds;stop();}
  setTime(t); state.raf=requestAnimationFrame(tick);
}
function selectMotion(){
  stop(); const id=$('#motion').value; state.currentMotion=state.motion.motions.find(m=>m.motionId===id)||null;
  if(state.currentMotion){
    const motion=state.currentMotion; $('#pose').value=motion.fromPoseId;
    $('#motionStatus').textContent=`${motion.status}: ${motion.validationNotes}`;
    $('#seek').max=motion.durationSeconds; $('#seek').disabled=!motion.keyframes.length; $('#play').disabled=!motion.keyframes.length; setTime(0);
  } else {$('#motionStatus').textContent='Static pose mode.'; $('#seek').max=1; $('#seek').disabled=true; $('#play').disabled=true; setTime(0)}
  render();
}
async function start(){
  [state.catalog,state.motion,state.rigs]=await Promise.all(['pose-catalog.json','motion-library.json','source-rig/robot-rig-pack/character-rig.json'].map(path=>fetch(path).then(r=>r.json())));
  $('#character').onchange=()=>{stop();populatePosePicker();populateMotionPicker();selectMotion();};
  $('#pose').onchange=()=>{stop();state.currentMotion=null;$('#motion').value='';selectMotion();render();};
  $('#motion').onchange=selectMotion; $('#seek').oninput=e=>setTime(e.target.value);
  $('#play').onclick=()=>{if(!state.currentMotion)return;state.playing=!state.playing;$('#play').textContent=state.playing?'Pause':'Play';state.last=performance.now();if(state.playing)state.raf=requestAnimationFrame(tick)};
  populatePosePicker();populateMotionPicker();selectMotion();
}
start().catch(error=>{$('#stage').innerHTML=`<div class="unavailable"><strong>Preview could not load.</strong><p>${error.message}</p><p>Serve this folder from a local web server; fetch is intentionally not run from file://.</p></div>`;console.error(error)});


