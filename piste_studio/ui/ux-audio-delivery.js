function masterPresetOption(p){
  return `<option value="${p.id}">${p.label}</option>`
}
async function openMasterCheck(){
  if(!backendConnected)return toast('Backend local requis pour le Master Check',true);
  try{
    const data=await api('/api/audio/delivery/presets');
    const presets=data.presets||[];
    window.__audioDeliveryPresets=presets;
    const d=$('#editorialDrawer');d.hidden=false;
    $('#editorialDrawerTitle').textContent='Master Check';
    $('#editorialDrawerBody').innerHTML=`
      <div class="selector-policy"><span>MASTER RENDU</span><b>Audio Delivery</b><small>Mesure après sommation réelle</small></div>
      <div class="form-grid">
        <div class="row"><label>Preset</label><select id="masterPreset">${presets.map(masterPresetOption).join('')}</select></div>
        <div class="row"><label>Cible LUFS</label><input id="masterTargetLufs" type="number" min="-30" max="-8" step="0.5" value="-16"></div>
        <div class="row"><label>Ceiling TP</label><input id="masterTargetTp" type="number" min="-6" max="0" step="0.1" value="-1"></div>
        <div class="row"><label>Tolérance</label><input id="masterTolerance" type="number" min="0.1" max="3" step="0.1" value="1"></div>
      </div>
      <label class="check-row"><input id="masterLimiter" type="checkbox"> Limiteur master (option explicite)</label>
      <div class="hint">Les presets sont des repères configurables, pas une norme universelle. Aucun limiteur ni normalisation ne sont appliqués automatiquement.</div>
      <div class="suggestion-actions"><button class="btn primary" onclick="runMasterCheck()">Mesurer le master</button><button class="btn" onclick="closeEditorialDrawer()">Annuler</button></div>
      <div id="masterCheckResult"></div>`;
    const select=$('#masterPreset');
    select.onchange=()=>applyMasterPreset(select.value);
  }catch(err){toast('Master Check : '+err.message,true)}
}
function applyMasterPreset(id){
  const p=(window.__audioDeliveryPresets||[]).find(x=>x.id===id);if(!p)return;
  if($('#masterTargetLufs'))$('#masterTargetLufs').value=p.target_lufs;
  if($('#masterTargetTp'))$('#masterTargetTp').value=p.true_peak_ceiling;
  if($('#masterTolerance'))$('#masterTolerance').value=p.loudness_tolerance_lu;
}
async function runMasterCheck(){
  const result=$('#masterCheckResult');
  try{
    if(result)result.innerHTML='<div class="hint">Rendu temporaire et mesure en cours…</div>';
    const payload={
      timeline:backendTimelinePayload(),
      preset_id:$('#masterPreset')?.value||'online_reference',
      target_lufs:+($('#masterTargetLufs')?.value||-16),
      true_peak_ceiling:+($('#masterTargetTp')?.value||-1),
      loudness_tolerance_lu:+($('#masterTolerance')?.value||1),
      limiter:!!$('#masterLimiter')?.checked
    };
    const r=await api('/api/audio/master/check',{method:'POST',body:JSON.stringify(payload)});
    window.__lastMasterCheck=r;
    const m=r.measurement||{},e=r.evaluation||{},render=r.render||{};
    if(result)result.innerHTML=`
      <div class="loudness-grid">
        <div><span>STATUT</span><b>${e.status||'—'}</b></div>
        <div><span>LUFS-I MASTER</span><b>${m.integrated_lufs==null?'—':(+m.integrated_lufs).toFixed(1)+' LUFS'}</b></div>
        <div><span>TRUE PEAK</span><b>${m.true_peak_dbfs==null?'—':(+m.true_peak_dbfs).toFixed(1)+' dBTP'}</b></div>
        <div><span>LRA</span><b>${m.loudness_range_lu==null?'—':(+m.loudness_range_lu).toFixed(1)+' LU'}</b></div>
      </div>
      <div class="loudness-proposal">
        <span>Cible ${(+r.preset.target_lufs).toFixed(1)} LUFS · ceiling ${(+r.preset.true_peak_ceiling).toFixed(1)} dBTP</span>
        <span>Écart loudness ${e.loudness_delta_lu==null?'—':(+e.loudness_delta_lu).toFixed(2)+' LU'}</span>
        <span>${render.clip_count||0} clip(s) sommés · limiteur ${render.limiter_enabled?'ACTIF':'inactif'}</span>
        ${(e.reasons||[]).map(x=>`<em>${x}</em>`).join('')}
      </div>
      <div class="suggestion-actions">${r.report_url?`<a class="btn" href="${r.report_url}" download>Télécharger le rapport JSON</a>`:''}</div>`;
    const mix=$('#mixMeter');if(mix)mix.textContent=`MASTER · ${m.integrated_lufs==null?'—':(+m.integrated_lufs).toFixed(1)+' LUFS'} · ${m.true_peak_dbfs==null?'—':(+m.true_peak_dbfs).toFixed(1)+' dBTP'} · ${e.status||'—'}`;
    toast(`Master Check ${e.status||'terminé'}`,e.status==='WARN')
  }catch(err){
    if(result)result.innerHTML=`<div class="hint">Erreur : ${err.message}</div>`;
    toast('Master Check : '+err.message,true)
  }
}
