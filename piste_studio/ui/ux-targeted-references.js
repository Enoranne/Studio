let targetedReferenceActiveMediaDbId=null;

function currentReferenceFrameTime(m){
  const video=$('#video');
  const same=typeof currentMonitorMedia!=='undefined'&&currentMonitorMedia===m.id;
  if(video&&same&&Number.isFinite(video.currentTime)){
    return Math.max(0,Math.min(m.duration||video.duration||0,+video.currentTime||0));
  }
  return Math.max(0,+m.in||0);
}

function targetedRoiFromForm(){
  const mode=$('#targetedReferenceMode')?.value||'full';
  if(mode==='full')return {x:0,y:0,width:1,height:1};
  const pct=id=>Math.max(0,Math.min(100,+$(id)?.value||0))/100;
  const x=pct('#targetedRoiX'),y=pct('#targetedRoiY');
  const width=Math.max(.05,Math.min(1-x,pct('#targetedRoiW')));
  const height=Math.max(.05,Math.min(1-y,pct('#targetedRoiH')));
  return {x,y,width,height};
}

function toggleTargetedRoiFields(){
  const box=$('#targetedRoiFields');if(!box)return;
  box.hidden=($('#targetedReferenceMode')?.value||'full')==='full';
}

function useDisplayedReferenceFrame(){
  const m=media.find(x=>x.dbId===+targetedReferenceActiveMediaDbId);
  if(!m)return;
  const input=$('#targetedReferenceTime');
  if(input)input.value=currentReferenceFrameTime(m).toFixed(3);
  toast('Timecode du Viewer repris');
}

async function openTargetedReferenceManager(dbId=null){
  const m=dbId?media.find(x=>x.dbId===+dbId):getMedia(selectedMedia);
  if(!m?.dbId){toast('Sélectionne un rush vidéo',true);return}
  if(!backendConnected){toast('Backend local requis',true);return}
  targetedReferenceActiveMediaDbId=m.dbId;
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;
  $('#editorialDrawerTitle').textContent=`Références ciblées · ${m.label}`;
  body.innerHTML='<div class="editorial-loading">Chargement des références…</div>';
  try{
    const [r,g]=await Promise.all([
      api(`/api/vision/references?media_id=${m.dbId}`),
      api('/api/vision/reference-groups'),
    ]);
    renderTargetedReferenceManager(m,r.references||[],g.groups||[]);
  }catch(err){
    body.innerHTML=`<div class="warn">Références indisponibles : ${err.message}</div>`;
  }
}

function renderTargetedReferenceManager(m,refs,groups=[]){
  const body=$('#editorialDrawerBody');
  const t=currentReferenceFrameTime(m);
  const groupNames=[...new Set(groups.map(group=>group.group_name).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  const groupOptions=groupNames.map(name=>`<option value="${name}"></option>`).join('');
  const groupSummary=groups.length?groups.map(group=>`<div class="semantic-resolved-row"><span>${group.tag} · ${group.group_name}</span><b>${group.reference_count} réf. · poids ${(+group.total_quality_weight||0).toFixed(1)}</b></div>`).join(''):'<div class="hint">Aucun groupe défini : les références sans groupe restent des preuves indépendantes.</div>';
  const cards=refs.length?refs.map(ref=>{
    const roi=ref.roi||{x:0,y:0,width:1,height:1};
    const full=Math.abs((roi.width||1)-1)<.001&&Math.abs((roi.height||1)-1)<.001&&Math.abs(roi.x||0)<.001&&Math.abs(roi.y||0)<.001;
    const zone=full?'frame entier':`zone ${Math.round((roi.x||0)*100)}%, ${Math.round((roi.y||0)*100)}% · ${Math.round((roi.width||1)*100)}×${Math.round((roi.height||1)*100)}%`;
    return `<article class="semantic-proposal-card targeted-reference-card" data-reference-id="${ref.id}">
      <div class="semantic-proposal-main">
        <div class="suggestion-head"><b>${ref.tag}</b><span>@ ${(+ref.timestamp_seconds).toFixed(2)} s</span></div>
        <div class="semantic-facet">${String(ref.facet||'').toUpperCase()} · ${zone}</div>
        <div class="suggestion-reasons">
          <span>${ref.group_name?`Groupe · ${ref.group_name}`:'Sans groupe'}</span>
          <span>Qualité · ${ref.quality==='primary'?'Primaire':ref.quality==='low'?'Faible':'Secondaire'} · poids ${(+ref.quality_weight||1).toFixed(1)}</span>
        </div>
        <div class="form-grid">
          <div class="row"><label>Groupe</label><input id="referenceGroup_${ref.id}" list="targetedReferenceGroups" value="${ref.group_name||''}" placeholder="ex. Fisher principal"></div>
          <div class="row"><label>Qualité</label><select id="referenceQuality_${ref.id}"><option value="primary" ${ref.quality==='primary'?'selected':''}>Primaire · 1,5×</option><option value="secondary" ${ref.quality==='secondary'?'selected':''}>Secondaire · 1,0×</option><option value="low" ${ref.quality==='low'?'selected':''}>Faible · 0,5×</option></select></div>
        </div>
        ${ref.image_url?`<img src="${ref.image_url}" alt="Référence ${ref.tag}" style="display:block;max-width:100%;max-height:180px;object-fit:contain;margin:8px 0;border-radius:4px">`:''}
        <div class="suggestion-actions"><button class="btn primary" onclick="updateTargetedReferenceMeta(${ref.id},${m.dbId})">Enregistrer groupe/qualité</button><button class="btn" onclick="deleteTargetedReference(${ref.id},${m.dbId})">Supprimer</button></div>
      </div>
    </article>`;
  }).join(''):'<div class="editorial-empty">Aucune référence ciblée sur ce rush.</div>';

  body.innerHTML=`
    <div class="selector-policy"><span>RÉFÉRENCE CIBLÉE</span><b>${m.label}</b><small>Frame/zone explicitement choisie · aucun tag global ajouté au rush</small></div>
    <div id="targetedReferenceError"></div>
    <datalist id="targetedReferenceGroups">${groupOptions}</datalist>
    <div class="inspector-section-title">GROUPES DE RÉFÉRENCES · PROJET</div>
    <div class="semantic-resolved">${groupSummary}</div>
    <div class="form-grid">
      <div class="row"><label>Facet</label><select id="targetedReferenceFacet"><option value="character">Character</option><option value="prop">Prop</option><option value="decor">Decor</option><option value="look">Look</option></select></div>
      <div class="row"><label>Valeur</label><input id="targetedReferenceValue" placeholder="ex. fisher"></div>
      <div class="row"><label>Frame (s)</label><input id="targetedReferenceTime" type="number" min="0" max="${m.duration||99999}" step="0.01" value="${t.toFixed(3)}"></div>
      <div class="row"><label>Groupe</label><input id="targetedReferenceGroup" list="targetedReferenceGroups" placeholder="ex. Fisher principal"></div>
      <div class="row"><label>Qualité</label><select id="targetedReferenceQuality"><option value="primary">Primaire · 1,5×</option><option value="secondary" selected>Secondaire · 1,0×</option><option value="low">Faible · 0,5×</option></select></div>
      <div class="row"><label>Cadrage</label><select id="targetedReferenceMode" onchange="toggleTargetedRoiFields()"><option value="full">Frame entier</option><option value="roi">Zone de l’image</option></select></div>
    </div>
    <div class="form-grid" id="targetedRoiFields" hidden>
      <div class="row"><label>X %</label><input id="targetedRoiX" type="number" min="0" max="95" step="1" value="20"></div>
      <div class="row"><label>Y %</label><input id="targetedRoiY" type="number" min="0" max="95" step="1" value="20"></div>
      <div class="row"><label>Largeur %</label><input id="targetedRoiW" type="number" min="5" max="100" step="1" value="60"></div>
      <div class="row"><label>Hauteur %</label><input id="targetedRoiH" type="number" min="5" max="100" step="1" value="60"></div>
    </div>
    <div class="hint">Les coordonnées de zone sont normalisées en pourcentage de l’image. Le crop est effectué localement avant calcul de l’embedding. Dans un même groupe : Primaire = 1,5×, Secondaire = 1,0×, Faible = 0,5×. Les groupes contribuent ensuite à poids égal.</div>
    <div class="suggestion-actions">
      <button class="btn" onclick="useDisplayedReferenceFrame()">Utiliser le frame affiché</button>
      <button class="btn primary" onclick="saveTargetedReference(false)">Créer la référence</button>
    </div>
    <div class="inspector-section-title" style="margin-top:14px">RÉFÉRENCES DE CE RUSH</div>
    <div class="targeted-reference-list">${cards}</div>`;
}

async function saveTargetedReference(allowModelDownload=false){
  const m=media.find(x=>x.dbId===+targetedReferenceActiveMediaDbId);
  if(!m)return;
  const facet=$('#targetedReferenceFacet')?.value||'';
  const value=($('#targetedReferenceValue')?.value||'').trim().toLowerCase();
  if(!value){toast('Renseigne la valeur de référence',true);return}
  const tag=`${facet}:${value}`;
  const timestamp=+$('#targetedReferenceTime')?.value||0;
  const groupName=($('#targetedReferenceGroup')?.value||'').trim();
  const quality=$('#targetedReferenceQuality')?.value||'secondary';
  const roi=targetedRoiFromForm();
  const error=$('#targetedReferenceError');
  if(error)error.innerHTML='<div class="editorial-loading">Extraction du frame et calcul de la référence…</div>';
  try{
    await api('/api/vision/references',{
      method:'POST',
      body:JSON.stringify({media_id:m.dbId,tag,timestamp_seconds:timestamp,roi,group_name:groupName,quality,allow_model_download:!!allowModelDownload}),
    });
    const keepDbId=m.dbId;
    await hydrateBackend();
    const restored=media.find(x=>x.dbId===keepDbId);
    if(restored){selectedMedia=restored.id;selectedClip=null;renderMedia();renderMediaInspector()}
    toast(`Référence ciblée créée · ${tag}`);
    await openTargetedReferenceManager(keepDbId);
  }catch(err){
    if(error)error.innerHTML=`<div class="warn">${err.message}</div><div class="suggestion-actions"><button class="btn" onclick="saveTargetedReference(true)">Autoriser le téléchargement du modèle et réessayer</button></div>`;
    else toast('Référence ciblée impossible : '+err.message,true);
  }
}

async function deleteTargetedReference(referenceId,dbId){
  try{
    await api(`/api/vision/references/${referenceId}`,{method:'DELETE'});
    await hydrateBackend();
    const restored=media.find(x=>x.dbId===+dbId);
    if(restored){selectedMedia=restored.id;selectedClip=null;renderMedia();renderMediaInspector()}
    toast('Référence ciblée supprimée');
    await openTargetedReferenceManager(dbId);
  }catch(err){toast('Suppression impossible : '+err.message,true)}
}


async function updateTargetedReferenceMeta(referenceId,dbId){
  const groupName=($('#referenceGroup_'+referenceId)?.value||'').trim();
  const quality=$('#referenceQuality_'+referenceId)?.value||'secondary';
  try{
    await api(`/api/vision/references/${referenceId}`,{
      method:'PATCH',
      body:JSON.stringify({group_name:groupName,quality}),
    });
    toast('Groupe et qualité enregistrés');
    await openTargetedReferenceManager(dbId);
  }catch(err){toast('Mise à jour impossible : '+err.message,true)}
}
