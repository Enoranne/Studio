function readinessEscape(value){
  return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function readinessStatusClass(status){
  const s=String(status||'').toLowerCase();
  if(s==='pass'||s==='ready_for_delivery')return'readiness-pass';
  if(s==='blocked')return'readiness-blocked';
  return'readiness-warn';
}

function readinessCapability(label,value){
  return `<div class="readiness-capability ${value?'on':'off'}"><span>${readinessEscape(label)}</span><b>${value?'PRÊT':'PAS ENCORE'}</b></div>`;
}

function readinessCheckDetails(item){
  const bits=[];
  if(item.video_count!=null)bits.push(`${item.video_count} vidéo`);
  if(item.audio_count!=null)bits.push(`${item.audio_count} audio`);
  if(item.video_cuts!=null)bits.push(`${item.video_cuts} coupe(s) vidéo`);
  if(item.audio_cuts!=null)bits.push(`${item.audio_cuts} coupe(s) audio`);
  if(item.title_cuts!=null)bits.push(`${item.title_cuts} titre(s)`);
  if(item.detected_version)bits.push(`Tesseract ${item.detected_version}`);
  if(item.missing_files?.length)bits.push(`${item.missing_files.length} fichier(s) manquant(s)`);
  return bits.length?`<small>${bits.map(readinessEscape).join(' · ')}</small>`:'';
}

function renderProductionReadiness(report){
  const body=$('#editorialDrawerBody');
  if(!body)return;
  const caps=report.capabilities||{},selection=report.selection||{},checks=report.checks||[];
  const pipeline=String(report.pipeline_status||'IN_PROGRESS');
  body.innerHTML=`
    <section class="readiness-summary ${readinessStatusClass(pipeline)}">
      <div class="readiness-summary-head">
        <span>PRODUCTION VALIDATION · V${readinessEscape(report.version||'0.24.0')}</span>
        <b>${readinessEscape(pipeline.replaceAll('_',' '))}</b>
      </div>
      <strong>${readinessEscape(report.project_name||'Projet PISTE')}</strong>
      <p>${selection.edit_name&&selection.version
        ?`Recette ciblée : ${readinessEscape(selection.edit_name)} / ${readinessEscape(selection.version)}`
        :'Aucune version timeline unique sélectionnée.'}</p>
    </section>
    <div class="readiness-capabilities">
      ${readinessCapability('Montage',caps.can_start_editing)}
      ${readinessCapability('Bootstrap',caps.can_bootstrap)}
      ${readinessCapability('Authoring',caps.can_author)}
      ${readinessCapability('Delivery',caps.can_deliver)}
    </div>
    <div class="readiness-section-title">CONTRÔLES</div>
    <div class="readiness-checks">
      ${checks.map(item=>`
        <article class="readiness-check ${readinessStatusClass(item.status)}">
          <div><span>${readinessEscape(item.id).replaceAll('_',' ')}</span><b>${readinessEscape(item.status)}</b></div>
          <p>${readinessEscape(item.message)}</p>
          ${readinessCheckDetails(item)}
        </article>`).join('')}
    </div>
    <section class="readiness-next">
      <span>PROCHAINE ACTION</span>
      <p>${readinessEscape(report.next_action||'Aucune action requise.')}</p>
    </section>
    <div class="readiness-actions">
      <button class="btn" onclick="openProductionReadiness()">Actualiser</button>
      ${caps.can_deliver?'<button class="btn accent" onclick="closeEditorialDrawer();openDeliveryCenter()">Ouvrir Delivery Center</button>':''}
    </div>
    <div class="hint">Ce diagnostic ne modifie ni la timeline, ni les médias, ni le master. Les actions de production restent explicites.</div>
  `;
}

async function openProductionReadiness(){
  if(!backendConnected){toast('Backend local requis pour le Production Readiness',true);return}
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;
  $('#editorialDrawerTitle').textContent='Production Readiness';
  body.innerHTML='<div class="editorial-loading">Vérification du projet, des outils et de la chaîne Tesseract…</div>';
  try{
    const params=new URLSearchParams();
    if(activeEditName)params.set('edit_name',activeEditName);
    const activeRecord=(backendState?.versions||[]).find(
      item=>item.edit_name===activeEditName&&item.version_label===activeVersion
    );
    if(activeRecord&&activeVersion)params.set('version',activeVersion);
    const suffix=params.toString()?`?${params.toString()}`:'';
    const report=await api('/api/readiness'+suffix);
    renderProductionReadiness(report);
  }catch(err){
    body.innerHTML=`<div class="readiness-check readiness-blocked"><div><span>readiness</span><b>ERREUR</b></div><p>${readinessEscape(err.message)}</p></div>`;
  }
}
