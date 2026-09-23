let viewerMode=PisteState.get('viewerMode'),browserFilter=PisteState.get('browserFilter'),indexMode=PisteState.get('indexMode'),activeWorkspace=PisteState.get('workspace');

function setViewerMode(mode,{silent=false}={}){
  viewerMode=PisteState.set('viewerMode',mode==='source'?'source':'program');
  document.body.classList.toggle('source-mode',viewerMode==='source');
  $$('.viewer-tab').forEach(b=>b.classList.toggle('active',b.dataset.monitor===viewerMode));
  $('#monitorMode').textContent=viewerMode==='source'?'Source sélectionnée':'Timeline';
  if(viewerMode==='program'){
    syncProgramMonitor(false);syncTitle();syncAudio(false);
  }else{
    $('#viewerTitle').classList.remove('show');
    const m=getMedia(selectedMedia);if(m)showSourceMedia(m,m.in||0,false);
  }
  if(!silent)toast(viewerMode==='source'?'Viewer SOURCE':'Viewer PROGRAM');
}

function showSourceMedia(m,time=0,play=false){
  pausePlayback();viewerMode=PisteState.set('viewerMode','source');document.body.classList.add('source-mode');
  $$('.viewer-tab').forEach(b=>b.classList.toggle('active',b.dataset.monitor==='source'));
  $('#monitorMode').textContent='Source sélectionnée';
  $('#viewerSource').textContent=`SOURCE · ${m.file}`;
  $('#sourceInBadge').textContent=`IN ${fmt(m.in||0)}`;$('#sourceOutBadge').textContent=`OUT ${fmt(m.out||m.duration)}`;
  const v=$('#video');
  if(!m.url){currentMonitorMedia=null;v.pause();setPlaceholder(m.label,`Rush local non associé.<br><small>${m.file}</small>`);return}
  const target=Math.max(0,Math.min(m.duration-.01,time));
  const same=currentMonitorMedia===`source:${m.id}`;
  currentMonitorMedia=`source:${m.id}`;
  if(!same){v.pause();v.src=m.url;v.dataset.mediaId=m.id;v.onloadedmetadata=()=>{try{v.currentTime=Math.min(target,v.duration||target)}catch(_){}$('#viewer').classList.add('has-video');if(play)v.play().catch(()=>{})};v.load()}
  else{try{v.currentTime=target}catch(_){}$('#viewer').classList.add('has-video');if(play)v.play().catch(()=>{})}
}

previewMedia=function(id){const m=getMedia(id);if(!m)return;selectedMedia=id;selectedClip=null;showSourceMedia(m,m.in||0,false);renderMedia();renderMediaInspector()}

function markRange(kind){
  if(viewerMode!=='source'){toast('Passe en SOURCE pour noter un rush',true);return}
  const m=getMedia(selectedMedia);if(!m)return;
  m.favorite=kind==='favorite';m.rejected=kind==='reject';
  if(kind==='favorite')m.rejected=false;if(kind==='reject')m.favorite=false;
  renderMedia();renderMediaInspector();renderIndex();toast(kind==='favorite'?'Plage marquée FAVORITE':'Plage marquée REJECT')
}

function mediaPassesFilter(m){if(browserFilter==='favorite')return !!m.favorite;if(browserFilter==='canon')return !!m.canon;if(browserFilter==='safe')return !!m.safe;return true}

renderMedia=function(){
  const q=($('#mediaSearch')?.value||'').toLowerCase().trim(),root=$('#mediaList');if(!root)return;root.innerHTML='';
  $$('.libtab').forEach(b=>b.classList.toggle('active',b.dataset.lib===libraryMode));
  $$('.filter-chip').forEach(b=>b.classList.toggle('active',b.dataset.filter===browserFilter));
  if(libraryMode==='video'){
    const list=media.filter(m=>mediaPassesFilter(m)&&(m.file+' '+m.label+' '+(m.tags||[]).join(' ')).toLowerCase().includes(q));$('#mediaCount').textContent=list.length;
    list.forEach(m=>{
      const e=document.createElement('article');e.className=`media-row${selectedMedia===m.id?' selected':''}${m.favorite?' favorite':''}${m.rejected?' rejected':''}`;e.draggable=true;
      const rangeL=Math.max(0,Math.min(100,(m.in||0)/m.duration*100)),rangeW=Math.max(2,Math.min(100-rangeL,((m.out??m.duration)-(m.in||0))/m.duration*100));
      e.innerHTML=`<div class="media-row-head"><b>${m.label}</b><small>${m.duration.toFixed(1)}s</small></div><div class="filmstrip" data-filmstrip="${m.id}">${m.url?`<video src="${m.url}" muted preload="metadata"></video>`:''}<div class="filmstrip-cells"><i></i><i></i><i></i><i></i><i></i></div><span class="favorite-band" style="left:${rangeL}%;width:${rangeW}%"></span><span class="reject-band" style="left:${rangeL}%;width:${rangeW}%"></span><span class="range-band" style="left:${rangeL}%;width:${rangeW}%"></span></div><div class="media-meta"><div class="tag-row">${m.canon?'<span class="badge canon">CANON</span>':''}${m.safe?'<span class="badge safe">SAFE</span>':''}${m.favorite?'<span class="badge favorite">★ FAVORITE</span>':''}${m.url?'<span class="badge local">LOCAL</span>':''}</div><span class="badge">S${m.spoiler||0}</span></div>`;
      e.ondragstart=ev=>{ev.dataTransfer.setData('text/piste-media',m.id);ev.dataTransfer.effectAllowed='copy'};
      e.onclick=()=>previewMedia(m.id);
      const strip=e.querySelector('.filmstrip');
      strip.addEventListener('pointermove',ev=>{if(!m.url)return;const box=strip.getBoundingClientRect(),ratio=Math.max(0,Math.min(1,(ev.clientX-box.left)/box.width)),t=ratio*m.duration;const mini=strip.querySelector('video');try{mini.currentTime=t}catch(_){}if(selectedMedia===m.id)showSourceMedia(m,t,false)});
      root.appendChild(e)
    })
  }else{
    const list=audioAssets.filter(a=>(a.file+' '+a.label+' '+(a.tags||[]).join(' ')).toLowerCase().includes(q));$('#mediaCount').textContent=list.length;
    list.forEach(a=>{const e=document.createElement('article');e.className=`media-row${selectedAudio===a.id?' selected':''}`;e.draggable=true;e.innerHTML=`<div class="media-row-head"><b>${a.label}</b><small>${a.duration.toFixed(1)}s</small></div><div class="asset-wave"><canvas data-asset-wave="${a.id}"></canvas></div><div class="media-meta"><div class="tag-row"><span class="badge">${a.role.toUpperCase()}</span>${a.url?'<span class="badge local">LOCAL</span>':''}</div><span class="badge">AUDIO</span></div>`;e.ondragstart=ev=>{ev.dataTransfer.setData('text/piste-audio',a.id);ev.dataTransfer.effectAllowed='copy'};e.onclick=()=>{selectedAudio=a.id;selectedClip=null;renderMedia();renderAudioInspector()};root.appendChild(e)});requestAnimationFrame(drawAllWaveforms)
  }updateLocalStatus()
}

renderMediaInspector=function(){
  const m=getMedia(selectedMedia);if(!m)return;$('#selectionKind').textContent='SOURCE';
  $('#inspector').innerHTML=`<h3>${m.label}</h3><p>${m.note||m.file}</p><div class="inspector-section"><div class="inspector-section-title">RANGE</div><div class="form-grid"><div class="row"><label>Source IN</label><input id="mi" type="number" value="${m.in||0}" min="0" max="${m.duration}" step="0.1"></div><div class="row"><label>Source OUT</label><input id="mo" type="number" value="${m.out??m.duration}" min="0.1" max="${m.duration}" step="0.1"></div></div><div class="ins-actions"><button class="btn primary" onclick="addMedia()">Ajouter à la Storyline</button><button class="btn" onclick="markRange('favorite')">★ Favori</button><button class="btn" onclick="markRange('reject')">Rejeter</button></div></div><div class="inspector-section"><div class="inspector-section-title">METADATA</div><div class="tag-row">${m.canon?'<span class="badge canon">CANON</span>':''}${m.safe?'<span class="badge safe">TRAILER-SAFE</span>':''}<span class="badge">SPOILER ${m.spoiler||0}</span>${m.url?'<span class="badge local">LOCAL</span>':''}</div><div class="hint">${(m.tags||[]).join(' · ')||'Aucun tag'}</div><div class="ins-actions"><button class="btn" onclick="bindSelectedMedia()">${m.url?'Remplacer le fichier':'Associer le fichier'}</button></div></div>`;
  $('#mi').onchange=()=>{if(updateMediaRange()){renderMedia();showSourceMedia(m,m.in,false)}};$('#mo').onchange=()=>{if(updateMediaRange())renderMedia()}
}

renderAudioInspector=function(){const a=getAudio(selectedAudio);if(!a)return;$('#selectionKind').textContent='AUDIO';$('#inspector').innerHTML=`<h3>${a.label}</h3><p>${a.note||a.file}</p><div class="inspector-section"><div class="inspector-section-title">SOURCE</div><div class="asset-wave" style="height:62px"><canvas data-asset-wave="${a.id}"></canvas></div><div class="ins-actions"><button class="btn primary" onclick="addAudioAssetToTimeline()">Ajouter à ${a.role.toUpperCase()}</button><button class="btn" onclick="previewAudioAsset()">▶ Écouter</button></div></div><div class="inspector-section"><div class="inspector-section-title">ROLE</div><div class="tag-row"><span class="badge">${a.role.toUpperCase()}</span>${a.url?'<span class="badge local">LOCAL</span>':''}</div><div class="ins-actions"><button class="btn" onclick="bindSelectedAudio()">${a.url?'Remplacer le fichier':'Associer le fichier'}</button></div></div>`;requestAnimationFrame(drawAllWaveforms)}
