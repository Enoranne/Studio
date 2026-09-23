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
  c.parentClipId=parent.id;c.anchorOffset=+(c.start-parent.start).toFixed(6);c.connectionMode='follow'
}
function detachChild(c){if(!c)return;delete c.parentClipId;delete c.anchorOffset;delete c.connectionMode}
function changeConnection(parentId){
  const c=getClip(selectedClip);if(!c||c.track==='video')return;
  if(!parentId)detachChild(c);else connectChild(c,parentId);
  renderTracks();toast(parentId?'Élément connecté à la STORY':'Élément détaché')
}

function cloneClips(list=clips){return list.map(c=>({...c,volumeEnvelope:Array.isArray(c.volumeEnvelope)?c.volumeEnvelope.map(p=>({...p})):c.volumeEnvelope}))}
function reflowCandidate(candidate,orderIds=null){
  const story=storyClipsSorted(candidate),byId=new Map(candidate.map(c=>[c.id,c]));
  const ordered=orderIds?orderIds.map(id=>byId.get(id)).filter(Boolean):story;
  const expected=new Set(story.map(c=>c.id));if(ordered.length!==story.length||ordered.some(c=>!expected.has(c.id)))throw new Error('Ordre STORY invalide');
  let cursor=getStorylineStart();
  ordered.forEach(c=>{c.start=+cursor.toFixed(6);cursor+=c.duration});
  const parents=new Map(ordered.map(c=>[c.id,c]));
  candidate.forEach(c=>{if(!c.parentClipId)return;const p=parents.get(c.parentClipId);if(!p)throw new Error(`Parent absent pour ${c.label}`);if(c.anchorOffset==null)c.anchorOffset=+(c.start-p.start).toFixed(6);c.connectionMode='follow';c.start=+(p.start+(+c.anchorOffset||0)).toFixed(6)});
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
    if(c.parentClipId){const p=candidate.find(x=>x.id===c.parentClipId&&x.track==='video');if(!p)return `Parent manquant pour ${c.label}`;if(Math.abs(c.start-(p.start+(+c.anchorOffset||0)))>1e-4)return `Connexion incohérente pour ${c.label}`}
    (byTrack[c.track]??=[]).push(c)
  }
  for(const arr of Object.values(byTrack)){arr.sort((a,b)=>a.start-b.start);for(let i=1;i<arr.length;i++){if(arr[i].start<arr[i-1].start+arr[i-1].duration-1e-6)return `Collision : ${arr[i-1].label} / ${arr[i].label}`}}
  const story=storyClipsSorted(candidate);let cursor=getStorylineStart();for(const c of story){if(Math.abs(c.start-cursor)>1e-4)return 'Storyline non contiguë';cursor+=c.duration}
  return null
}
function backendTimelinePayload(list=clips,mode=storylineMode){
  return {edit_name:activeEditName,duration_seconds:DURATION,storyline:{mode,start:getStorylineStart()},tracks,clips:list.map(c=>{const n={...c};const m=c.mediaId&&getMedia(c.mediaId),a=c.audioId&&getAudio(c.audioId);if(m?.dbId)n.mediaDbId=m.dbId;if(a?.dbId)n.audioDbId=a.dbId;delete n.mediaId;delete n.audioId;return n})}
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
  const before=cloneClips(),candidate=cloneClips(),target=candidate.find(c=>c.id===state.clipId);if(!target)return;
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
  const before=cloneClips(),candidate=cloneClips(),newClip={id:'v'+Date.now(),track:'video',mediaId:m.id,label:m.label,start,duration:d,sourceStart:m.in||0};candidate.push(newClip);
  const others=storyClipsSorted(candidate).filter(c=>c.id!==newClip.id),idx=others.filter(c=>start>=c.start+c.duration/2).length,order=others.map(c=>c.id);order.splice(idx,0,newClip.id);reflowCandidate(candidate,order);selectedClip=newClip.id;selectedMedia=m.id;commitMagneticCandidate(candidate,`${m.label} inséré dans la Storyline`,before)
}

addMedia=function(){
  const m=getMedia(selectedMedia);if(!m)return;if(!updateMediaRange())return;
  const before=cloneClips(),candidate=cloneClips(),story=storyClipsSorted(candidate),start=story.length?story[story.length-1].start+story[story.length-1].duration:getStorylineStart(),d=(m.out??m.duration)-(m.in||0);
  const c={id:'v'+Date.now(),track:'video',mediaId:m.id,label:m.label,start,duration:d,sourceStart:m.in||0};candidate.push(c);reflowCandidate(candidate);selectedClip=c.id;commitMagneticCandidate(candidate,m.label+' ajouté à la Storyline',before)
}

const _legacyRemoveClip=removeClip;
removeClip=function(){
  const c=getClip(selectedClip);if(!c||c.track!=='video')return _legacyRemoveClip();
  const before=cloneClips(),candidate=cloneClips().filter(x=>x.id!==c.id);candidate.forEach(x=>{if(x.parentClipId===c.id)detachChild(x)});reflowCandidate(candidate);selectedClip=candidate[0]?.id||null;commitMagneticCandidate(candidate,'Plan supprimé · Storyline refermée',before)
}

const _v012RenderInspector=renderInspector;
renderInspector=function(){
  _v012RenderInspector();const c=getClip(selectedClip);if(!c||c.track==='video')return;
  const root=$('#inspector'),story=storyClipsSorted(),section=document.createElement('div');section.className='inspector-section connection-section';
  section.innerHTML=`<div class="inspector-section-title">CONNEXION STORY</div><div class="row"><label>Plan parent</label><select id="parentClipSelect"><option value="">Détaché</option>${story.map(p=>`<option value="${p.id}" ${c.parentClipId===p.id?'selected':''}>${p.label} · ${fmt(p.start)}</option>`).join('')}</select></div><div class="hint">${c.parentClipId?`Suit ${getClip(c.parentClipId)?.label||c.parentClipId} avec un offset de ${(+c.anchorOffset||0).toFixed(1)} s.`:'Position absolue : ne suivra aucun plan STORY.'}</div>`;
  root.insertBefore(section,root.lastElementChild);$('#parentClipSelect').onchange=e=>changeConnection(e.target.value)
}

const _v012RenderTracks=renderTracks;
renderTracks=function(){_v012RenderTracks();$$('.clip').forEach(el=>{const c=getClip(el.dataset.clip);if(!c?.parentClipId)return;el.classList.add('connected');const tag=document.createElement('span');tag.className='connection-badge';tag.textContent='↳ '+(getClip(c.parentClipId)?.label||c.parentClipId);el.appendChild(tag)})}

document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){
    e.preventDefault();undoLastEdit()
  }
});
