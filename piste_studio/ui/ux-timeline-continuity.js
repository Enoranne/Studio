let timelineContinuityLastResult=null;

function continuityStatusLabel(status){
  return ({
    CONTINUOUS:'CONTINUITÉ',
    RUPTURE:'RUPTURE POTENTIELLE',
    INSUFFICIENT:'PREUVES INSUFFISANTES',
    NO_SIGNAL:'AUCUN SIGNAL',
  })[status]||status||'AUCUN SIGNAL';
}

function appendTimelineContinuitySection(){
  const c=getClip(selectedClip);
  const root=$('#inspector');
  if(!c||!root||c.track!=='video'||!c.mediaId)return;
  const m=getMedia(c.mediaId);
  if(!m?.dbId)return;
  const section=document.createElement('div');
  section.className='inspector-section timeline-continuity-section';
  section.innerHTML=`
    <div class="inspector-section-title">CONTINUITÉ DE VOISINAGE</div>
    <div class="hint">Compare ce plan à son précédent et à son suivant dans la STORYLINE réelle. Aucun remplacement n’est appliqué automatiquement.</div>
    <div class="ins-actions">
      <button class="btn primary" onclick="openTimelineContinuity('${c.id}')">Analyser voisins</button>
    </div>`;
  root.appendChild(section);
}

const _v0225RenderInspector=renderInspector;
renderInspector=function(){
  _v0225RenderInspector();
  appendTimelineContinuitySection();
};

function continuityClipCard(label,clip){
  if(!clip){
    return `<div class="card continuity-neighbor empty"><h3>${label}</h3><p>Pas de plan.</p></div>`;
  }
  return `<div class="card continuity-neighbor">
    <h3>${label} · ${clip.label||clip.clip_id}</h3>
    <p>${(+clip.start||0).toFixed(2)} s · ${(+clip.duration||0).toFixed(2)} s</p>
    <div class="suggestion-reasons">${(clip.tags||[]).length?(clip.tags||[]).map(tag=>`<span>${tag}</span>`).join(''):'<span>Aucun tag structuré</span>'}</div>
  </div>`;
}

function continuityFindingMarkup(finding){
  const cls=finding.severity==='WARNING'?'warn':'hint';
  return `<div class="${cls} continuity-finding">
    <b>${finding.kind} · ${finding.facet||''}</b>
    <div>${finding.message}</div>
  </div>`;
}

async function openTimelineContinuity(clipId=null,candidateMediaDbId=null){
  const c=getClip(clipId||selectedClip);
  if(!c||c.track!=='video'||!c.mediaId){
    toast('Sélectionne un plan vidéo de la STORYLINE',true);
    return;
  }
  if(!backendConnected){
    toast('Backend local requis',true);
    return;
  }
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;
  $('#editorialDrawerTitle').textContent='Continuité de voisinage';
  body.innerHTML='<div class="editorial-loading">Analyse du contexte réel de montage…</div>';
  try{
    const qs=new URLSearchParams({
      edit_name:activeEditName,
      clip_id:c.id,
    });
    if(candidateMediaDbId!=null)qs.set('candidate_media_id',String(candidateMediaDbId));
    const result=await api('/api/vision/timeline-continuity?'+qs.toString());
    timelineContinuityLastResult=result;
    renderTimelineContinuity(result,c);
  }catch(err){
    body.innerHTML=`<div class="warn">Analyse de continuité indisponible : ${err.message}</div>`;
  }
}

function renderTimelineContinuity(result,c){
  const body=$('#editorialDrawerBody');
  const selectedCandidate=result.candidate_media_id!=null?String(result.candidate_media_id):'';
  const options=media.filter(m=>m.dbId).map(m=>`<option value="${m.dbId}" ${String(m.dbId)===selectedCandidate?'selected':''}>${m.label}</option>`).join('');
  const warnings=(result.findings||[]).filter(x=>x.severity==='WARNING');
  const infos=(result.findings||[]).filter(x=>x.severity!=='WARNING');
  const canonConflicts=(result.canon_assessments||[]).filter(x=>['CONFLICT','HARD_LOCK'].includes(x.status));
  const targetLabel=result.target?.label||c.label;
  const candidateNote=result.mode==='CANDIDATE'
    ?`Simulation uniquement · ${targetLabel} testé à la place de ${c.label}`
    :`Plan actuellement monté · ${targetLabel}`;

  body.innerHTML=`
    <div class="selector-policy">
      <span>CONTEXTE STORYLINE</span>
      <b>${continuityStatusLabel(result.status)}</b>
      <small>${candidateNote}</small>
    </div>
    <div class="continuity-triptych">
      ${continuityClipCard('PRÉCÉDENT',result.previous)}
      ${continuityClipCard(result.mode==='CANDIDATE'?'CANDIDAT':'PLAN',result.target)}
      ${continuityClipCard('SUIVANT',result.next)}
    </div>
    <div class="form-grid">
      <div class="row full">
        <label>Tester un autre rush à cette position</label>
        <select id="continuityCandidateMedia"><option value="">Plan actuellement monté</option>${options}</select>
      </div>
    </div>
    <div class="suggestion-actions">
      <button class="btn primary" onclick="runTimelineContinuityCandidate('${c.id}')">Tester ce candidat</button>
      ${result.mode==='CANDIDATE'?'<button class="btn" onclick="openTimelineContinuity(\''+c.id+'\')">Revenir au plan monté</button>':''}
    </div>
    <div class="hint">Le test candidat ne modifie ni la timeline, ni le Source IN/OUT, ni les tags. Il simule uniquement le média à la position du clip sélectionné.</div>
    <div class="inspector-section-title" style="margin-top:14px">SIGNAUX DE CONTINUITÉ</div>
    ${warnings.length?warnings.map(continuityFindingMarkup).join(''):'<div class="okbox">Aucune rupture explicite détectée à partir des tags structurés disponibles.</div>'}
    ${infos.length?'<div class="continuity-info-list">'+infos.map(continuityFindingMarkup).join('')+'</div>':''}
    ${canonConflicts.length?`<div class="inspector-section-title" style="margin-top:14px">CANON</div>${canonConflicts.map(a=>canonAssessmentMarkup(a)).join('')}`:''}
    <div class="vision-evidence">Voisins analysés : ${result.summary?.neighbor_count||0} · alertes : ${result.summary?.warning_count||0} · continuités explicites : ${result.summary?.continuity_count||0}</div>
  `;
}

function runTimelineContinuityCandidate(clipId){
  const value=$('#continuityCandidateMedia')?.value||'';
  openTimelineContinuity(clipId,value?+value:null);
}

if(typeof commands!=='undefined'&&!commands.some(c=>c.label==='Vision · Continuité voisins')){
  commands.splice(
    Math.min(commands.length,97),
    0,
    {
      label:'Vision · Continuité voisins',
      hint:'',
      keywords:'timeline previous next voisin continuity rupture candidate',
      run:()=>openTimelineContinuity(),
    }
  );
}
