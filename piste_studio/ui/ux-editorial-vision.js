function visualWindowThreshold(level){
  if(level==='low')return 0.45;
  if(level==='high')return 0.22;
  return 0.32;
}

async function openEditorialWindows(dbId=null, level='normal'){
  const m=dbId?media.find(x=>x.dbId===+dbId):getMedia(selectedMedia);
  if(!m?.dbId){toast('Sélectionne un rush vidéo',true);return}
  if(!backendConnected){toast('Backend local requis',true);return}
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;
  $('#editorialDrawerTitle').textContent=`Fenêtres IN/OUT · ${m.label}`;
  body.innerHTML='<div class="editorial-loading">Détection locale des ruptures visuelles…</div>';
  try{
    const threshold=visualWindowThreshold(level);
    const r=await api(`/api/media/${m.dbId}/editorial-windows?threshold=${threshold}&min_duration=0.75&limit=12`);
    renderEditorialWindows(r,m,level);
  }catch(err){
    body.innerHTML=`<div class="warn">Détection indisponible : ${err.message}</div>`;
  }
}

function renderEditorialWindows(result,reference,level='normal'){
  const body=$('#editorialDrawerBody'),list=result.candidates||[];
  const changeCount=(result.scene_changes||[]).length;
  body.innerHTML=`
    <div class="selector-policy">
      <span>RUPTURES VISUELLES</span>
      <b>${reference.label}</b>
      <small>Suggestion locale · validation humaine · aucune coupe automatique</small>
    </div>
    <div class="form-grid">
      <div class="row">
        <label>Sensibilité</label>
        <select id="visualWindowSensitivity">
          <option value="low" ${level==='low'?'selected':''}>Faible</option>
          <option value="normal" ${level==='normal'?'selected':''}>Normale</option>
          <option value="high" ${level==='high'?'selected':''}>Forte</option>
        </select>
      </div>
      <div class="row"><label>Ruptures détectées</label><div class="readonly-value">${changeCount}</div></div>
    </div>
    <div class="hint">Seuil ffmpeg actuel : ${(+result.scene_threshold).toFixed(2)} · une sensibilité plus forte abaisse le seuil et peut proposer davantage de segments.</div>
    <div class="ins-actions"><button class="btn" onclick="openEditorialWindows(${reference.dbId},$('#visualWindowSensitivity').value)">Réanalyser</button></div>
    <div class="editorial-window-list">
      ${list.length?list.map((w,i)=>`
        <article class="suggestion-card editorial-window-card">
          <div class="suggestion-rank">${String(i+1).padStart(2,'0')}</div>
          <div class="suggestion-main">
            <div class="suggestion-head"><b>Fenêtre candidate</b><span>${(+w.duration).toFixed(2)} s</span></div>
            <div class="suggestion-range">${fmt(+w.source_in)} → ${fmt(+w.source_out)}</div>
            <div class="suggestion-reasons"><span>${w.reason}</span></div>
            <div class="suggestion-actions">
              <button class="btn" onclick="previewEditorialWindow(${reference.dbId},${+w.source_in},${+w.source_out},false)">Prévisualiser</button>
              <button class="btn primary" onclick="previewEditorialWindow(${reference.dbId},${+w.source_in},${+w.source_out},true)">Charger IN/OUT</button>
            </div>
          </div>
        </article>`).join(''):'<div class="editorial-empty large">Aucune fenêtre exploitable détectée.</div>'}
    </div>`;
}

function previewEditorialWindow(dbId,sourceIn,sourceOut,adopt=false){
  if(typeof previewSuggestion==='function'){
    previewSuggestion(dbId,sourceIn,sourceOut,adopt);
    if(adopt)toast('Fenêtre IN/OUT chargée en SOURCE');
    return;
  }
  const m=media.find(x=>x.dbId===+dbId);if(!m)return;
  selectedMedia=m.id;selectedClip=null;
  if(adopt){m.in=+sourceIn;m.out=+sourceOut}
  showSourceMedia(m,+sourceIn,false);renderMedia();renderMediaInspector();
}
