function audioCrossfadeAllowed(a,b){
  if(!a||!b)return false;
  if(!a.audioId&&!a.audioDbId)return false;if(!b.audioId&&!b.audioDbId)return false;
  if(String(a.crossfadeWith||'')!==String(b.id||''))return false;
  if(String(b.crossfadeWith||'')!==String(a.id||''))return false;
  const da=+a.crossfadeDuration||0,db=+b.crossfadeDuration||0;
  if(da<=0||db<=0||Math.abs(da-db)>1e-4)return false;
  const overlap=Math.min(a.start+a.duration,b.start+b.duration)-Math.max(a.start,b.start);
  return overlap>0&&overlap<=da+1e-4
}
function fmtMetric(v,suffix){return v==null?'—':(+v).toFixed(1)+' '+suffix}
function selectedAudioAsset(){const c=getClip(selectedClip);return c?.audioId?getAudio(c.audioId):null}
function nextAudioClipSameTrack(c){
  return clips.filter(x=>x.audioId&&x.track===c.track&&x.id!==c.id&&x.start>=c.start).sort((a,b)=>a.start-b.start)[0]||null
}
function appendAudioIntelligenceInspector(){
  const c=getClip(selectedClip),root=$('#inspector');if(!c?.audioId||!root)return;
  const a=getAudio(c.audioId),l=a?.loudness,ready=l?.status==='READY';
  const section=document.createElement('div');section.className='inspector-section audio-intelligence-section';
  section.innerHTML=`<div class="inspector-section-title">LOUDNESS</div>
    <div class="loudness-grid">
      <div><span>LUFS-I</span><b>${ready?fmtMetric(l.integrated_lufs,'LUFS'):'—'}</b></div>
      <div><span>TRUE PEAK</span><b>${ready?fmtMetric(l.true_peak_dbfs,'dBTP'):'—'}</b></div>
      <div><span>LRA</span><b>${ready?fmtMetric(l.loudness_range_lu,'LU'):'—'}</b></div>
      <div><span>SILENCES</span><b>${ready?(l.silence||[]).length:'—'}</b></div>
    </div>
    <div class="form-grid">
      <div class="row"><label>Cible LUFS</label><input id="targetLufsInput" type="number" min="-30" max="-8" step="0.5" value="-16"></div>
      <div class="row"><label>Ceiling TP</label><input id="targetTpInput" type="number" min="-6" max="0" step="0.1" value="-1.5"></div>
    </div>
    <div class="ins-actions">
      <button class="btn" onclick="analyzeSelectedAudioLoudness()">${ready?'Réanalyser':'Analyser loudness'}</button>
      <button class="btn primary" ${ready?'':'disabled'} onclick="openNormalizationProposal()">Normaliser</button>
      <button class="btn" onclick="openClippingReport()">Clipping</button>
    </div>
    ${c.audioRole==='music'?'<div class="ins-actions"><button class="btn primary" onclick="openDuckingProposal()">Ducking VO</button></div>':''}
    ${nextAudioClipSameTrack(c)?'<div class="ins-actions"><button class="btn" onclick="openCrossfadeProposal()">Crossfade suivant</button></div>':''}
    <div class="hint">LUFS/true peak sont mesurés par ffmpeg. Normalisation, ducking et crossfade exigent une validation humaine.</div>`;
  root.appendChild(section)
}
const _v019RenderInspectorIntelligence=renderInspector;
renderInspector=function(){_v019RenderInspectorIntelligence();appendAudioIntelligenceInspector()}

async function analyzeSelectedAudioLoudness(){
  const c=getClip(selectedClip),a=selectedAudioAsset();if(!c||!a?.dbId)return toast('Source audio cataloguée requise',true);
  const keep=c.id;
  try{toast('Analyse LUFS / true peak…');await api(`/api/audio/${a.dbId}/analyze`,{method:'POST',body:JSON.stringify({force:true,silences:true})});await hydrateBackend();if(getClip(keep)){selectedClip=keep;renderTracks();renderInspector()}toast('Analyse loudness terminée')}
  catch(err){toast('Analyse audio : '+err.message,true)}
}
function openAudioDrawer(title,html){const d=$('#editorialDrawer');d.hidden=false;$('#editorialDrawerTitle').textContent=title;$('#editorialDrawerBody').innerHTML=html}
async function openNormalizationProposal(){
  const c=getClip(selectedClip),a=selectedAudioAsset();if(!c||!a?.dbId)return;
  try{
    const target=+($('#targetLufsInput')?.value||-16),tp=+($('#targetTpInput')?.value||-1.5);
    const p=await api('/api/audio/normalize/propose',{method:'POST',body:JSON.stringify({media_id:a.dbId,target_lufs:target,true_peak_ceiling:tp})});
    openAudioDrawer('Normalisation',`<div class="selector-policy"><span>NON DESTRUCTIF</span><b>${a.label}</b><small>Validation humaine requise</small></div>
      <div class="loudness-proposal"><b>${p.gain_adjustment_db>=0?'+':''}${p.gain_adjustment_db.toFixed(2)} dB</b><span>${p.source_lufs.toFixed(1)} → ${p.estimated_lufs_after.toFixed(1)} LUFS</span><span>TP estimé ${p.estimated_true_peak_after==null?'—':p.estimated_true_peak_after.toFixed(1)+' dBTP'}</span>${p.limited_by_true_peak?'<em>Gain limité par le ceiling true peak.</em>':''}</div>
      <div class="suggestion-actions"><button class="btn primary" onclick="applyNormalizationProposal('${c.id}',${p.gain_adjustment_db})">Accepter</button><button class="btn" onclick="closeEditorialDrawer()">Annuler</button></div>`)
  }catch(err){toast('Normalisation : '+err.message,true)}
}
async function applyNormalizationProposal(clipId,delta){
  try{
    const r=await api('/api/audio/normalize/apply',{method:'POST',body:JSON.stringify({timeline:backendTimelinePayload(),clip_id:clipId,gain_adjustment_db:delta})});
    hydrateTimeline(r.timeline);selectedClip=clipId;renderTracks();renderInspector();setPlayhead(getClip(clipId)?.start||playhead);closeEditorialDrawer();toast('Normalisation appliquée')
  }catch(err){toast('Normalisation : '+err.message,true)}
}
async function openClippingReport(){
  try{
    const r=await api('/api/audio/clipping',{method:'POST',body:JSON.stringify({timeline:backendTimelinePayload(),true_peak_ceiling:-1})});
    const rows=(r.clips||[]).map(x=>`<div class="clip-risk ${String(x.status).toLowerCase()}"><b>${getClip(x.clip_id)?.label||x.clip_id}</b><span>${x.status}</span><small>${x.estimated_true_peak_dbfs==null?x.reason:(+x.estimated_true_peak_dbfs).toFixed(1)+' dBTP estimé'}</small></div>`).join('');
    openAudioDrawer('Risque de clipping',`<div class="selector-policy"><span>ESTIMATION PAR CLIP</span><b>${r.risk_count} risque(s)</b><small>Ce contrôle ne remplace pas une mesure du master final.</small></div><div class="clip-risk-list">${rows||'<div class="editorial-empty">Aucun clip audio analysable.</div>'}</div>`)
  }catch(err){toast('Clipping : '+err.message,true)}
}
async function openDuckingProposal(){
  const c=getClip(selectedClip);if(!c?.audioId)return;
  try{
    const p=await api('/api/audio/ducking/propose',{method:'POST',body:JSON.stringify({timeline:backendTimelinePayload(),music_clip_id:c.id,reduction_db:8,attack_seconds:.25,release_seconds:.5})});
    const blockers=(p.blockers||[]).map(x=>`<span>${x.label} · ${x.role.toUpperCase()}</span>`).join('');
    openAudioDrawer('Ducking VO',`<div class="selector-policy"><span>MUSIC → VO/DIALOGUE</span><b>−${p.reduction_db.toFixed(1)} dB</b><small>Aucune Storyline modifiée.</small></div><div class="suggestion-reasons">${blockers||'<span>Aucun chevauchement VO/DIALOGUE.</span>'}</div><div class="duck-preview">${p.suggested_envelope.map(x=>`<span>${x.time.toFixed(2)}s · ${formatDb(x.gainDb)}</span>`).join('')}</div><div class="suggestion-actions"><button class="btn primary" ${p.suggested_envelope.length?'':'disabled'} onclick='applyDuckingProposal(${JSON.stringify(p).replace(/'/g,"&#39;")})'>Accepter</button><button class="btn" onclick="closeEditorialDrawer()">Annuler</button></div>`)
  }catch(err){toast('Ducking : '+err.message,true)}
}
async function applyDuckingProposal(p){
  try{
    const r=await api('/api/audio/ducking/apply',{method:'POST',body:JSON.stringify({timeline:backendTimelinePayload(),music_clip_id:p.music_clip_id,envelope:p.suggested_envelope})});
    hydrateTimeline(r.timeline);selectedClip=p.music_clip_id;renderTracks();renderInspector();closeEditorialDrawer();toast('Ducking appliqué')
  }catch(err){toast('Ducking : '+err.message,true)}
}
async function openCrossfadeProposal(){
  const left=getClip(selectedClip),right=nextAudioClipSameTrack(left);if(!left||!right)return toast('Aucun clip suivant compatible',true);
  try{
    const p=await api('/api/audio/crossfade/propose',{method:'POST',body:JSON.stringify({timeline:backendTimelinePayload(),left_clip_id:left.id,right_clip_id:right.id,duration_seconds:.5})});
    window.__crossfadeProposal=p;
    openAudioDrawer('Crossfade',`<div class="selector-policy"><span>${left.label}</span><b>↔ ${right.label}</b><small>${p.duration_seconds.toFixed(2)} s</small></div><div class="loudness-proposal"><span>Fade out : ${p.left_fade_out.toFixed(2)} s</span><span>Fade in : ${p.right_fade_in.toFixed(2)} s</span><em>${p.policy.timing_change?'Le clip droit avancera légèrement pour créer l’overlap.':'Overlap déjà présent.'}</em></div><div class="suggestion-actions"><button class="btn primary" onclick="applyCrossfadeProposal()">Accepter</button><button class="btn" onclick="closeEditorialDrawer()">Annuler</button></div>`)
  }catch(err){toast('Crossfade : '+err.message,true)}
}
async function applyCrossfadeProposal(){
  const p=window.__crossfadeProposal;if(!p)return;
  try{
    const r=await api('/api/audio/crossfade/apply',{method:'POST',body:JSON.stringify({timeline:backendTimelinePayload(),proposal:p})});
    hydrateTimeline(r.timeline);selectedClip=p.left_clip_id;renderTracks();renderInspector();closeEditorialDrawer();toast('Crossfade appliqué')
  }catch(err){toast('Crossfade : '+err.message,true)}
}
const _v019RenderTracksIntelligence=renderTracks;
renderTracks=function(){_v019RenderTracksIntelligence();$$('.clip[data-clip]').forEach(el=>{const c=getClip(el.dataset.clip);if(!c?.crossfadeWith)return;el.classList.add('crossfade-clip');const tag=document.createElement('span');tag.className='crossfade-badge';tag.textContent='XF '+(+c.crossfadeDuration||0).toFixed(2)+'s';el.appendChild(tag)})}
