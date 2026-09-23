let editorialMarkers=[];

function hydrateEditorialState(state){
  editorialMarkers=(state?.markers||[]).map(x=>({...x}));
  requestAnimationFrame(renderEditorialMarkers);
}

function editorialRangeBands(m){
  const ranges=m.editorialRanges||[];
  if(!ranges.length){
    const left=Math.max(0,Math.min(100,(m.in||0)/m.duration*100));
    const width=Math.max(2,Math.min(100-left,((m.out??m.duration)-(m.in||0))/m.duration*100));
    return `<span class="favorite-band" style="left:${left}%;width:${width}%"></span><span class="reject-band" style="left:${left}%;width:${width}%"></span>`;
  }
  return ranges.map(r=>{
    const left=Math.max(0,Math.min(100,(+r.source_in||0)/m.duration*100));
    const width=Math.max(1,Math.min(100-left,((+r.source_out||0)-(+r.source_in||0))/m.duration*100));
    return `<span class="${r.kind==='favorite'?'favorite-band':'reject-band'} persistent-range" data-range-id="${r.id}" style="display:block;left:${left}%;width:${width}%"></span>`;
  }).join('');
}

const _v015MarkRange=markRange;
markRange=async function(kind){
  if(viewerMode!=='source'){toast('Passe en SOURCE pour noter un rush',true);return}
  const m=getMedia(selectedMedia);if(!m)return;
  if(!backendConnected||!m.dbId)return _v015MarkRange(kind);
  try{
    const r=await api(`/api/media/${m.dbId}/ranges`,{
      method:'POST',
      body:JSON.stringify({
        kind,
        source_in:+(m.in||0),
        source_out:+(m.out??m.duration),
      }),
    });
    m.editorialRanges=r.ranges||[];
    m.favorite=m.editorialRanges.some(x=>x.kind==='favorite');
    m.rejected=m.editorialRanges.some(x=>x.kind==='reject');
    renderMedia();renderMediaInspector();renderIndex();
    toast(kind==='favorite'?'Favorite enregistrée':'Reject enregistré');
  }catch(err){toast('Marquage éditorial refusé : '+err.message,true)}
}

async function removeEditorialRange(id){
  const m=getMedia(selectedMedia);if(!m)return;
  if(backendConnected){
    try{await api(`/api/editorial/ranges/${id}`,{method:'DELETE'})}
    catch(err){toast('Suppression impossible : '+err.message,true);return}
  }
  m.editorialRanges=(m.editorialRanges||[]).filter(r=>+r.id!==+id);
  m.favorite=m.editorialRanges.some(x=>x.kind==='favorite');
  m.rejected=m.editorialRanges.some(x=>x.kind==='reject');
  renderMedia();renderMediaInspector();toast('Plage éditoriale supprimée');
}

function editorialRangeList(m){
  const ranges=m.editorialRanges||[];
  if(!ranges.length)return '<div class="editorial-empty">Aucune plage persistée.</div>';
  return ranges.map(r=>`<div class="range-chip ${r.kind}"><span><b>${r.kind==='favorite'?'★ Favorite':'× Reject'}</b> ${fmt(+r.source_in)} → ${fmt(+r.source_out)}</span><button onclick="removeEditorialRange(${r.id})" title="Supprimer">×</button></div>`).join('');
}

function appendEditorialMediaSection(){
  const m=getMedia(selectedMedia),root=$('#inspector');if(!m||!root)return;
  const section=document.createElement('div');section.className='inspector-section editorial-inspector-section';
  section.innerHTML=`<div class="inspector-section-title">EDITORIAL</div><div class="editorial-range-list">${editorialRangeList(m)}</div><div class="ins-actions"><button class="btn primary" onclick="openSourceSelector(${m.dbId||'null'})">Alternatives</button><button class="btn" onclick="markRange('favorite')">★ Favorite</button><button class="btn" onclick="markRange('reject')">Reject</button></div><div class="hint">Les alternatives sont classées et expliquées. Aucun remplacement n’est automatique.</div>`;
  root.appendChild(section);
}

const _v015RenderMediaInspector=renderMediaInspector;
renderMediaInspector=function(){_v015RenderMediaInspector();appendEditorialMediaSection()}

const _v015RenderInspectorEditorial=renderInspector;
renderInspector=function(){
  _v015RenderInspectorEditorial();
  const c=getClip(selectedClip),root=$('#inspector');if(!c?.mediaId||!root)return;
  const m=getMedia(c.mediaId);if(!m)return;
  const section=document.createElement('div');section.className='inspector-section editorial-inspector-section';
  section.innerHTML=`<div class="inspector-section-title">EDITORIAL SOURCE</div><div class="editorial-source-current"><span>Prise actuelle</span><b>${m.label}</b></div><div class="ins-actions"><button class="btn primary" onclick="openSourceSelector(${m.dbId||'null'})">Trouver des alternatives</button></div><div class="hint">Le Source Selector propose uniquement des candidats. La Storyline reste inchangée.</div>`;
  root.insertBefore(section,root.lastElementChild);
}

function closeEditorialDrawer(){$('#editorialDrawer').hidden=true}
async function openSourceSelector(dbId=null){
  const m=dbId?media.find(x=>x.dbId===+dbId):getMedia(selectedMedia);
  if(!m){toast('Sélectionne un rush vidéo',true);return}
  if(!backendConnected||!m.dbId){toast('Backend local requis pour les alternatives',true);return}
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;$('#editorialDrawerTitle').textContent=`Alternatives · ${m.label}`;
  body.innerHTML='<div class="editorial-loading">Analyse des candidats…</div>';
  try{
    const r=await api(`/api/editorial/suggest/${m.dbId}?limit=6&max_spoiler=${m.spoiler||0}`);
    renderSourceSuggestions(r,m);
  }catch(err){body.innerHTML=`<div class="warn">Suggestions indisponibles : ${err.message}</div>`}
}
function renderSourceSuggestions(result,reference){
  const body=$('#editorialDrawerBody'),list=result.suggestions||[];
  if(!list.length){body.innerHTML='<div class="editorial-empty large">Aucune alternative admissible pour ce niveau de spoiler.</div>';return}
  body.innerHTML=`<div class="selector-policy"><span>Référence</span><b>${reference.label}</b><small>Validation humaine requise · aucun remplacement automatique</small></div>`+
  list.map((s,i)=>`<article class="suggestion-card">
    <div class="suggestion-rank">${String(i+1).padStart(2,'0')}</div>
    <div class="suggestion-main">
      <div class="suggestion-head"><b>${s.title}</b><span>${s.score.toFixed(1)}</span></div>
      <div class="suggestion-range">${fmt(s.source_in)} → ${fmt(s.source_out)} · ${s.range_reason}</div>
      <div class="suggestion-reasons">${s.reasons.map(x=>`<span>${x}</span>`).join('')}</div>
      <div class="suggestion-actions"><button class="btn" onclick="previewSuggestion(${s.media_id},${s.source_in},${s.source_out},false)">Prévisualiser</button><button class="btn primary" onclick="previewSuggestion(${s.media_id},${s.source_in},${s.source_out},true)">Charger la plage</button></div>
    </div>
  </article>`).join('');
}
function previewSuggestion(dbId,sourceIn,sourceOut,adopt=false){
  const m=media.find(x=>x.dbId===+dbId);if(!m)return;
  selectedMedia=m.id;selectedClip=null;
  if(adopt){m.in=+sourceIn;m.out=+sourceOut}
  showSourceMedia(m,+sourceIn,false);renderMedia();renderMediaInspector();
  if(adopt)toast('Plage candidate chargée en SOURCE');
}

function renderEditorialMarkers(){
  const ruler=$('#ruler');if(!ruler)return;
  ruler.querySelectorAll('.editorial-marker').forEach(x=>x.remove());
  editorialMarkers.forEach(marker=>{
    const b=document.createElement('button');
    b.className=`editorial-marker marker-${marker.kind||'note'}`;
    b.style.left=`${Math.max(0,Math.min(100,(+marker.time_seconds||0)/DURATION*100))}%`;
    b.title=`${marker.label} · ${fmt(+marker.time_seconds||0)}`;
    b.dataset.markerId=marker.id;
    b.onclick=e=>{e.stopPropagation();setViewerMode('program',{silent:true});setPlayhead(+marker.time_seconds||0);toast(marker.label)};
    ruler.appendChild(b);
  });
}

function openMarkerComposer(){
  const box=$('#markerComposer');box.hidden=false;
  $('#markerTimeLabel').textContent=fmt(playhead);
  $('#markerLabel').value='';
  requestAnimationFrame(()=>$('#markerLabel').focus());
}
function closeMarkerComposer(){$('#markerComposer').hidden=true}
async function saveMarker(){
  const label=$('#markerLabel').value.trim(),kind=$('#markerKind').value;
  if(!label){toast('Donne un nom au marqueur',true);return}
  if(backendConnected){
    try{
      const r=await api('/api/markers',{method:'POST',body:JSON.stringify({edit_name:activeEditName,time_seconds:playhead,label,kind})});
      editorialMarkers.push(r.marker);
    }catch(err){toast('Marqueur refusé : '+err.message,true);return}
  }else{
    editorialMarkers.push({id:'local-'+Date.now(),edit_name:activeEditName,time_seconds:playhead,label,kind});
  }
  closeMarkerComposer();renderEditorialMarkers();toast(`Marker · ${label}`);
}
$('#markerSaveBtn').onclick=saveMarker;
$('#markerLabel').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();saveMarker()}if(e.key==='Escape')closeMarkerComposer()});
document.addEventListener('pointerdown',e=>{const box=$('#markerComposer');if(box&&!box.hidden&&!e.target.closest('#markerComposer')&&!e.target.closest('#addMarkerBtn'))closeMarkerComposer()});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&!$('#editorialDrawer').hidden){closeEditorialDrawer();return}
  if(e.target.matches('input,select,textarea'))return;
  if(e.key.toLowerCase()==='m'){e.preventDefault();openMarkerComposer()}
});

const _v015RenderTracksForMarkers=renderTracks;
renderTracks=function(){_v015RenderTracksForMarkers();requestAnimationFrame(renderEditorialMarkers)}
