async function analyzeMediaCatalog(){
  if(!backendConnected){toast('Backend local requis pour analyser les rushes',true);return}
  const btn=$('#analyzeMediaBtn');
  if(btn){btn.disabled=true;btn.textContent='Analyse…'}
  try{
    const r=await api('/api/media/analyze',{method:'POST',body:JSON.stringify({filmstrips:true})});
    toast(`Analyse média · ${r.ready}/${r.total} prêt(s)${r.failed?.length?` · ${r.failed.length} échec(s)`:''}`);
    await hydrateBackend();
  }catch(err){toast('Analyse média impossible : '+err.message,true)}
  finally{if(btn){btn.disabled=false;btn.textContent='Analyser'}}
}

async function analyzeSelectedMedia(){
  const m=getMedia(selectedMedia);
  if(!m?.dbId){toast('Sélectionne un rush catalogué',true);return}
  try{
    toast(`Analyse de ${m.label}…`);
    await api(`/api/media/${m.dbId}/analyze`,{method:'POST',body:JSON.stringify({filmstrip:true})});
    const dbId=m.dbId;
    await hydrateBackend();
    const restored=media.find(x=>x.dbId===dbId);
    if(restored){selectedMedia=restored.id;selectedClip=null;renderMedia();renderMediaInspector()}
    toast(`${m.label} analysé`);
  }catch(err){toast('Analyse du rush impossible : '+err.message,true)}
}

function mediaTechnicalSummary(m){
  const a=m?.analysis,tech=a?.technical||{};
  if(!a)return '<div class="editorial-empty">Rush non analysé.</div>';
  if(a.status!=='READY')return `<div class="editorial-empty">Analyse : ${a.status}</div>`;
  const bits=[];
  if(tech.width&&tech.height)bits.push(`${tech.width}×${tech.height}`);
  if(tech.fps)bits.push(`${(+tech.fps).toFixed(2)} fps`);
  if(tech.video_codec)bits.push(String(tech.video_codec).toUpperCase());
  if(tech.pixel_format)bits.push(tech.pixel_format);
  return `<div class="media-tech-line">${bits.map(x=>`<span>${x}</span>`).join('')}</div><div class="hint">Empreinte visuelle locale · ${(a.visual_signature||[]).length} échantillon(s)</div>`;
}

function appendMediaIntelligenceSection(){
  const m=getMedia(selectedMedia),root=$('#inspector');if(!m||!root)return;
  const section=document.createElement('div');section.className='inspector-section media-intelligence-section';
  section.innerHTML=`<div class="inspector-section-title">MEDIA INTELLIGENCE</div>${mediaTechnicalSummary(m)}<div class="ins-actions"><button class="btn" onclick="analyzeSelectedMedia()">${m.analysis?.status==='READY'?'Réanalyser':'Analyser ce rush'}</button><button class="btn primary" onclick="openSimilarTakes(${m.dbId||'null'})">Prises proches</button></div><div class="hint">Analyse locale via ffmpeg/ffprobe. Aucun média n’est envoyé vers un service externe.</div>`;
  root.appendChild(section);
}

const _v016RenderMediaInspectorIntelligence=renderMediaInspector;
renderMediaInspector=function(){_v016RenderMediaInspectorIntelligence();appendMediaIntelligenceSection()}

async function openSimilarTakes(dbId=null){
  const m=dbId?media.find(x=>x.dbId===+dbId):getMedia(selectedMedia);
  if(!m?.dbId){toast('Sélectionne un rush analysable',true);return}
  if(!backendConnected){toast('Backend local requis',true);return}
  const drawer=$('#editorialDrawer'),body=$('#editorialDrawerBody');
  drawer.hidden=false;$('#editorialDrawerTitle').textContent=`Prises proches · ${m.label}`;
  body.innerHTML='<div class="editorial-loading">Comparaison locale des prises…</div>';
  try{
    const r=await api(`/api/media/${m.dbId}/similar`);
    const rows=(r.similar||[]).slice(0,8);
    if(!rows.length){body.innerHTML='<div class="editorial-empty large">Aucune autre prise vidéo cataloguée.</div>';return}
    body.innerHTML=`<div class="selector-policy"><span>PROXIMITÉ</span><b>${m.label}</b><small>Indice local : empreinte visuelle si disponible, sinon nom/durée.</small></div>`+
      rows.map((row,i)=>{
        const candidate=media.find(x=>x.dbId===+row.media_id);
        const pct=Math.round((+row.similarity||0)*100);
        const visual=row.visual_similarity==null?'':` · visuel ${Math.round(row.visual_similarity*100)} %`;
        return `<article class="suggestion-card"><div class="suggestion-rank">${String(i+1).padStart(2,'0')}</div><div class="suggestion-main"><div class="suggestion-head"><b>${candidate?.label||('Média '+row.media_id)}</b><span>${pct} %</span></div><div class="suggestion-range">similarité globale${visual}</div><div class="suggestion-reasons">${(row.evidence||[]).map(x=>`<span>${x}</span>`).join('')}</div><div class="suggestion-actions"><button class="btn" onclick="previewSimilarTake(${row.media_id})">Prévisualiser</button></div></div></article>`;
      }).join('');
  }catch(err){body.innerHTML=`<div class="warn">Comparaison indisponible : ${err.message}</div>`}
}
function previewSimilarTake(dbId){
  const m=media.find(x=>x.dbId===+dbId);if(!m)return;
  selectedMedia=m.id;selectedClip=null;showSourceMedia(m,m.in||0,false);renderMedia();renderMediaInspector();
}

const _v016RenderSourceSuggestions=renderSourceSuggestions;
renderSourceSuggestions=function(result,reference){
  _v016RenderSourceSuggestions(result,reference);
  $$('.suggestion-card').forEach((card,i)=>{
    const s=(result.suggestions||[])[i];if(!s)return;
    if(s.visual_similarity!=null){
      const target=card.querySelector('.suggestion-range');
      if(target)target.insertAdjacentHTML('beforeend',` · proximité visuelle ${Math.round(s.visual_similarity*100)} %`);
    }
  });
}
