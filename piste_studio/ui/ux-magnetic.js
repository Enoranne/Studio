let storylineStart=null,storylineMode='free',localUndoStack=[];

function getStorylineStart(){
  if(Number.isFinite(storylineStart))return storylineStart;
  const story=storyClipsSorted();
  storylineStart=story.length?story[0].start:Math.max(0,HARD_END||0);
  return storylineStart;
}
function setStorylineStateFromDoc(doc){
  const v=doc?.storyline?.start,story=storyClipsSorted();
  storylineStart=Number.isFinite(+v)?+v:(story.length?story[0].start:Math.max(0,HARD_END||0));
  if(doc?.storyline?.mode){storylineMode=doc.storyline.mode}
  else{
    let cursor=storylineStart,contiguous=true;
    for(const c of story){if(Math.abs(c.start-cursor)>1e-4){contiguous=false;break}cursor+=c.duration}
    storylineMode=contiguous?'magnetic':'free'
  }
}
function storyClipsSorted(list=clips){return list.filter(c=>c.track==='video').slice().sort((a,b)=>a.start-b.start||String(a.id).localeCompare(String(b.id)))}
function storyParentAt(time,list=clips){
  const story=storyClipsSorted(list);if(!story.length)return null;
  const inside=story.find(c=>time>=c.start&&time<c.start+c.duration);if(inside)return inside;
  const previous=story.filter(c=>c.start<=time).pop();return previous||story[0]
}
function connectChild(c,parentId=null){
  if(!c||c.track==='video')return;
  const parent=parentId?getClip(parentId):storyParentAt(c.start);
  if(!parent){delete c.parentClipId;delete c.anchorOffset;delete c.connectionMode;return}
  c.parentClipId=parent.id;
  c.anchorOffset=+(c.start-parent.start).toFixed(6);
  c.connectionPointOffset=+Math.min(Math.max(c.start-parent.start,0),parent.duration).toFixed(6);
  c.connectionMode='follow'
}
function detachChild(c){if(!c)return;delete c.parentClipId;delete c.anchorOffset;delete c.connectionPointOffset;delete c.connectionMode}
async function changeConnection(parentId){
  const c=getClip(selectedClip);if(!c||c.track==='video')return;
  const before=cloneClips();
  if(backendConnected){
    const ok=await commitBackendMagneticOperation(
      parentId?'attach':'detach',
      parentId?{child_id:c.id,parent_id:parentId}:{child_id:c.id},
      parentId?'Connexion STORY modifiée':'Élément détaché',
      before,
    );
    if(!ok)renderInspector();
    return
  }
  const candidate=cloneClips(),child=candidate.find(x=>x.id===c.id);
  if(!child)return;
  if(!parentId)detachChild(child);
  else{
    const parent=candidate.find(x=>x.id===parentId&&x.track==='video');
    if(!parent){toast('Plan parent introuvable',true);renderInspector();return}
    child.parentClipId=parent.id;
    child.anchorOffset=+(child.start-parent.start).toFixed(6);
    child.connectionPointOffset=+Math.min(Math.max(child.start-parent.start,0),parent.duration).toFixed(6);
    child.connectionMode='follow';
  }
  const ok=await commitMagneticCandidate(
    candidate,
    parentId?'Connexion STORY modifiée':'Élément détaché',
    before,
  );
  if(!ok)renderInspector()
}

function connectionTargetAt(time,list=clips){
  const story=storyClipsSorted(list);
  if(!story.length)return null;
  const first=story[0],last=story[story.length-1],end=last.start+last.duration;
  if(time<first.start-1e-6||time>end+1e-6)return null;
  return story.find((c,i)=>time>=c.start-1e-6&&(time<c.start+c.duration-1e-6||i===story.length-1&&time<=c.start+c.duration+1e-6))||null
}
function setConnectionPointOnCandidate(candidate,childId,targetTime){
  const child=candidate.find(c=>c.id===childId);
  if(!child||child.track==='video')throw new Error('Élément connecté introuvable');
  const parent=connectionTargetAt(targetTime,candidate);
  if(!parent)throw new Error('Le point doit rester sur la Storyline');
  const point=Math.min(Math.max(targetTime-parent.start,0),parent.duration);
  child.parentClipId=parent.id;
  child.anchorOffset=+(child.start-parent.start).toFixed(6);
  child.connectionPointOffset=+point.toFixed(6);
  child.connectionMode='follow';
  return child
}

function cloneClips(list=clips){return list.map(c=>({...c,volumeEnvelope:Array.isArray(c.volumeEnvelope)?c.volumeEnvelope.map(p=>({...p})):c.volumeEnvelope}))}
function reflowCandidate(candidate,orderIds=null){
  const story=storyClipsSorted(candidate),byId=new Map(candidate.map(c=>[c.id,c]));
  const ordered=orderIds?orderIds.map(id=>byId.get(id)).filter(Boolean):story;
  const expected=new Set(story.map(c=>c.id));if(ordered.length!==story.length||ordered.some(c=>!expected.has(c.id)))throw new Error('Ordre STORY invalide');
  let cursor=getStorylineStart();
  ordered.forEach(c=>{c.start=+cursor.toFixed(6);cursor+=c.duration});
  const parents=new Map(ordered.map(c=>[c.id,c]));
  candidate.forEach(c=>{
    if(!c.parentClipId)return;
    const p=parents.get(c.parentClipId);
    if(!p)throw new Error(`Parent absent pour ${c.label}`);
    if(c.anchorOffset==null)c.anchorOffset=+(c.start-p.start).toFixed(6);
    if(c.connectionPointOffset==null)c.connectionPointOffset=+Math.min(Math.max(+c.anchorOffset||0,0),p.duration).toFixed(6);
    else c.connectionPointOffset=+Math.min(Math.max(+c.connectionPointOffset||0,0),p.duration).toFixed(6);
    c.connectionMode='follow';
    c.start=+(p.start+(+c.anchorOffset||0)).toFixed(6)
  });
  return candidate
}
function validateCandidate(candidate,original=clips){
  const byTrack={};const originalById=new Map(original.map(c=>[c.id,c]));
  for(const c of candidate){
    if(c.start<0||c.duration<MIN_CLIP||c.start+c.duration>DURATION+1e-6)return `${c.label} sort de la timeline`;
    const tr=getTrack(c.track);const old=originalById.get(c.id);
    if(tr?.locked&&old&&(Math.abs(old.start-c.start)>1e-6||Math.abs(old.duration-c.duration)>1e-6))return `Piste ${tr.name} verrouillée`;
    if(c.mediaId){const m=getMedia(c.mediaId);if(m&&((c.sourceStart||0)<0||(c.sourceStart||0)+c.duration>m.duration+1e-6))return `${c.label} dépasse sa source vidéo`}
    if(c.audioId){const a=getAudio(c.audioId);if(a&&((c.sourceStart||0)<0||(c.sourceStart||0)+c.duration>a.duration+1e-6))return `${c.label} dépasse sa source audio`}
    if(c.parentClipId){
      const p=candidate.find(x=>x.id===c.parentClipId&&x.track==='video');
      if(!p)return `Parent manquant pour ${c.label}`;
      if(Math.abs(c.start-(p.start+(+c.anchorOffset||0)))>1e-4)return `Connexion incohérente pour ${c.label}`;
      const point=c.connectionPointOffset==null?Math.min(Math.max(+c.anchorOffset||0,0),p.duration):+c.connectionPointOffset;
      if(point<0||point>p.duration+1e-6)return `Point de connexion hors du parent pour ${c.label}`;
    }
    (byTrack[c.track]??=[]).push(c)
  }
  for(const arr of Object.values(byTrack)){arr.sort((a,b)=>a.start-b.start);for(let i=1;i<arr.length;i++){if(arr[i].start<arr[i-1].start+arr[i-1].duration-1e-6&&!(typeof audioCrossfadeAllowed==='function'&&audioCrossfadeAllowed(arr[i-1],arr[i])))return `Collision : ${arr[i-1].label} / ${arr[i].label}`}}
  const story=storyClipsSorted(candidate);let cursor=getStorylineStart();for(const c of story){if(Math.abs(c.start-cursor)>1e-4)return 'Storyline non contiguë';cursor+=c.duration}
  return null
}
function backendClipPayload(c){
  const n={...c},m=c.mediaId&&getMedia(c.mediaId),a=c.audioId&&getAudio(c.audioId);
  if(m?.dbId)n.mediaDbId=m.dbId;
  if(a?.dbId)n.audioDbId=a.dbId;
  delete n.mediaId;delete n.audioId;
  return n
}
function backendTimelinePayload(list=clips,mode=storylineMode){
  return {edit_name:activeEditName,duration_seconds:DURATION,storyline:{mode,start:getStorylineStart()},tracks,clips:list.map(backendClipPayload)}
}
async function validateMagneticWithBackend(before,candidate){
  if(!backendConnected)return true;
  try{await api('/api/storyline/validate',{method:'POST',body:JSON.stringify({before:backendTimelinePayload(before,storylineMode),after:backendTimelinePayload(candidate,'magnetic')})});return true}
  catch(err){toast('Opération magnétique bloquée : '+err.message,true);return false}
}
async function checkpointBeforeMagnetic(before,reason){
  if(backendConnected){
    try{
      await api('/api/history/checkpoint',{method:'POST',body:JSON.stringify({edit_name:activeEditName,reason,timeline:backendTimelinePayload(before,storylineMode)})});
      return true
    }catch(err){toast('Checkpoint impossible : '+err.message,true);return false}
  }
  localUndoStack.push({clips:cloneClips(before),storylineMode,storylineStart:getStorylineStart(),reason});
  if(localUndoStack.length>50)localUndoStack.shift();
  return true
}
async function commitBackendMagneticOperation(operation,args,message,before=clips){
  if(!backendConnected)return null;
  try{
    const response=await api('/api/storyline/operate',{
      method:'POST',
      body:JSON.stringify({
        timeline:backendTimelinePayload(before,storylineMode),
        operation,
        args,
      }),
    });
    if(!(await checkpointBeforeMagnetic(before,message)))return false;
    const previousSelection=selectedClip;
    hydrateTimeline(response.timeline);
    storylineMode='magnetic';
    selectedClip=previousSelection&&getClip(previousSelection)?previousSelection:(clips[0]?.id||null);
    renderTracks();renderMedia();setPlayhead(Math.min(playhead,DURATION));toast(message);
    return true
  }catch(err){
    toast('Opération magnétique bloquée : '+err.message,true);
    return false
  }
}
async function commitMagneticCandidate(candidate,message,before=clips){
  const err=validateCandidate(candidate,before);if(err){toast(err,true);return false}
  if(!(await validateMagneticWithBackend(before,candidate)))return false;
  if(!(await checkpointBeforeMagnetic(before,message)))return false;
  storylineMode='magnetic';clips=candidate;selectedClip=selectedClip&&getClip(selectedClip)?selectedClip:(clips[0]?.id||null);renderTracks();renderMedia();setPlayhead(Math.min(playhead,DURATION));toast(message);return true
}
async function undoLastEdit(){
  pausePlayback();
  if(backendConnected){
    try{
      const r=await api('/api/history/undo',{method:'POST',body:JSON.stringify({edit_name:activeEditName})});
      hydrateTimeline(r.timeline);
      renderTracks();renderMedia();setPlayhead(Math.min(playhead,DURATION));
      toast('Undo · '+(r.restored?.reason||'checkpoint restauré'));
      return true
    }catch(err){toast('Undo indisponible : '+err.message,true);return false}
  }
  const snap=localUndoStack.pop();
  if(!snap){toast('Aucun checkpoint local à restaurer',true);return false}
  clips=cloneClips(snap.clips);storylineMode=snap.storylineMode;storylineStart=snap.storylineStart;selectedClip=clips[0]?.id||null;
  renderTracks();renderMedia();setPlayhead(Math.min(playhead,DURATION));toast('Undo local · '+(snap.reason||'édition'));return true
}

const _legacyBeginClipInteraction=beginClipInteraction,_legacyPointerMove=onClipPointerMove,_legacyEndClipInteraction=endClipInteraction;
beginClipInteraction=function(ev,clipId,lane){
  const c=getClip(clipId);
  if(!c||c.track!=='video')return _legacyBeginClipInteraction(ev,clipId,lane);
  if(ev.button!==0)return;const track=getTrack(c.track);if(track?.locked){toast('Storyline verrouillée',true);return}
  ev.preventDefault();ev.stopPropagation();selectedClip=clipId;selectedMedia=c.mediaId||selectedMedia;
  const edge=ev.target.dataset.edge||'move';
  interaction={clipId,mode:edge,startX:ev.clientX,lane,start:{...c},element:ev.currentTarget,valid:true,magnetic:true,desiredTarget:c.start};
  interaction.element.classList.add('selected');document.addEventListener('pointermove',onClipPointerMove);document.addEventListener('pointerup',endClipInteraction,{once:true});renderInspector();$('#interactionReadout').textContent=edge==='move'?'Réorganisation magnétique…':edge==='left'?'Ripple trim IN…':'Ripple trim OUT…'
}
onClipPointerMove=function(ev){
  if(!interaction?.magnetic)return _legacyPointerMove(ev);
  const c=getClip(interaction.clipId),box=interaction.lane.getBoundingClientRect(),dt=(ev.clientX-interaction.startX)/box.width*DURATION,base=interaction.start;
  let preview={...base},err=null;
  if(interaction.mode==='move'){interaction.desiredTarget=snapTime(base.start+dt);preview.start=Math.max(0,interaction.desiredTarget)}
  else if(interaction.mode==='left'){const d=snapTime(dt);preview.sourceStart=(base.sourceStart||0)+d;preview.duration=base.duration-d;if(preview.sourceStart<0)err='Début de source dépassé';if(preview.duration<MIN_CLIP)err='Plan trop court'}
  else{preview.duration=snapTime(base.duration+dt);if(preview.duration<MIN_CLIP)err='Plan trop court';const m=getMedia(base.mediaId);if(m&&(base.sourceStart||0)+preview.duration>m.duration+1e-6)err='Fin de source dépassée'}
  interaction.preview=preview;interaction.error=err;interaction.valid=!err;
  const el=interaction.element;el.classList.toggle('invalid',!!err);if(interaction.mode==='move')el.style.left=`${preview.start/DURATION*100}%`;else el.style.width=`${Math.max(MIN_CLIP,preview.duration)/DURATION*100}%`;
  $('#interactionReadout').textContent=err||`${interaction.mode==='move'?'REORDER':'RIPPLE TRIM'} · ${preview.duration.toFixed(1)}s`
}
endClipInteraction=async function(){
  document.removeEventListener('pointermove',onClipPointerMove);if(!interaction)return;
  if(!interaction.magnetic){
    const id=interaction.clipId;_legacyEndClipInteraction();const c=getClip(id);if(c?.parentClipId){const p=getClip(c.parentClipId);if(p)c.anchorOffset=+(c.start-p.start).toFixed(6)}renderTracks();return
  }
  const state=interaction;interaction=null;$('#interactionReadout').textContent='Storyline magnétique · drag · ripple trim';
  if(!state.valid){toast(state.error||'Opération invalide',true);renderTracks();return}
  const before=cloneClips();
  if(backendConnected){
    if(state.mode==='move'){
      await commitBackendMagneticOperation(
        'move',
        {clip_id:state.clipId,target_time:Math.max(0,state.desiredTarget)},
        'Storyline réordonnée',
        before,
      );
    }else{
      const delta=state.mode==='left'
        ?(state.preview.sourceStart||0)-(state.start.sourceStart||0)
        :state.preview.duration-state.start.duration;
      await commitBackendMagneticOperation(
        'trim',
        {clip_id:state.clipId,edge:state.mode,delta,min_duration:MIN_CLIP},
        'Ripple trim appliqué',
        before,
      );
    }
    return
  }
  const candidate=cloneClips(),target=candidate.find(c=>c.id===state.clipId);if(!target)return;
  const story=storyClipsSorted(candidate);
  if(state.mode==='move'){
    const others=story.filter(c=>c.id!==target.id),targetTime=Math.max(0,state.desiredTarget),idx=others.filter(c=>targetTime>=c.start+c.duration/2).length,order=others.map(c=>c.id);order.splice(idx,0,target.id);reflowCandidate(candidate,order)
  }else if(state.mode==='left'){
    const delta=(state.preview.sourceStart||0)-(target.sourceStart||0);target.sourceStart=state.preview.sourceStart;target.duration=state.preview.duration;reflowCandidate(candidate)
  }else{target.duration=state.preview.duration;reflowCandidate(candidate)}
  await commitMagneticCandidate(candidate,state.mode==='move'?'Storyline réordonnée':'Ripple trim appliqué',before)
}

const _legacyApplyEdit=applyEdit;
applyEdit=function(){const id=selectedClip;_legacyApplyEdit();const c=getClip(id);if(c?.parentClipId){const p=getClip(c.parentClipId);if(p)c.anchorOffset=+(c.start-p.start).toFixed(6)}renderTracks()}

const _legacyAddTitle=addTitle,_legacyAddAudio=addAudio,_legacyAddAudioAsset=addAudioAssetToTimeline;
addTitle=function(){_legacyAddTitle();const c=getClip(selectedClip);if(c&&c.track!=='video')connectChild(c);renderTracks()}
addAudio=function(track){_legacyAddAudio(track);const c=getClip(selectedClip);if(c&&c.track!=='video')connectChild(c);renderTracks()}
addAudioAssetToTimeline=function(){_legacyAddAudioAsset();const c=getClip(selectedClip);if(c&&c.track!=='video')connectChild(c);renderTracks()}

const _legacyDropLibrary=dropLibraryOnLane;
dropLibraryOnLane=function(e,trackId,lane){
  if(trackId!=='video'){_legacyDropLibrary(e,trackId,lane);const c=getClip(selectedClip);if(c&&c.track!=='video')connectChild(c);renderTracks();return}
  e.preventDefault();lane.classList.remove('dragover');const mid=e.dataTransfer.getData('text/piste-media');if(!mid)return;
  const m=getMedia(mid);if(!m)return;const d=Math.max(MIN_CLIP,(m.out??m.duration)-(m.in||0)),start=snapTime(laneTimeFromEvent(e,lane));
  const before=cloneClips(),newClip={id:'v'+Date.now(),track:'video',mediaId:m.id,label:m.label,start,duration:d,sourceStart:m.in||0};
  selectedClip=newClip.id;selectedMedia=m.id;
  if(backendConnected){
    commitBackendMagneticOperation(
      'insert',
      {clip:backendClipPayload(newClip),target_time:start},
      `${m.label} inséré dans la Storyline`,
      before,
    );
    return
  }
  const candidate=cloneClips();candidate.push(newClip);
  const others=storyClipsSorted(candidate).filter(c=>c.id!==newClip.id),idx=others.filter(c=>start>=c.start+c.duration/2).length,order=others.map(c=>c.id);order.splice(idx,0,newClip.id);reflowCandidate(candidate,order);commitMagneticCandidate(candidate,`${m.label} inséré dans la Storyline`,before)
}

addMedia=function(){
  const m=getMedia(selectedMedia);if(!m)return;if(!updateMediaRange())return;
  const before=cloneClips(),story=storyClipsSorted(before),start=story.length?story[story.length-1].start+story[story.length-1].duration:getStorylineStart(),d=(m.out??m.duration)-(m.in||0);
  const c={id:'v'+Date.now(),track:'video',mediaId:m.id,label:m.label,start,duration:d,sourceStart:m.in||0};selectedClip=c.id;
  if(backendConnected){
    commitBackendMagneticOperation(
      'insert',
      {clip:backendClipPayload(c)},
      m.label+' ajouté à la Storyline',
      before,
    );
    return
  }
  const candidate=cloneClips();candidate.push(c);reflowCandidate(candidate);commitMagneticCandidate(candidate,m.label+' ajouté à la Storyline',before)
}

const _legacyRemoveClip=removeClip;
removeClip=function(){
  const c=getClip(selectedClip);if(!c||c.track!=='video')return _legacyRemoveClip();
  const before=cloneClips();
  if(backendConnected){
    commitBackendMagneticOperation(
      'remove',
      {clip_id:c.id},
      'Plan supprimé · Storyline refermée',
      before,
    );
    return
  }
  const candidate=cloneClips().filter(x=>x.id!==c.id);candidate.forEach(x=>{if(x.parentClipId===c.id)detachChild(x)});reflowCandidate(candidate);selectedClip=candidate[0]?.id||null;commitMagneticCandidate(candidate,'Plan supprimé · Storyline refermée',before)
}

const _v012RenderInspector=renderInspector;
renderInspector=function(){
  _v012RenderInspector();const c=getClip(selectedClip);if(!c||c.track==='video')return;
  const root=$('#inspector'),story=storyClipsSorted(),section=document.createElement('div');section.className='inspector-section connection-section';
  const parent=c.parentClipId?getClip(c.parentClipId):null;
  const point=parent?(c.connectionPointOffset==null?Math.min(Math.max(+c.anchorOffset||0,0),parent.duration):+c.connectionPointOffset):0;
  section.innerHTML=`<div class="inspector-section-title">CONNEXION STORY</div>
    <div class="row"><label>Plan parent</label><select id="parentClipSelect"><option value="">Détaché</option>${story.map(p=>`<option value="${p.id}" ${c.parentClipId===p.id?'selected':''}>${p.label} · ${fmt(p.start)}</option>`).join('')}</select></div>
    ${parent?`<div class="row" style="margin-top:7px"><label>Point sur parent (s)</label><input id="connectionPointInput" type="number" min="0" max="${parent.duration}" step="0.1" value="${point.toFixed(2)}"></div><div class="ins-actions"><button class="btn" type="button" onclick="applyConnectionPointFromInspector()">Appliquer le point</button></div>`:''}
    <div class="hint">${c.parentClipId?`Le clip reste à ${fmt(c.start)}. Il suit ${parent?.label||c.parentClipId} avec un offset temporel de ${(+c.anchorOffset||0).toFixed(1)} s ; son point graphique est à +${point.toFixed(1)} s sur le parent.`:'Position absolue : ne suivra aucun plan STORY.'}</div>`;
  root.insertBefore(section,root.lastElementChild);$('#parentClipSelect').onchange=e=>changeConnection(e.target.value)
}

let connectionPointDrag=null;

function connectionPointAbsoluteTime(c){
  if(!c?.parentClipId)return null;
  const p=getClip(c.parentClipId);
  if(!p)return null;
  const point=c.connectionPointOffset==null?Math.min(Math.max(+c.anchorOffset||0,0),p.duration):+c.connectionPointOffset;
  return p.start+point
}
function connectionSvgPointForTime(time,laneBox,innerBox){
  return laneBox.left-innerBox.left+(time/DURATION)*laneBox.width
}
function renderConnectionPoints(){
  const inner=$('#timelineInner'),videoLane=$('#lane-video');
  if(!inner||!videoLane)return;
  inner.querySelector('.connection-overlay')?.remove();
  const connected=clips.filter(c=>c.track!=='video'&&c.parentClipId);
  if(!connected.length)return;
  const innerBox=inner.getBoundingClientRect(),laneBox=videoLane.getBoundingClientRect();
  const height=Math.max(inner.scrollHeight,inner.clientHeight);
  const width=Math.max(inner.scrollWidth,inner.clientWidth);
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');
  svg.classList.add('connection-overlay');
  svg.setAttribute('width',width);svg.setAttribute('height',height);
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
  connected.forEach(c=>{
    const childEl=inner.querySelector(`.clip[data-clip="${CSS.escape(c.id)}"]`);
    if(!childEl)return;
    const childBox=childEl.getBoundingClientRect();
    let parentId=c.parentClipId,pointOffset=c.connectionPointOffset;
    if(connectionPointDrag?.childId===c.id&&connectionPointDrag.preview){
      parentId=connectionPointDrag.preview.parentId;
      pointOffset=connectionPointDrag.preview.pointOffset;
    }
    const parent=getClip(parentId);
    if(!parent)return;
    if(pointOffset==null)pointOffset=Math.min(Math.max(+c.anchorOffset||0,0),parent.duration);
    const anchorTime=parent.start+(+pointOffset||0);
    const x1=childBox.left-innerBox.left+Math.min(14,Math.max(5,childBox.width/2));
    const y1=childBox.top-innerBox.top+(childBox.top<laneBox.top?childBox.height:0);
    const x2=connectionSvgPointForTime(anchorTime,laneBox,innerBox);
    const y2=laneBox.top-innerBox.top+laneBox.height/2;
    const path=document.createElementNS(ns,'path');
    const midY=y1+(y2-y1)*.52;
    path.setAttribute('d',`M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`);
    path.classList.add('connection-line');
    if(c.id===selectedClip)path.classList.add('selected');
    svg.appendChild(path);
    const dot=document.createElementNS(ns,'circle');
    dot.setAttribute('cx',x2);dot.setAttribute('cy',y2);dot.setAttribute('r',c.id===selectedClip?'5':'2.5');
    dot.classList.add('connection-point');
    dot.dataset.childId=c.id;
    if(c.id===selectedClip){
      dot.classList.add('selected');
      dot.setAttribute('tabindex','0');
      dot.setAttribute('role','slider');
      dot.setAttribute('aria-label',`Point de connexion de ${c.label}`);
      dot.addEventListener('pointerdown',ev=>beginConnectionPointDrag(ev,c.id));
    }
    svg.appendChild(dot)
  });
  inner.appendChild(svg)
}
function connectionTimeFromPointer(ev){
  const lane=$('#lane-video');if(!lane)return null;
  const box=lane.getBoundingClientRect();
  return Math.max(0,Math.min(DURATION,((ev.clientX-box.left)/box.width)*DURATION))
}
function beginConnectionPointDrag(ev,childId){
  if(ev.button!==0)return;
  const child=getClip(childId),parent=child&&getClip(child.parentClipId);
  if(!child||!parent)return;
  ev.preventDefault();ev.stopPropagation();
  selectedClip=childId;
  connectionPointDrag={childId,before:cloneClips(),start:connectionPointAbsoluteTime(child),preview:null};
  document.addEventListener('pointermove',onConnectionPointDrag);
  document.addEventListener('pointerup',endConnectionPointDrag,{once:true});
  $('#interactionReadout').textContent='Déplacer le point de connexion…';
  renderInspector()
}
function onConnectionPointDrag(ev){
  if(!connectionPointDrag)return;
  const raw=connectionTimeFromPointer(ev);if(raw==null)return;
  const time=snapTime(raw),parent=connectionTargetAt(time);
  if(!parent){
    connectionPointDrag.preview=null;
    $('#interactionReadout').textContent='Point hors Storyline';
    renderConnectionPoints();return
  }
  connectionPointDrag.preview={
    time,
    parentId:parent.id,
    pointOffset:+Math.min(Math.max(time-parent.start,0),parent.duration).toFixed(6),
  };
  $('#interactionReadout').textContent=`CONNEXION · ${parent.label} · ${fmt(time)}`;
  renderConnectionPoints()
}
async function endConnectionPointDrag(){
  document.removeEventListener('pointermove',onConnectionPointDrag);
  if(!connectionPointDrag)return;
  const state=connectionPointDrag;connectionPointDrag=null;
  $('#interactionReadout').textContent='Storyline magnétique · drag · ripple trim';
  if(!state.preview){renderTracks();return}
  const before=state.before;
  if(backendConnected){
    const original=before.find(c=>c.id===state.childId);
    if(original
      && original.parentClipId===state.preview.parentId
      && Math.abs((+original.connectionPointOffset||0)-(+state.preview.pointOffset||0))<1e-6
    ){renderTracks();return}
    await commitBackendMagneticOperation(
      'connection_point',
      {child_id:state.childId,target_time:state.preview.time},
      'Point de connexion déplacé',
      before,
    );
    return
  }
  const candidate=cloneClips(before);
  try{setConnectionPointOnCandidate(candidate,state.childId,state.preview.time)}
  catch(err){toast(err.message||String(err),true);renderTracks();return}
  const original=before.find(c=>c.id===state.childId),next=candidate.find(c=>c.id===state.childId);
  if(!original||!next||(
    original.parentClipId===next.parentClipId
    && Math.abs((+original.connectionPointOffset||0)-(+next.connectionPointOffset||0))<1e-6
  )){renderTracks();return}
  await commitMagneticCandidate(candidate,'Point de connexion déplacé',before)
}
async function applyConnectionPointFromInspector(){
  const c=getClip(selectedClip),parent=c&&getClip(c.parentClipId);
  if(!c||!parent)return;
  const value=+$('#connectionPointInput')?.value;
  if(!Number.isFinite(value)){toast('Point de connexion invalide',true);return}
  const time=parent.start+Math.max(0,Math.min(parent.duration,value));
  const before=cloneClips();
  if(backendConnected){
    await commitBackendMagneticOperation(
      'connection_point',
      {child_id:c.id,target_time:time},
      'Point de connexion ajusté',
      before,
    );
    return
  }
  const candidate=cloneClips();
  try{setConnectionPointOnCandidate(candidate,c.id,time)}
  catch(err){toast(err.message||String(err),true);return}
  await commitMagneticCandidate(candidate,'Point de connexion ajusté',before)
}

const _v012RenderTracks=renderTracks;
renderTracks=function(){
  _v012RenderTracks();
  $$('.clip').forEach(el=>{
    const c=getClip(el.dataset.clip);if(!c?.parentClipId)return;
    el.classList.add('connected');
    const tag=document.createElement('span');
    tag.className='connection-badge';
    const p=getClip(c.parentClipId),point=p?(c.connectionPointOffset==null?Math.min(Math.max(+c.anchorOffset||0,0),p.duration):+c.connectionPointOffset):0;
    tag.textContent='↳ '+(p?.label||c.parentClipId)+' · +'+point.toFixed(1)+'s';
    el.appendChild(tag)
  });
  requestAnimationFrame(renderConnectionPoints)
}

document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){
    e.preventDefault();undoLastEdit()
  }
});

window.addEventListener('resize',()=>renderConnectionPoints());
