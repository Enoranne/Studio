let deliveryTargetsCache=[];
let deliveryDefaultPresetId='online_1080';

function deliveryEsc(value){
  return String(value??'').replace(/[&<>"']/g,ch=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[ch])
}
function deliveryTargetById(id){
  return deliveryTargetsCache.find(x=>x.id===id)||null
}
function deliveryTechnicalSummary(target){
  if(!target)return '';
  const video=target.video_codec==='prores_ks'
    ? 'ProRes 422 HQ'
    : `H.264 ${target.video_bitrate_mbps||'—'} Mb/s`;
  const audio=target.audio_codec==='pcm_s24le'
    ? 'PCM 24-bit'
    : `AAC ${target.audio_bitrate_kbps||'—'} kb/s`;
  return `${target.width}×${target.height} · ${target.aspect_ratio} · ${target.fps} fps · ${video} · ${audio} · ${target.audio_sample_rate/1000} kHz`
}
function deliveryStatusClass(status){
  status=String(status||'MISSING').toUpperCase();
  if(status==='PASS')return 'delivery-pass';
  if(status==='BLOCKED')return 'delivery-blocked';
  return 'delivery-warn'
}
function deliveryStatusCard(label,item){
  const state=String(item?.status||'MISSING').toUpperCase();
  return `<div class="delivery-check ${deliveryStatusClass(state)}"><div><span>${deliveryEsc(label)}</span><b>${deliveryEsc(state)}</b></div><p>${deliveryEsc(item?.message||'État indisponible.')}</p></div>`
}
function deliveryPresetBadge(target){
  const type=target.custom?'PERSONNALISÉ':'INTÉGRÉ';
  const def=target.id===deliveryDefaultPresetId?' · DÉFAUT':'';
  return `${type}${def}`
}
function deliveryPresetEditor(target){
  if(!target.custom)return '';
  const isH264=target.video_codec==='libx264';
  return `
    <div class="delivery-preset-editor">
      <div class="inspector-section-title">PRESET PERSONNALISÉ</div>
      <div class="form-grid">
        <div class="row"><label>Nom</label><input id="deliveryPresetLabel" maxlength="100" value="${deliveryEsc(target.label)}"></div>
        <div class="row"><label>Famille</label><select id="deliveryPresetFamily">
          ${['festival','online','social','custom'].map(x=>`<option value="${x}" ${target.family===x?'selected':''}>${x}</option>`).join('')}
        </select></div>
        <div class="row"><label>Largeur</label><input id="deliveryPresetWidth" type="number" min="320" max="7680" step="2" value="${target.width}"></div>
        <div class="row"><label>Hauteur</label><input id="deliveryPresetHeight" type="number" min="240" max="7680" step="2" value="${target.height}"></div>
        <div class="row"><label>FPS</label><select id="deliveryPresetFps">
          ${[24,30,60].map(x=>`<option value="${x}" ${+target.fps===x?'selected':''}>${x}</option>`).join('')}
        </select></div>
        <div class="row"><label>Codec</label><select id="deliveryPresetCodec">
          <option value="libx264" ${isH264?'selected':''}>H.264</option>
          <option value="prores_ks" ${!isH264?'selected':''}>ProRes 422 HQ</option>
        </select></div>
        <div class="row delivery-h264-only ${isH264?'':'delivery-crop-hidden'}"><label>Vidéo Mb/s</label><input id="deliveryPresetVideoBitrate" type="number" min="1" max="200" step="0.5" value="${target.video_bitrate_mbps||8}"></div>
        <div class="row delivery-h264-only ${isH264?'':'delivery-crop-hidden'}"><label>Audio kb/s</label><input id="deliveryPresetAudioBitrate" type="number" min="96" max="512" step="32" value="${target.audio_bitrate_kbps||256}"></div>
        <div class="row"><label>Source Tesseract</label><select id="deliveryPresetTessResolution">
          ${['720p','1080p','4k'].map(x=>`<option value="${x}" ${target.tesseract_resolution===x?'selected':''}>${x}</option>`).join('')}
        </select></div>
        <div class="row"><label>Cadrage défaut</label><select id="deliveryPresetDefaultFraming">
          ${['native','fit','fill'].map(x=>`<option value="${x}" ${target.default_framing===x?'selected':''}>${x.toUpperCase()}</option>`).join('')}
        </select></div>
      </div>
      <div class="hint">Codec, conteneur, pixel format et audio sont normalisés ensemble : H.264 → MP4/yuv420p/AAC ; ProRes → MOV/yuv422p10le/PCM 24-bit.</div>
      <div class="suggestion-actions">
        <button class="btn primary" onclick="saveDeliveryPreset()">Enregistrer le preset</button>
        <button class="btn" onclick="deleteDeliveryPreset()">Supprimer</button>
      </div>
    </div>
  `
}
function deliveryPresetActions(target){
  return `
    <div class="delivery-preset-actions">
      <button class="btn" onclick="duplicateDeliveryPreset()">Dupliquer</button>
      ${target.id===deliveryDefaultPresetId?'':`<button class="btn" onclick="setDeliveryPresetDefault()">Définir par défaut</button>`}
      <button class="btn" onclick="downloadDeliveryPreset()">Exporter JSON</button>
      <button class="btn" onclick="document.getElementById('deliveryPresetImportFile').click()">Importer JSON</button>
      <input id="deliveryPresetImportFile" type="file" accept="application/json,.json" hidden>
    </div>
  `
}
function renderDeliveryCenter(targetId=null,framingMode=null){
  const d=$('#editorialDrawer');if(!d)return;
  const target=deliveryTargetById(targetId)
    ||deliveryTargetById(deliveryDefaultPresetId)
    ||deliveryTargetsCache[0];
  if(!target)return;
  const framing=framingMode&&target.framing_modes.includes(framingMode)
    ?framingMode:target.default_framing;
  const reframable=(target.framing_modes||[]).some(x=>x!=='native');
  d.hidden=false;
  $('#editorialDrawerTitle').textContent='Delivery Center';
  $('#editorialDrawerBody').innerHTML=`
    <div class="selector-policy"><span>V0.23.5 · DELIVERY</span><b>Presets & export</b><small>Préflight avant transcodage</small></div>
    <div class="row"><label>Preset</label><select id="deliveryTarget">
      ${deliveryTargetsCache.map(x=>`<option value="${deliveryEsc(x.id)}" ${x.id===target.id?'selected':''}>${deliveryEsc(x.label)}${x.id===deliveryDefaultPresetId?' · défaut':''}</option>`).join('')}
    </select></div>
    <div class="delivery-target-summary">
      <div class="delivery-preset-head"><b>${deliveryEsc(target.label)}</b><em>${deliveryPresetBadge(target)}</em></div>
      <span>${deliveryEsc(deliveryTechnicalSummary(target))}</span>
      ${(target.notes||[]).map(x=>`<small>${deliveryEsc(x)}</small>`).join('')}
    </div>
    ${deliveryPresetActions(target)}
    ${deliveryPresetEditor(target)}
    ${reframable?`
      <div class="row"><label>Cadrage export</label><select id="deliveryFraming">
        ${target.framing_modes.map(x=>`<option value="${x}" ${x===framing?'selected':''}>${x==='fit'?'FIT · conserver toute l’image':x==='fill'?'FILL · plein cadre avec crop':'NATIVE'}</option>`).join('')}
      </select></div>
      <label class="check-row ${framing==='fill'?'':'delivery-crop-hidden'}" id="deliveryCropRow">
        <input id="deliveryAllowCrop" type="checkbox"> Autoriser explicitement le crop centré
      </label>
      <div class="hint">PISTE ne choisit pas de recadrage éditorial à ta place. FIT préserve tout le cadre ; FILL peut retirer une partie importante des bords.</div>
    `:''}
    <div id="deliveryPreflight"><div class="hint">Préflight en cours…</div></div>
    <div class="suggestion-actions">
      <button class="btn primary" id="deliveryExportBtn" onclick="runDeliveryExport()" disabled>Exporter le livrable</button>
      <button class="btn" onclick="closeEditorialDrawer()">Fermer</button>
    </div>
    <div id="deliveryResult"></div>
  `;
  $('#deliveryTarget').onchange=e=>renderDeliveryCenter(e.target.value,null);
  const framingSelect=$('#deliveryFraming');
  if(framingSelect)framingSelect.onchange=e=>{
    const row=$('#deliveryCropRow');
    if(row)row.classList.toggle('delivery-crop-hidden',e.target.value!=='fill');
    const box=$('#deliveryAllowCrop');if(box&&e.target.value!=='fill')box.checked=false;
    refreshDeliveryPreflight()
  };
  const crop=$('#deliveryAllowCrop');
  if(crop)crop.onchange=refreshDeliveryPreflight;
  const codec=$('#deliveryPresetCodec');
  if(codec)codec.onchange=()=>{
    const h264=codec.value==='libx264';
    $$('.delivery-h264-only').forEach(el=>el.classList.toggle('delivery-crop-hidden',!h264))
  };
  const importFile=$('#deliveryPresetImportFile');
  if(importFile)importFile.onchange=importDeliveryPresetFile;
  refreshDeliveryPreflight()
}
async function refreshDeliveryTargets(selectId=null){
  const data=await api('/api/delivery/targets');
  deliveryTargetsCache=data.targets||[];
  deliveryDefaultPresetId=data.default_preset_id||'online_1080';
  const id=selectId&&deliveryTargetById(selectId)?selectId:deliveryDefaultPresetId;
  renderDeliveryCenter(id)
}
async function openDeliveryCenter(){
  if(!backendConnected)return toast('Backend local requis pour le Delivery Center',true);
  if(!activeVersion)return toast('Publie d’abord une version avant le delivery',true);
  try{await refreshDeliveryTargets()}
  catch(err){toast('Delivery : '+err.message,true)}
}
function currentDeliveryPayload(){
  const target=deliveryTargetById($('#deliveryTarget')?.value)||deliveryTargetsCache[0];
  return {
    edit_name:activeEditName,
    target_id:target?.id,
    framing_mode:$('#deliveryFraming')?.value||target?.default_framing||'native',
    allow_crop:!!$('#deliveryAllowCrop')?.checked,
  }
}
function deliveryPresetFormPayload(){
  const target=deliveryTargetById($('#deliveryTarget')?.value);
  if(!target?.custom)throw new Error('Duplique d’abord un preset intégré.');
  return {
    label:$('#deliveryPresetLabel')?.value||target.label,
    family:$('#deliveryPresetFamily')?.value||target.family,
    width:+($('#deliveryPresetWidth')?.value||target.width),
    height:+($('#deliveryPresetHeight')?.value||target.height),
    fps:+($('#deliveryPresetFps')?.value||target.fps),
    video_codec:$('#deliveryPresetCodec')?.value||target.video_codec,
    video_bitrate_mbps:+($('#deliveryPresetVideoBitrate')?.value||target.video_bitrate_mbps||8),
    audio_bitrate_kbps:+($('#deliveryPresetAudioBitrate')?.value||target.audio_bitrate_kbps||256),
    tesseract_resolution:$('#deliveryPresetTessResolution')?.value||target.tesseract_resolution||'1080p',
    default_framing:$('#deliveryPresetDefaultFraming')?.value||target.default_framing||'native',
    notes:target.notes||[],
  }
}
async function saveDeliveryPreset(){
  const target=deliveryTargetById($('#deliveryTarget')?.value);
  if(!target?.custom)return toast('Preset intégré immuable : duplique-le d’abord',true);
  try{
    const r=await api(`/api/delivery/presets/${encodeURIComponent(target.id)}`,{
      method:'PATCH',body:JSON.stringify(deliveryPresetFormPayload())
    });
    deliveryTargetsCache=r.targets||deliveryTargetsCache;
    deliveryDefaultPresetId=r.default_preset_id||deliveryDefaultPresetId;
    renderDeliveryCenter(r.preset.id);
    toast('Preset delivery enregistré')
  }catch(err){toast('Preset : '+err.message,true)}
}
async function duplicateDeliveryPreset(){
  const target=deliveryTargetById($('#deliveryTarget')?.value);if(!target)return;
  try{
    const r=await api(`/api/delivery/presets/${encodeURIComponent(target.id)}/duplicate`,{
      method:'POST',body:JSON.stringify({label:`${target.label} · copie`})
    });
    deliveryTargetsCache=r.targets||deliveryTargetsCache;
    deliveryDefaultPresetId=r.default_preset_id||deliveryDefaultPresetId;
    renderDeliveryCenter(r.preset.id);
    toast('Preset dupliqué · personnalisation disponible')
  }catch(err){toast('Duplication preset : '+err.message,true)}
}
async function deleteDeliveryPreset(){
  const target=deliveryTargetById($('#deliveryTarget')?.value);
  if(!target?.custom)return toast('Un preset intégré ne peut pas être supprimé',true);
  try{
    const r=await api(`/api/delivery/presets/${encodeURIComponent(target.id)}`,{method:'DELETE'});
    deliveryTargetsCache=r.targets||[];
    deliveryDefaultPresetId=r.default_preset_id||'online_1080';
    renderDeliveryCenter(deliveryDefaultPresetId);
    toast('Preset personnalisé supprimé')
  }catch(err){toast('Suppression preset : '+err.message,true)}
}
async function setDeliveryPresetDefault(){
  const target=deliveryTargetById($('#deliveryTarget')?.value);if(!target)return;
  try{
    const r=await api(`/api/delivery/presets/${encodeURIComponent(target.id)}/default`,{method:'POST',body:'{}'});
    deliveryDefaultPresetId=r.default_preset_id||target.id;
    renderDeliveryCenter(target.id);
    toast('Preset défini par défaut')
  }catch(err){toast('Preset par défaut : '+err.message,true)}
}
async function downloadDeliveryPreset(){
  const target=deliveryTargetById($('#deliveryTarget')?.value);if(!target)return;
  try{
    const response=await fetch(`/api/delivery/presets/${encodeURIComponent(target.id)}/export`);
    if(!response.ok)throw new Error(await response.text());
    const doc=await response.json();
    const blob=new Blob([JSON.stringify(doc,null,2)+'\n'],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=`${target.id}.piste-delivery.json`;a.click();
    setTimeout(()=>URL.revokeObjectURL(url),0);
    toast('Preset JSON préparé')
  }catch(err){toast('Export preset : '+err.message,true)}
}
async function importDeliveryPresetFile(ev){
  const file=ev.target.files?.[0];if(!file)return;
  try{
    const doc=JSON.parse(await file.text());
    const r=await api('/api/delivery/presets/import',{method:'POST',body:JSON.stringify(doc)});
    deliveryTargetsCache=r.targets||deliveryTargetsCache;
    deliveryDefaultPresetId=r.default_preset_id||deliveryDefaultPresetId;
    renderDeliveryCenter(r.preset.id);
    toast('Preset JSON importé')
  }catch(err){toast('Import preset : '+err.message,true)}
}
async function refreshDeliveryPreflight(){
  if(!activeVersion)return;
  const root=$('#deliveryPreflight'),button=$('#deliveryExportBtn');
  if(root)root.innerHTML='<div class="hint">Préflight en cours…</div>';
  if(button)button.disabled=true;
  try{
    const result=await api(`/api/delivery/${encodeURIComponent(activeVersion)}/preflight`,{
      method:'POST',
      body:JSON.stringify(currentDeliveryPayload()),
    });
    window.__deliveryPreflight=result;
    const checks=result.checks||{},frame=checks.framing||{},crop=frame.crop_estimate||{};
    const cropLine=frame.mode==='fill'&&crop.known&&crop.percent!=null
      ?`<div class="delivery-crop-estimate"><b>Crop estimé</b><span>≈ ${(+crop.percent).toFixed(1)}% de la ${crop.axis==='width'?'largeur':'hauteur'} du cadre source hors image</span></div>`
      :'';
    if(root)root.innerHTML=`
      <div class="delivery-preflight-head"><span>PRÉFLIGHT</span><b>${result.can_export?(result.requires_confirmation?'WARN':'PASS'):'BLOCKED'}</b></div>
      ${deliveryStatusCard('Version publiée',checks.published_version)}
      ${deliveryStatusCard('Audio master',checks.audio)}
      ${deliveryStatusCard('Titres / overlays',checks.titles)}
      ${deliveryStatusCard('Cadrage',checks.framing)}
      ${cropLine}
      ${result.requires_confirmation?'<div class="hint">Le bouton d’export reste disponible pour les avertissements : cliquer dessus vaut confirmation explicite. Un blocage de cadrage doit d’abord être résolu.</div>':''}
    `;
    if(button){
      button.disabled=!result.can_export;
      button.textContent=result.requires_confirmation?'Exporter avec avertissements':'Exporter le livrable'
    }
  }catch(err){
    if(root)root.innerHTML=`<div class="warn">Préflight impossible : ${deliveryEsc(err.message)}</div>`;
    if(button)button.disabled=true
  }
}
async function runDeliveryExport(){
  if(!activeVersion)return;
  const button=$('#deliveryExportBtn'),result=$('#deliveryResult');
  if(button)button.disabled=true;
  if(result)result.innerHTML='<div class="hint">Rendu Tesseract puis transcodage delivery en cours…</div>';
  try{
    const r=await api(`/api/delivery/${encodeURIComponent(activeVersion)}/export`,{
      method:'POST',
      body:JSON.stringify(currentDeliveryPayload()),
    });
    const p=r.probe||{},target=r.target||{},conformance=r.conformance||{};
    const conformState=String(conformance.status||'—').toUpperCase();
    if(result)result.innerHTML=`
      <div class="delivery-success">
        <div><span>LIVRABLE</span><b>${deliveryEsc(target.label||target.id)}</b></div>
        <p>${p.width||'—'}×${p.height||'—'} · ${p.fps||'—'} fps · vidéo ${deliveryEsc(p.video_codec||'—')} · audio ${deliveryEsc(p.audio_codec||'—')} · ${p.audio_sample_rate||'—'} Hz</p>
        <div class="delivery-conformance ${conformState==='PASS'?'delivery-pass':'delivery-warn'}"><span>CONFORMITÉ</span><b>${deliveryEsc(conformState)}</b></div>
        ${(conformance.reasons||[]).map(x=>`<em class="delivery-conformance-reason">${deliveryEsc(x)}</em>`).join('')}
        <small>${deliveryEsc(r.path)}</small>
        <div class="suggestion-actions">
          ${r.file_url?`<a class="btn primary" href="${deliveryEsc(r.file_url)}" download>Télécharger le livrable</a>`:''}
          ${r.report_url?`<a class="btn" href="${deliveryEsc(r.report_url)}" download>Rapport JSON</a>`:''}
        </div>
      </div>`;
    toast('Livrable créé · '+(target.label||target.id))
  }catch(err){
    if(result)result.innerHTML=`<div class="warn">Export impossible : ${deliveryEsc(err.message)}</div>`;
    toast('Delivery : '+err.message,true)
  }finally{
    if(button)button.disabled=false
  }
}

if(typeof commands!=='undefined'&&!commands.some(c=>c.label==='Delivery · Festival / social')){
  commands.push({
    label:'Delivery · Festival / social',
    hint:'Export',
    keywords:'delivery export festival social vertical square prores youtube preset',
    run:()=>openDeliveryCenter(),
  })
}
