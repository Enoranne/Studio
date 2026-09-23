const AUDIO_MIX_ROLES=['dialogue','vo','music','ambience','sfx'];
const AUDIO_DB_MIN=-60,AUDIO_DB_MAX=12;
let mixMaster=null,mixSplitter=null,mixAnalyserL=null,mixAnalyserR=null;
const audioGraphNodes=new Map(),trackBusNodes=new Map();

function clampAudioDb(v){return Math.max(AUDIO_DB_MIN,Math.min(AUDIO_DB_MAX,+v||0))}
function dbToLinear(v){return Math.pow(10,clampAudioDb(v)/20)}
function linearToDb(v){v=+v||0;return v<=0?AUDIO_DB_MIN:clampAudioDb(20*Math.log10(v))}
function formatDb(v){const n=Math.round(clampAudioDb(v)*10)/10;return (n>0?'+':'')+n.toFixed(1)+' dB'}
function normalizeAudioClip(c){
  if(!c||(c.audioId==null&&c.audioDbId==null))return c;
  if(c.gainDb==null)c.gainDb=linearToDb(c.gain==null?1:c.gain);
  c.gainDb=clampAudioDb(c.gainDb);
  c.gain=dbToLinear(c.gainDb);
  c.pan=Math.max(-1,Math.min(1,+c.pan||0));
  c.audioRole=(c.audioRole||(['vo','music','sfx'].includes(c.track)?c.track:'sfx')).toLowerCase();
  if(!AUDIO_MIX_ROLES.includes(c.audioRole))c.audioRole='sfx';
  c.fadeIn=Math.max(0,+c.fadeIn||0);c.fadeOut=Math.max(0,+c.fadeOut||0);
  c.volumeEnvelope=Array.isArray(c.volumeEnvelope)?c.volumeEnvelope.map(p=>({time:+p.time||0,gainDb:clampAudioDb(p.gainDb)})).sort((a,b)=>a.time-b.time):[];
  return c
}
clips.forEach(normalizeAudioClip);

function envelopeDbAt(c,t){
  normalizeAudioClip(c);
  const local=Math.max(0,Math.min(c.duration,t-c.start)),pts=c.volumeEnvelope||[];
  if(!pts.length)return c.gainDb;
  if(local<=pts[0].time)return pts[0].gainDb;
  if(local>=pts[pts.length-1].time)return pts[pts.length-1].gainDb;
  for(let i=1;i<pts.length;i++){
    if(local<=pts[i].time){
      const a=pts[i-1],b=pts[i],span=Math.max(.000001,b.time-a.time),r=(local-a.time)/span;
      return a.gainDb+(b.gainDb-a.gainDb)*r
    }
  }
  return c.gainDb
}
function audioGainAt(c,t){
  let linear=dbToLinear(envelopeDbAt(c,t)),local=t-c.start;
  if((c.fadeIn||0)>0&&local<c.fadeIn)linear*=Math.max(0,local/c.fadeIn);
  const rem=c.start+c.duration-t;
  if((c.fadeOut||0)>0&&rem<c.fadeOut)linear*=Math.max(0,rem/c.fadeOut);
  return Math.max(0,Math.min(4,linear))
}

function isAudioTrack(t){return t&&['audio','vo','music','sfx','dialogue','ambience'].includes(String(t.kind||t.id).toLowerCase())}
function ensureMixGraph(){
  audioContext=audioContext||new (window.AudioContext||window.webkitAudioContext)();
  if(mixMaster)return;
  mixMaster=audioContext.createGain();mixMaster.gain.value=1;
  mixSplitter=audioContext.createChannelSplitter(2);
  mixAnalyserL=audioContext.createAnalyser();mixAnalyserR=audioContext.createAnalyser();
  mixAnalyserL.fftSize=256;mixAnalyserR.fftSize=256;
  mixMaster.connect(audioContext.destination);mixMaster.connect(mixSplitter);
  mixSplitter.connect(mixAnalyserL,0);mixSplitter.connect(mixAnalyserR,1);
}
function ensureTrackBus(trackId){
  ensureMixGraph();
  if(!trackBusNodes.has(trackId)){const g=audioContext.createGain();g.connect(mixMaster);trackBusNodes.set(trackId,g)}
  return trackBusNodes.get(trackId)
}
function updateTrackBusGains(){
  if(!mixMaster)return;
  const anySolo=tracks.some(t=>isAudioTrack(t)&&t.solo);
  tracks.filter(isAudioTrack).forEach(t=>{
    const bus=ensureTrackBus(t.id),audible=!t.muted&&(!anySolo||!!t.solo);
    bus.gain.setTargetAtTime(audible?1:0,audioContext.currentTime,.005)
  })
}
function disconnectAudioGraph(id){
  const g=audioGraphNodes.get(id);if(!g)return;
  for(const n of [g.source,g.gain,g.panner]){try{n?.disconnect()}catch(_){}}
  audioGraphNodes.delete(id)
}
ensureAudioPlayer=function(c){
  normalizeAudioClip(c);
  let p=audioPlayers.get(c.id),a=getAudio(c.audioId);if(!a?.url)return null;
  ensureMixGraph();
  if(!p||p.dataset.url!==a.url){
    if(p)p.pause();disconnectAudioGraph(c.id);
    p=new Audio(a.url);p.preload='auto';p.dataset.url=a.url;p.volume=1;
    audioPlayers.set(c.id,p);
    const source=audioContext.createMediaElementSource(p),gain=audioContext.createGain(),panner=audioContext.createStereoPanner?audioContext.createStereoPanner():null;
    source.connect(gain);
    if(panner){gain.connect(panner);panner.connect(ensureTrackBus(c.track))}
    else gain.connect(ensureTrackBus(c.track));
    audioGraphNodes.set(c.id,{source,gain,panner,track:c.track})
  }
  const graph=audioGraphNodes.get(c.id);
  if(graph&&graph.track!==c.track){
    try{(graph.panner||graph.gain).disconnect()}catch(_){}
    (graph.panner||graph.gain).connect(ensureTrackBus(c.track));graph.track=c.track
  }
  return p
}
function peakDb(analyser){
  if(!analyser)return -60;
  const data=new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(data);
  let peak=0;for(const v of data)peak=Math.max(peak,Math.abs(v));
  return peak<=.00001?-60:Math.max(-60,20*Math.log10(peak))
}
function renderAudioMeters(){
  const root=$('#audioMeters');if(!root)return;
  const l=playing?peakDb(mixAnalyserL):-60,r=playing?peakDb(mixAnalyserR):-60;
  const lp=Math.max(0,Math.min(100,(l+60)/60*100)),rp=Math.max(0,Math.min(100,(r+60)/60*100));
  root.style.setProperty('--meter-l',lp+'%');root.style.setProperty('--meter-r',rp+'%');
  root.dataset.peakL=formatDb(l);root.dataset.peakR=formatDb(r)
}

syncAudio=function(fromPlayback=false){
  ensureMixGraph();updateTrackBusGains();let active=0;
  clips.filter(c=>c.audioId).forEach(c=>{
    normalizeAudioClip(c);const tr=getTrack(c.track),a=getAudio(c.audioId),p=ensureAudioPlayer(c);
    const anySolo=tracks.some(t=>isAudioTrack(t)&&t.solo),audible=!tr?.muted&&(!anySolo||!!tr?.solo);
    const on=audible&&playhead>=c.start&&playhead<c.start+c.duration;
    if(!p||!a||!on){if(p&&!p.paused)p.pause();return}
    active++;const target=Math.max(0,Math.min(a.duration-.01,(c.sourceStart||0)+(playhead-c.start)));
    const graph=audioGraphNodes.get(c.id);
    if(graph){graph.gain.gain.setValueAtTime(audioGainAt(c,playhead),audioContext.currentTime);if(graph.panner)graph.panner.pan.setValueAtTime(c.pan||0,audioContext.currentTime)}
    if(!fromPlayback||Math.abs((p.currentTime||0)-target)>.28){try{p.currentTime=target}catch(_){}}
    if(playing&&p.paused){audioContext.resume().catch(()=>{});p.play().catch(()=>{})}
    if(!playing&&!p.paused)p.pause()
  });
  $('#mixMeter').textContent=`MIX · ${active} source${active>1?'s':''} active${active>1?'s':''}`;renderAudioMeters()
}
const _v018TogglePlayAudio=togglePlay;
togglePlay=function(){ensureMixGraph();audioContext.resume().catch(()=>{});_v018TogglePlayAudio()}
const _v018PauseAudio=pausePlayback;
pausePlayback=function(){_v018PauseAudio();renderAudioMeters()}
const _v018ToggleMuteAudio=toggleMute;
toggleMute=function(id){_v018ToggleMuteAudio(id);updateTrackBusGains();syncAudio()}

function toggleSolo(id){
  const t=getTrack(id);if(!t||!isAudioTrack(t))return;t.solo=!t.solo;renderTracks();updateTrackBusGains();syncAudio();toast(`${t.name} ${t.solo?'solo':'solo désactivé'}`)
}

async function checkpointAudioEdit(before,reason){
  if(backendConnected){
    try{await api('/api/history/checkpoint',{method:'POST',body:JSON.stringify({edit_name:activeEditName,reason,timeline:backendTimelinePayload(before,storylineMode)})});return true}
    catch(err){toast('Checkpoint audio impossible : '+err.message,true);return false}
  }
  if(typeof localUndoStack!=='undefined'){localUndoStack.push({clips:cloneClips(before),storylineMode,storylineStart:getStorylineStart(),reason});if(localUndoStack.length>50)localUndoStack.shift()}
  return true
}

function dbToY(db){return (AUDIO_DB_MAX-clampAudioDb(db))/(AUDIO_DB_MAX-AUDIO_DB_MIN)*100}
function automationPath(c){
  normalizeAudioClip(c);const pts=c.volumeEnvelope||[];
  const data=[{time:0,gainDb:envelopeDbAt(c,c.start)},...pts,{time:c.duration,gainDb:envelopeDbAt(c,c.start+c.duration)}];
  return data.map((p,i)=>`${i?'L':'M'} ${(p.time/c.duration*100).toFixed(2)} ${dbToY(p.gainDb).toFixed(2)}`).join(' ')
}
function decorateAudioMixClips(){
  $$('.clip[data-clip]').forEach(el=>{
    const c=getClip(el.dataset.clip);if(!c?.audioId)return;normalizeAudioClip(c);el.classList.add('audio-mix-enhanced');
    const small=el.querySelector('small');if(small)small.textContent=`${fmt(c.start)} · ${c.duration.toFixed(1)}s · ${formatDb(c.gainDb)}`;
    const overlay=document.createElement('div');overlay.className='audio-mix-overlay';
    overlay.innerHTML=`<svg class="automation-line" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="${automationPath(c)}"></path></svg>
      <button class="fade-grip fade-in-grip" title="Fade in ${c.fadeIn.toFixed(2)} s" style="left:${c.fadeIn/c.duration*100}%"></button>
      <button class="fade-grip fade-out-grip" title="Fade out ${c.fadeOut.toFixed(2)} s" style="right:${c.fadeOut/c.duration*100}%"></button>
      ${(c.volumeEnvelope||[]).map((p,i)=>`<button class="automation-point" data-point="${i}" title="${formatDb(p.gainDb)} @ ${p.time.toFixed(2)}s" style="left:${p.time/c.duration*100}%;top:${dbToY(p.gainDb)}%"></button>`).join('')}`;
    el.appendChild(overlay);
    overlay.querySelector('.fade-in-grip').onpointerdown=e=>beginFadeDrag(e,c.id,'in',el);
    overlay.querySelector('.fade-out-grip').onpointerdown=e=>beginFadeDrag(e,c.id,'out',el);
    overlay.querySelectorAll('.automation-point').forEach(p=>p.onpointerdown=e=>beginAutomationDrag(e,c.id,+p.dataset.point,el,p))
  })
}
function beginFadeDrag(ev,id,edge,el){
  ev.preventDefault();ev.stopPropagation();const c=getClip(id),before=cloneClips(),rect=el.getBoundingClientRect();if(!c)return;
  const move=e=>{let ratio=Math.max(0,Math.min(1,(e.clientX-rect.left)/rect.width));if(edge==='in')c.fadeIn=Math.min(c.duration-(c.fadeOut||0),ratio*c.duration);else c.fadeOut=Math.min(c.duration-(c.fadeIn||0),(1-ratio)*c.duration);decorateAfterAudioChange(c)};
  const up=async()=>{document.removeEventListener('pointermove',move);await checkpointAudioEdit(before,`Fade ${edge} · ${c.label}`);renderTracks();renderInspector();syncAudio()};
  document.addEventListener('pointermove',move);document.addEventListener('pointerup',up,{once:true})
}
function beginAutomationDrag(ev,id,index,el,pointEl){
  ev.preventDefault();ev.stopPropagation();const c=getClip(id),before=cloneClips(),rect=el.getBoundingClientRect(),point=c?.volumeEnvelope?.[index];if(!c||!point)return;
  const move=e=>{point.time=Math.max(0,Math.min(c.duration,(e.clientX-rect.left)/rect.width*c.duration));point.gainDb=clampAudioDb(AUDIO_DB_MAX-(e.clientY-rect.top)/rect.height*(AUDIO_DB_MAX-AUDIO_DB_MIN));pointEl.style.left=(point.time/c.duration*100)+'%';pointEl.style.top=dbToY(point.gainDb)+'%';pointEl.title=`${formatDb(point.gainDb)} @ ${point.time.toFixed(2)}s`};
  const up=async()=>{document.removeEventListener('pointermove',move);c.volumeEnvelope.sort((a,b)=>a.time-b.time);await checkpointAudioEdit(before,`Automation · ${c.label}`);renderTracks();renderInspector();syncAudio()};
  document.addEventListener('pointermove',move);document.addEventListener('pointerup',up,{once:true})
}
function decorateAfterAudioChange(c){
  const el=document.querySelector(`.clip[data-clip="${c.id}"]`);if(!el)return;
  const fi=el.querySelector('.fade-in-grip'),fo=el.querySelector('.fade-out-grip');if(fi)fi.style.left=c.fadeIn/c.duration*100+'%';if(fo)fo.style.right=c.fadeOut/c.duration*100+'%'
}

function audioEnvelopeList(c){
  if(!c.volumeEnvelope?.length)return '<div class="hint">Aucun point d’automation. Le gain du clip reste constant hors fades.</div>';
  return '<div class="automation-list">'+c.volumeEnvelope.map((p,i)=>`<div class="automation-row"><span>${p.time.toFixed(2)} s</span><b>${formatDb(p.gainDb)}</b><button onclick="removeAudioAutomationPoint(${i})">×</button></div>`).join('')+'</div>'
}
function appendAudioMixInspector(){
  const c=getClip(selectedClip),root=$('#inspector');if(!c?.audioId||!root)return;normalizeAudioClip(c);
  ['cg','cfi','cfo'].forEach(id=>$('#'+id)?.closest('.row')?.remove());
  const section=document.createElement('div');section.className='inspector-section audio-mix-section';
  section.innerHTML=`<div class="inspector-section-title">AUDIO MIX</div>
    <div class="form-grid">
      <div class="row"><label>Rôle</label><select id="audioRoleInput">${AUDIO_MIX_ROLES.map(r=>`<option value="${r}" ${c.audioRole===r?'selected':''}>${r.toUpperCase()}</option>`).join('')}</select></div>
      <div class="row"><label>Gain dB</label><input id="gainDbInput" type="number" min="-60" max="12" step="0.5" value="${c.gainDb.toFixed(1)}"></div>
      <div class="row"><label>Pan</label><input id="panInput" type="number" min="-1" max="1" step="0.05" value="${c.pan.toFixed(2)}"></div>
      <div class="row"><label>Fade in</label><input id="fadeInInput" type="number" min="0" max="${c.duration}" step="0.05" value="${c.fadeIn.toFixed(2)}"></div>
      <div class="row"><label>Fade out</label><input id="fadeOutInput" type="number" min="0" max="${c.duration}" step="0.05" value="${c.fadeOut.toFixed(2)}"></div>
    </div>
    <div class="audio-role-note">${c.audioRole.toUpperCase()} · ${c.pan<-.05?'gauche':c.pan>.05?'droite':'centre'} · ${formatDb(c.gainDb)}</div>
    <div class="inspector-section-title">VOLUME AUTOMATION</div>
    ${audioEnvelopeList(c)}
    <div class="ins-actions"><button class="btn" onclick="addAudioAutomationPoint()">+ Point au playhead</button><button class="btn" onclick="clearAudioAutomation()">Effacer automation</button></div>
    <div class="hint">Les points de volume et les poignées de fade sont manipulables directement sur le clip. Preview Web Audio : gain, pan, fades et automation sont audibles.</div>`;
  root.appendChild(section)
}
const _v018RenderInspectorAudio=renderInspector;
renderInspector=function(){_v018RenderInspectorAudio();appendAudioMixInspector()}

const _v018ApplyEditAudio=applyEdit;
applyEdit=async function(){
  const c=getClip(selectedClip);if(!c?.audioId)return _v018ApplyEditAudio();
  const before=cloneClips(),next={...c,track:$('#ct').value,start:+$('#cs').value,duration:+$('#cd').value,sourceStart:+$('#ci').value};
  normalizeAudioClip(next);next.gainDb=clampAudioDb($('#gainDbInput').value);next.gain=dbToLinear(next.gainDb);next.pan=Math.max(-1,Math.min(1,+$('#panInput').value||0));next.audioRole=$('#audioRoleInput').value;next.fadeIn=Math.max(0,+$('#fadeInInput').value||0);next.fadeOut=Math.max(0,+$('#fadeOutInput').value||0);next.volumeEnvelope=(c.volumeEnvelope||[]).filter(p=>p.time<=next.duration).map(p=>({...p}));
  const err=validate(next,c.id);if(err){toast(err,true);return}
  if(next.fadeIn+next.fadeOut>next.duration){toast('Fades supérieurs à la durée du clip',true);return}
  await checkpointAudioEdit(before,`Mix audio · ${c.label}`);Object.assign(c,next);renderTracks();renderInspector();setPlayhead(c.start);toast('PATCH audio local appliqué')
}

async function addAudioAutomationPoint(){
  const c=getClip(selectedClip);if(!c?.audioId)return;normalizeAudioClip(c);const before=cloneClips(),time=Math.max(0,Math.min(c.duration,playhead-c.start)),gainDb=envelopeDbAt(c,c.start+time);
  const existing=c.volumeEnvelope.find(p=>Math.abs(p.time-time)<.025);if(existing)existing.gainDb=gainDb;else c.volumeEnvelope.push({time:+time.toFixed(3),gainDb:+gainDb.toFixed(2)});
  c.volumeEnvelope.sort((a,b)=>a.time-b.time);await checkpointAudioEdit(before,`Point volume · ${c.label}`);renderTracks();renderInspector();syncAudio()
}
async function removeAudioAutomationPoint(index){
  const c=getClip(selectedClip);if(!c?.audioId||!c.volumeEnvelope?.[index])return;const before=cloneClips();c.volumeEnvelope.splice(index,1);await checkpointAudioEdit(before,`Supprime point volume · ${c.label}`);renderTracks();renderInspector();syncAudio()
}
async function clearAudioAutomation(){
  const c=getClip(selectedClip);if(!c?.audioId||!c.volumeEnvelope?.length)return;const before=cloneClips();c.volumeEnvelope=[];await checkpointAudioEdit(before,`Efface automation · ${c.label}`);renderTracks();renderInspector();syncAudio()
}

const _v018RenderTracksAudio=renderTracks;
renderTracks=function(){
  clips.forEach(normalizeAudioClip);_v018RenderTracksAudio();
  tracks.filter(isAudioTrack).forEach(t=>{const head=document.querySelector(`#lane-${t.id}`)?.previousElementSibling;if(!head)return;const controls=head.querySelector('.track-controls');if(controls&&!controls.querySelector('.solo-btn')){const b=document.createElement('button');b.className='solo-btn '+(t.solo?'on':'');b.textContent='S';b.title='Solo';b.onclick=()=>toggleSolo(t.id);controls.insertBefore(b,controls.children[1]||null)}});decorateAudioMixClips();updateTrackBusGains()
}

const _v018RemoveClipAudio=removeClip;
removeClip=function(){const id=selectedClip;disconnectAudioGraph(id);_v018RemoveClipAudio()}

const _v018DuplicateAudio=duplicateClip;
duplicateClip=function(){const c=getClip(selectedClip);if(!c?.audioId)return _v018DuplicateAudio();const before=cloneClips();const n={...c,volumeEnvelope:(c.volumeEnvelope||[]).map(p=>({...p})),id:'x'+Date.now(),start:snapTime(c.start+c.duration)};const err=validate(n);if(err)return toast(err,true);clips.push(n);selectedClip=n.id;checkpointAudioEdit(before,`Duplique audio · ${c.label}`);renderTracks();toast('Clip audio dupliqué')}

const _v018ValidateAudio=validate;
validate=function(c,ignore){if(c?.audioId){normalizeAudioClip(c);if(c.gainDb<AUDIO_DB_MIN||c.gainDb>AUDIO_DB_MAX)return 'Gain hors plage -60..+12 dB';if(c.pan<-1||c.pan>1)return 'Pan hors plage -1..1';if(!AUDIO_MIX_ROLES.includes(c.audioRole))return 'Rôle audio invalide';if((c.volumeEnvelope||[]).some(p=>p.time<0||p.time>c.duration||p.gainDb<AUDIO_DB_MIN||p.gainDb>AUDIO_DB_MAX))return 'Automation audio invalide'}return _v018ValidateAudio(c,ignore)}

const _v018BindAudioFile=bindAudioFile;
bindAudioFile=async function(a,file){await _v018BindAudioFile(a,file);clips.filter(c=>c.audioId===a.id).forEach(normalizeAudioClip);renderAudioMeters()}
