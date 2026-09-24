let semanticVisionStatusCache=null;
let semanticProposalCache=new Map();

async function loadSemanticVisionStatus(force=false){
  if(semanticVisionStatusCache&&!force)return semanticVisionStatusCache;
  if(!backendConnected)return null;
  try{
    semanticVisionStatusCache=await api('/api/vision/status');
    return semanticVisionStatusCache;
  }catch(_){return null}
}

function semanticVisionSummary(m){
  const p=m?.semanticProfile;
  if(p?.status==='READY'){
    return `<div class="vision-state ready"><span>◆ Vision locale</span><b>READY</b></div><div class="hint">${p.frame_count||0} image(s) de référence · modèle ${p.model_id||'local'}</div>`;
  }
  return '<div class="vision-state"><span>◇ Vision locale</span><b>NON ANALYSÉE</b></div><div class="hint">Aucun tag n’est écrit automatiquement.</div>';
}

function appendSemanticVisionSection(){
  const m=getMedia(selectedMedia),root=$('#inspector');if(!m||!root||!m.dbId)return;
  const section=document.createElement('div');
  section.className='inspector-section semantic-vision-section';
  section.innerHTML=`<div class="inspector-section-title">SEMANTIC VISION</div>
    ${semanticVisionSummary(m)}
    <div class="ins-actions">
      <button class="btn" onclick="analyzeSemanticSelected(false)">${m.semanticProfile?.status==='READY'?'Réanalyser vision':'Analyser vision'}</button>
      <button class="btn" onclick="openTargetedReferenceManager(${m.dbId})">Référence ciblée${m.semanticReferenceCount?` · ${m.semanticReferenceCount}`:''}</button>
      <button class="btn primary" onclick="openSemanticContinuity(${m.dbId})">Proposer continuité</button>
    </div>
    <div class="hint">Les propositions character / prop / decor / look peuvent utiliser des références de rush entier ou des frames/zones explicitement validés.</div>`;
  root.appendChild(section);
}

const _v017RenderMediaInspectorSemantic=renderMediaInspector;
renderMediaInspector=function(){
  _v017RenderMediaInspectorSemantic();
  appendSemanticVisionSection();
}

async function analyzeSemanticSelected(allowModelDownload=false){
  const m=getMedia(selectedMedia);
  if(!m?.dbId){toast('Sélectionne un rush vidéo catalogué',true);return}
  if(!backendConnected){toast('Backend local requis',true);return}
  try{
    toast(allowModelDownload?'Chargement du modèle vision…':`Vision locale · ${m.label}…`);
    await api(`/api/vision/analyze/${m.dbId}`,{
      method:'POST',
      body:JSON.stringify({
        allow_model_download:!!allowModelDownload,
        force_frames:false,
      }),
    });
    const dbId=m.dbId;
    await hydrateBackend();
    const restored=media.find(x=>x.dbId===dbId);
    if(restored){selectedMedia=restored.id;selectedClip=null;renderMedia();renderMediaInspector()}
    semanticVisionStatusCache=null;
    toast('Profil vision local créé');
  }catch(err){
    openVisionSetupDrawer(err.message,m,allowModelDownload);
  }
}

async function openVisionSetupDrawer(message,m,downloadAttempted=false){
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;
  $('#editorialDrawerTitle').textContent='Vision locale';
  const status=await loadSemanticVisionStatus(true);
  const deps=status?.dependencies_ready?'Dépendances installées':'Dépendances vision absentes';
  const cache=status?.model_cached===true?'Modèle en cache':status?.model_cached===false?'Modèle absent du cache':'Cache modèle inconnu';
  const ff=status?.ffmpeg_ready?'ffmpeg prêt':'ffmpeg absent';
  body.innerHTML=`<div class="selector-policy"><span>SEMANTIC VISION</span><b>${m?.label||'Rush sélectionné'}</b><small>Images traitées localement. Aucun média n’est envoyé vers un service externe.</small></div>
    <div class="vision-setup-status"><span>${deps}</span><span>${cache}</span><span>${ff}</span></div>
    <div class="warn">${message||status?.message||'Vision locale indisponible.'}</div>
    <div class="vision-setup-note">L’option de téléchargement ne télécharge que le modèle configuré. Les images du projet restent locales.</div>
    <div class="suggestion-actions">
      ${status?.dependencies_ready&&status?.ffmpeg_ready&&status?.model_cached===false&&!downloadAttempted?'<button class="btn primary" onclick="analyzeSemanticSelected(true)">Autoriser le téléchargement du modèle</button>':''}
    </div>`;
}

async function openSemanticContinuity(dbId=null){
  const m=dbId?media.find(x=>x.dbId===+dbId):getMedia(selectedMedia);
  if(!m?.dbId){toast('Sélectionne un rush vidéo',true);return}
  if(!backendConnected){toast('Backend local requis',true);return}
  if(!m.semanticProfile||m.semanticProfile.status!=='READY'){
    openVisionSetupDrawer('Analyse ce rush avant de proposer des tags de continuité.',m,false);
    return;
  }
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;
  $('#editorialDrawerTitle').textContent=`Continuité · ${m.label}`;
  body.innerHTML='<div class="editorial-loading">Comparaison aux références validées…</div>';
  try{
    const r=await api(`/api/vision/propose/${m.dbId}`,{
      method:'POST',
      body:JSON.stringify({reset_rejected:false,edit_name:activeEditName}),
    });
    renderSemanticProposals(r,m);
  }catch(err){
    body.innerHTML=`<div class="warn">Vision sémantique indisponible : ${err.message}</div>`;
  }
}

function semanticReferenceNames(evidence){
  const ids=evidence?.reference_media_ids||[];
  return ids.map(id=>media.find(x=>x.dbId===+id)?.label||`Média ${id}`);
}

function canonAssessmentLabel(status){
  return ({
    ALIGNED:'CANON ALIGNÉ',
    UNVERIFIED:'NON VÉRIFIÉ',
    CONFLICT:'CONFLIT CANON',
    HARD_LOCK:'HARD LOCK',
    REVIEW:'À REVOIR',
  })[status]||status||'NON VÉRIFIÉ';
}

function canonAssessmentMarkup(assessment){
  if(!assessment)return '';
  const status=assessment.status||'UNVERIFIED';
  const findings=assessment.findings||[];
  return `<div class="canon-assessment canon-${String(status).toLowerCase().replace('_','-')}">
    <div class="suggestion-head"><b>${canonAssessmentLabel(status)}</b><span>${assessment.requires_explicit_acknowledgement?'acquittement requis':'informatif'}</span></div>
    <div class="suggestion-reasons">${findings.map(f=>`<span>${f.message}</span>`).join('')}</div>
    ${findings.map(f=>f.source?`<div class="vision-evidence">Source · ${f.source}</div>`:'').join('')}
  </div>`;
}

function openCanonConflictConfirmation(id,dbId){
  const p=semanticProposalCache.get(+id);
  if(!p)return;
  const a=p.canon_assessment||{};
  const body=$('#editorialDrawerBody');
  $('#editorialDrawerTitle').textContent=`Conflit Canon · ${p.tag}`;
  body.innerHTML=`
    <div class="selector-policy"><span>VALIDATION EXPLICITE</span><b>${canonAssessmentLabel(a.status)}</b><small>Aucune modification n’a encore été effectuée.</small></div>
    ${canonAssessmentMarkup(a)}
    <div class="warn">Accepter malgré ce signal ajoutera explicitement le tag <b>${p.tag}</b> au média. Le Canon et les locks ne seront pas modifiés.</div>
    <div class="suggestion-actions">
      <button class="btn primary" onclick="resolveSemanticProposalUI(${p.id},true,${dbId},true)">Accepter malgré conflit</button>
      <button class="btn" onclick="refreshSemanticProposals(media.find(x=>x.dbId===+${dbId}))">Revenir</button>
    </div>`;
}

function renderSemanticProposals(result,m){
  const body=$('#editorialDrawerBody'),rows=result.proposals||[];
  semanticProposalCache=new Map(rows.map(p=>[+p.id,p]));
  const pending=rows.filter(x=>x.status==='PENDING');
  const resolved=rows.filter(x=>x.status!=='PENDING');
  const policy='<small>Validation humaine requise · aucun tag ni montage modifié automatiquement</small>';
  let html=`<div class="selector-policy"><span>RÉFÉRENCES VISUELLES VALIDÉES</span><b>${m.label}</b>${policy}</div>`;
  if(!pending.length){
    html+='<div class="editorial-empty large">Aucune nouvelle proposition au-dessus des seuils de continuité.</div>';
  }else{
    html+=pending.map(p=>{
      const pct=Math.round((+p.confidence||0)*100);
      const refs=semanticReferenceNames(p.evidence);
      const threshold=Math.round((+p.evidence?.threshold||0)*100);
      return `<article class="semantic-proposal-card">
        <div class="semantic-proposal-main">
          <div class="suggestion-head"><b>${p.tag}</b><span>${pct} %</span></div>
          <div class="semantic-facet">${p.facet.toUpperCase()} · seuil ${threshold} %</div>
          <div class="suggestion-reasons">
            <span>${p.evidence?.reference_count||0} référence(s)</span>
            ${p.evidence?.reference_group_count?`<span>${p.evidence.reference_group_count} groupe(s)</span>`:'' }
            ${p.evidence?.targeted_reference_count?`<span>${p.evidence.targeted_reference_count} ciblée(s)</span>`:'' }
            ${p.evidence?.quality_distribution?`<span>P/S/F · ${p.evidence.quality_distribution.primary||0}/${p.evidence.quality_distribution.secondary||0}/${p.evidence.quality_distribution.low||0}</span>`:'' }
            ${p.evidence?.best_targeted_reference_id?`<span>cible #${p.evidence.best_targeted_reference_id}</span>`:'' }
            ${refs.slice(0,3).map(x=>`<span>${x}</span>`).join('')}
          </div>
          <div class="vision-evidence">Meilleure référence : ${Math.round((+p.evidence?.best_reference_similarity||0)*100)} %</div>
          <div class="suggestion-actions"><button class="btn primary" onclick="resolveSemanticProposalUI(${p.id},true,${m.dbId})">Accepter</button><button class="btn" onclick="resolveSemanticProposalUI(${p.id},false,${m.dbId})">Rejeter</button></div>
        </div>
      </article>`;
    }).join('');
  }
  if(resolved.length){
    html+=`<div class="semantic-resolved"><div class="inspector-section-title">HISTORIQUE</div>${resolved.map(p=>`<div class="semantic-resolved-row ${p.status.toLowerCase()}"><span>${p.tag}</span><b>${p.status}</b></div>`).join('')}</div>`;
  }
  body.innerHTML=html;
}

async function resolveSemanticProposalUI(id,accept,dbId,acknowledgeCanonConflict=false){
  try{
    const result=await api(`/api/vision/proposals/${id}/resolve`,{
      method:'POST',
      body:JSON.stringify({accept:!!accept,acknowledge_canon_conflict:!!acknowledgeCanonConflict,edit_name:activeEditName}),
    });
    if(result.proposal?.resolution_status==='REQUIRES_ACKNOWLEDGEMENT'){
      semanticProposalCache.set(+id,result.proposal);
      openCanonConflictConfirmation(id,dbId);
      return;
    }
    const keepDbId=+dbId;
    await hydrateBackend();
    const restored=media.find(x=>x.dbId===keepDbId);
    if(restored){
      selectedMedia=restored.id;selectedClip=null;renderMedia();renderMediaInspector();
      await refreshSemanticProposals(restored);
    }
    toast(accept?'Tag de continuité accepté':'Proposition rejetée');
  }catch(err){toast('Décision vision impossible : '+err.message,true)}
}

async function refreshSemanticProposals(m){
  const body=$('#editorialDrawerBody');
  if(!body||$('#editorialDrawer').hidden)return;
  try{
    const r=await api(`/api/vision/proposals/${m.dbId}?edit_name=${encodeURIComponent(activeEditName)}`);
    $('#editorialDrawerTitle').textContent=`Continuité · ${m.label}`;
    renderSemanticProposals(r,m);
  }catch(err){body.innerHTML=`<div class="warn">${err.message}</div>`}
}
