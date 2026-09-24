let deliveryTargetsCache=[];

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
  return `<div class="delivery-check ${deliveryStatusClass(state)}"><div><span>${label}</span><b>${state}</b></div><p>${item?.message||'État indisponible.'}</p></div>`
}
function renderDeliveryCenter(targetId=null,framingMode=null){
  const d=$('#editorialDrawer');if(!d)return;
  const target=deliveryTargetById(targetId)||deliveryTargetsCache[0];
  if(!target)return;
  const framing=framingMode&&target.framing_modes.includes(framingMode)
    ?framingMode:target.default_framing;
  const social=target.family==='social';
  d.hidden=false;
  $('#editorialDrawerTitle').textContent='Delivery Center';
  $('#editorialDrawerBody').innerHTML=`
    <div class="selector-policy"><span>V0.23.4 · DELIVERY</span><b>Festival / social</b><small>Préflight avant transcodage</small></div>
    <div class="row"><label>Livrable</label><select id="deliveryTarget">
      ${deliveryTargetsCache.map(x=>`<option value="${x.id}" ${x.id===target.id?'selected':''}>${x.label}</option>`).join('')}
    </select></div>
    <div class="delivery-target-summary">
      <b>${target.label}</b>
      <span>${deliveryTechnicalSummary(target)}</span>
      ${(target.notes||[]).map(x=>`<small>${x}</small>`).join('')}
    </div>
    ${social?`
      <div class="row"><label>Cadrage</label><select id="deliveryFraming">
        ${target.framing_modes.map(x=>`<option value="${x}" ${x===framing?'selected':''}>${x==='fit'?'FIT · conserver toute l’image':'FILL · plein cadre avec crop'}</option>`).join('')}
      </select></div>
      <label class="check-row ${framing==='fill'?'':'delivery-crop-hidden'}" id="deliveryCropRow">
        <input id="deliveryAllowCrop" type="checkbox"> Autoriser explicitement le crop centré
      </label>
      <div class="hint">PISTE ne choisit pas de recadrage éditorial à ta place. FIT préserve tout le cadre ; FILL peut retirer une grande partie des bords.</div>
    `:''}
    <div id="deliveryPreflight"><div class="hint">Préflight en cours…</div></div>
    <div class="suggestion-actions">
      <button class="btn primary" id="deliveryExportBtn" onclick="runDeliveryExport()" disabled>Exporter le livrable</button>
      <button class="btn" onclick="closeEditorialDrawer()">Annuler</button>
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
  refreshDeliveryPreflight()
}
async function openDeliveryCenter(){
  if(!backendConnected)return toast('Backend local requis pour le Delivery Center',true);
  if(!activeVersion)return toast('Publie d’abord une version avant le delivery',true);
  try{
    const data=await api('/api/delivery/targets');
    deliveryTargetsCache=data.targets||[];
    renderDeliveryCenter()
  }catch(err){toast('Delivery : '+err.message,true)}
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
      ${result.requires_confirmation?'<div class="hint">Le bouton d’export reste volontairement disponible pour les avertissements : cliquer dessus vaut confirmation explicite. Un blocage de cadrage, lui, doit d’abord être résolu.</div>':''}
    `;
    if(button){
      button.disabled=!result.can_export;
      button.textContent=result.requires_confirmation?'Exporter avec avertissements':'Exporter le livrable'
    }
  }catch(err){
    if(root)root.innerHTML=`<div class="warn">Préflight impossible : ${err.message}</div>`;
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
        <div><span>LIVRABLE</span><b>${target.label||target.id}</b></div>
        <p>${p.width||'—'}×${p.height||'—'} · ${p.fps||'—'} fps · vidéo ${p.video_codec||'—'} · audio ${p.audio_codec||'—'} · ${p.audio_sample_rate||'—'} Hz</p>
        <div class="delivery-conformance ${conformState==='PASS'?'delivery-pass':'delivery-warn'}"><span>CONFORMITÉ</span><b>${conformState}</b></div>
        ${(conformance.reasons||[]).map(x=>`<em class="delivery-conformance-reason">${x}</em>`).join('')}
        <small>${r.path}</small>
        <div class="suggestion-actions">
          ${r.file_url?`<a class="btn primary" href="${r.file_url}" download>Télécharger le livrable</a>`:''}
          ${r.report_url?`<a class="btn" href="${r.report_url}" download>Rapport JSON</a>`:''}
        </div>
      </div>`;
    toast('Livrable créé · '+(target.label||target.id))
  }catch(err){
    if(result)result.innerHTML=`<div class="warn">Export impossible : ${err.message}</div>`;
    toast('Delivery : '+err.message,true)
  }finally{
    if(button)button.disabled=false
  }
}

if(typeof commands!=='undefined'&&!commands.some(c=>c.label==='Delivery · Festival / social')){
  commands.push({
    label:'Delivery · Festival / social',
    hint:'Export',
    keywords:'delivery export festival social vertical square prores youtube',
    run:()=>openDeliveryCenter(),
  })
}
