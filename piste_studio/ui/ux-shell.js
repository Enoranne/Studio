function setWorkspace(name){activeWorkspace=name;document.body.classList.remove('workspace-assemble','workspace-edit','workspace-review');document.body.classList.add(`workspace-${name}`);$$('.workspace-switch button').forEach(b=>b.classList.toggle('active',b.dataset.workspace===name));if(name==='assemble'){document.body.classList.remove('browser-collapsed');document.body.classList.add('index-collapsed')}else if(name==='edit'){document.body.classList.remove('browser-collapsed','inspector-collapsed','index-collapsed')}else{document.body.classList.remove('index-collapsed')}requestAnimationFrame(()=>{renderTracks();drawAllWaveforms()})}
function toggleBrowser(){document.body.classList.toggle('browser-collapsed');requestAnimationFrame(renderTracks)}
function toggleInspector(){document.body.classList.toggle('inspector-collapsed');requestAnimationFrame(renderTracks)}
function toggleIndex(){document.body.classList.toggle('index-collapsed');requestAnimationFrame(renderTracks)}

function updateLocalStatus(){const nv=media.filter(m=>m.url).length,na=audioAssets.filter(a=>a.url).length,e=$('#localStatus');if(!e)return;e.textContent=`${nv+na}/${media.length+audioAssets.length} local`;e.classList.toggle('warn',nv<media.length||na<audioAssets.length)}

$$('.workspace-switch button').forEach(b=>b.onclick=()=>setWorkspace(b.dataset.workspace));
$$('.viewer-tab').forEach(b=>b.onclick=()=>setViewerMode(b.dataset.monitor));
$$('.filter-chip').forEach(b=>b.onclick=()=>{browserFilter=b.dataset.filter;renderMedia()});
$$('.index-tabs button').forEach(b=>b.onclick=()=>{indexMode=b.dataset.index;renderIndex()});
$('#toggleBrowserBtn').onclick=toggleBrowser;$('#toggleInspectorBtn').onclick=toggleInspector;$('#toggleIndexBtn').onclick=toggleIndex;

document.addEventListener('keydown',e=>{if(e.target.matches('input,select,textarea'))return;const k=e.key.toLowerCase();if(k==='1')setWorkspace('assemble');if(k==='2')setWorkspace('edit');if(k==='3')setWorkspace('review');if(k==='b')toggleBrowser();if(k==='i')toggleInspector();if(k==='f')markRange('favorite');if(k==='x')markRange('reject');if(k==='p')setViewerMode(viewerMode==='program'?'source':'program')});

const _timelineTogglePlay=togglePlay,_timelineStep=step;
togglePlay=function(){
  if(viewerMode==='program')return _timelineTogglePlay();
  const m=getMedia(selectedMedia),v=$('#video');if(!m?.url)return toast('Associe le rush local pour lire la source',true);
  const out=m.out??m.duration;if(v.currentTime>=out-.02||v.currentTime<(m.in||0))v.currentTime=m.in||0;
  if(v.paused){v.play().then(()=>{$('#playBtn').textContent='❚❚'}).catch(()=>toast('Lecture bloquée par le navigateur',true))}else{v.pause();$('#playBtn').textContent='▶'}
}
step=function(d){
  if(viewerMode==='program')return _timelineStep(d);
  const m=getMedia(selectedMedia),v=$('#video');if(!m)return;v.pause();$('#playBtn').textContent='▶';const lo=m.in||0,hi=m.out??m.duration;const t=Math.max(lo,Math.min(hi-.01,(v.currentTime||lo)+d));try{v.currentTime=t}catch(_){}$('#timecode').textContent=fmt(t);$('#viewerHud').textContent=`SOURCE · ${fmt(t)}`
}
$('#video').addEventListener('timeupdate',()=>{if(viewerMode!=='source')return;const m=getMedia(selectedMedia);if(!m)return;const out=m.out??m.duration;if($('#video').currentTime>=out){$('#video').pause();$('#video').currentTime=Math.max(m.in||0,out-.01);$('#playBtn').textContent='▶'}$('#timecode').textContent=fmt($('#video').currentTime||0);$('#viewerHud').textContent=`SOURCE · ${fmt($('#video').currentTime||0)}`});
$('#video').addEventListener('pause',()=>{if(viewerMode==='source')$('#playBtn').textContent='▶'});
