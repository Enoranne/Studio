let DURATION=30,HARD_END=3; const MIN_CLIP=.2;
const media=[
{id:'r017',file:'rush_017.mp4',label:'MALO + FISHER',duration:5,tags:['Malo','Fisher Price'],canon:true,safe:true,spoiler:0,note:'Malo avec le magnétophone Fisher Price.',in:0,out:5,url:null},
{id:'r024',file:'rush_024.mp4',label:'RONAN · RIRE',duration:5,tags:['Ronan','rire'],canon:true,safe:true,spoiler:0,note:'Rire de Ronan, motif émotionnel fort.',in:0,out:5,url:null},
{id:'r031',file:'rush_031.mp4',label:'MOBYLETTE',duration:5,tags:['extérieur','mobylette'],canon:false,safe:true,spoiler:0,note:'Plan extérieur dynamique.',in:0,out:5,url:null},
{id:'r044',file:'rush_044.mp4',label:'PHILIPS D6920',duration:5,tags:['Philips','cassette'],canon:true,safe:false,spoiler:1,note:'Objet canonique plus tardif.',in:0,out:5,url:null},
{id:'r052',file:'rush_052.mp4',label:'RADIO MALO',duration:5,tags:['radio','chambre'],canon:false,safe:true,spoiler:0,note:'Construction de l’univers sonore enfant.',in:0,out:5,url:null},
{id:'r063',file:'rush_063.mp4',label:'CASSETTES',duration:5,tags:['BIEN','RATÉS MAIS GARDER'],canon:true,safe:true,spoiler:0,note:'Insert cassette très lisible.',in:0,out:5,url:null},
{id:'r071',file:'rush_071.mp4',label:'PORTAIL · BONJOUR',duration:5,tags:['portail','vent'],canon:false,safe:true,spoiler:0,note:'Motif poétique extérieur.',in:0,out:5,url:null},
{id:'r078',file:'rush_078.mp4',label:'CUISINE · MÈRE',duration:5,tags:['Mère','frigo'],canon:false,safe:false,spoiler:2,note:'Souvenir narratif à protéger.',in:0,out:5,url:null}
];
const audioAssets=[
{id:'au_vo',file:'vo_malo_adulte.wav',label:'VO MALO ADULTE',role:'vo',duration:8,tags:['vo','Malo adulte'],note:'Voix off principale.',url:null,peaks:null},
{id:'au_music',file:'bed_musical.wav',label:'BED MUSICAL',role:'music',duration:22,tags:['music','bed'],note:'Lit musical du teaser.',url:null,peaks:null},
{id:'au_hiss',file:'cassette_hiss.wav',label:'CASSETTE HISS',role:'sfx',duration:5,tags:['cassette','souffle'],note:'Texture magnétophone / cassette.',url:null,peaks:null},
{id:'au_click',file:'click.wav',label:'CLICK',role:'sfx',duration:1,tags:['cassette','click'],note:'Clic mécanique de fin.',url:null,peaks:null}
];
const tracks=[
{id:'video',name:'VIDEO',kind:'video',muted:false,locked:false},
{id:'titles',name:'TITLES',kind:'title',muted:false,locked:false},
{id:'vo',name:'VO',kind:'audio',muted:false,locked:false},
{id:'music',name:'MUSIC',kind:'music',muted:false,locked:false},
{id:'sfx',name:'SFX',kind:'sfx',muted:false,locked:false}
];
let clips=[
{id:'v1',track:'video',mediaId:'r017',label:'MALO + FISHER',start:3,duration:5,sourceStart:0},
{id:'v2',track:'video',mediaId:'r024',label:'RONAN · RIRE',start:8,duration:5,sourceStart:0},
{id:'v3',track:'video',mediaId:'r063',label:'CASSETTES',start:13,duration:5,sourceStart:0},
{id:'v4',track:'video',mediaId:'r071',label:'PORTAIL · BONJOUR',start:18,duration:5,sourceStart:0},
{id:'t1',track:'titles',label:'PISTE 0',start:24,duration:3,text:'PISTE 0'},
{id:'a1',track:'vo',audioId:'au_vo',label:'VO Malo adulte',start:3.5,duration:8,sourceStart:0,gain:1,fadeIn:.25,fadeOut:.35},
{id:'m1',track:'music',audioId:'au_music',label:'Bed musical',start:3,duration:22,sourceStart:0,gain:.55,fadeIn:1.2,fadeOut:1.5},
{id:'s1',track:'sfx',audioId:'au_hiss',label:'Cassette hiss',start:3,duration:5,sourceStart:0,gain:.7,fadeIn:.15,fadeOut:.4},
{id:'s2',track:'sfx',audioId:'au_click',label:'CLICK',start:27,duration:1,sourceStart:0,gain:1,fadeIn:0,fadeOut:.08}
];
let selectedClip='v1',selectedMedia='r017',selectedAudio='au_vo',libraryMode='video',playhead=0,playing=false,raf=null,playStartPerf=0,playStartHead=0,currentMonitorMedia=null,interaction=null,audioPlayers=new Map(),audioContext=null;
let backendConnected=false, backendState=null, activeEditName='teaser_30', activeVersion=null;
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const fmt=t=>`00:${String(Math.floor(Math.max(0,t))).padStart(2,'0')}.${Math.round((Math.max(0,t)%1)*10)}`;
const getMedia=id=>media.find(m=>m.id===id),getAudio=id=>audioAssets.find(a=>a.id===id),getTrack=id=>tracks.find(t=>t.id===id),getClip=id=>clips.find(c=>c.id===id);
const snapValue=()=>+$('#snap').value;
function snapTime(v){const s=snapValue();return Math.round(v/s)*s}
function toast(msg,error=false){const e=$('#toast');e.textContent=msg;e.className='toast show'+(error?' error':'');clearTimeout(window.__t);window.__t=setTimeout(()=>e.className='toast',2200)}
function initRuler(){const r=$('#ruler');for(let i=0;i<=30;i+=3){const s=document.createElement('span');s.style.left=`${i/DURATION*100}%`;s.textContent=i+'s';r.appendChild(s)}r.onclick=e=>{const box=r.getBoundingClientRect();setPlayhead(((e.clientX-box.left)/box.width)*DURATION)}}
function activeVideoClip(t=playhead){return clips.filter(c=>c.track==='video'&&t>=c.start&&t<c.start+c.duration).sort((a,b)=>a.start-b.start)[0]||null}
function activeTitle(t=playhead){return clips.find(c=>c.track==='titles'&&t>=c.start&&t<c.start+c.duration)||null}
function setPlayhead(t,fromPlayback=false){playhead=Math.max(0,Math.min(DURATION,t));$('#playhead').style.left=`calc(86px + (100% - 86px) * ${playhead/DURATION})`;$('#timecode').textContent=fmt(playhead);$('#viewerHud').textContent=`V001 · ${fmt(playhead)}`;syncProgramMonitor(fromPlayback);syncAudio(fromPlayback);syncTitle()}
function step(d){pausePlayback();setPlayhead(playhead+d)}
function syncTitle(){const title=activeTitle();$('#viewerTitle').classList.toggle('show',!!title);$('#viewerTitle').textContent=title?.text||title?.label||''}
function setPlaceholder(title,body){const p=$('#viewerPlaceholder');p.innerHTML=`<strong>${title}</strong>${body}`;$('#viewer').classList.remove('has-video')}
function syncProgramMonitor(fromPlayback=false){
  const clip=activeVideoClip();const v=$('#video');
  if(!clip){currentMonitorMedia=null;v.pause();$('#viewerSource').textContent='NO VIDEO';setPlaceholder('PISTE 0 · PREVIEW','Aucun clip VIDEO sous le playhead.');return}
  const m=getMedia(clip.mediaId);$('#viewerSource').textContent=`${clip.label} · ${fmt(clip.sourceStart+(playhead-clip.start))}`;
  if(!m?.url){currentMonitorMedia=null;v.pause();setPlaceholder(clip.label,`Rush local non associé.<br><small>${m?.file||''} · Source ${fmt(clip.sourceStart)} → ${fmt(clip.sourceStart+clip.duration)}</small>`);return}
  const target=Math.min(m.duration-.01,Math.max(0,clip.sourceStart+(playhead-clip.start)));
  const switchSource=currentMonitorMedia!==m.id;
  if(switchSource){currentMonitorMedia=m.id;v.pause();v.src=m.url;v.dataset.mediaId=m.id;v.onloadedmetadata=()=>{v.currentTime=Math.min(target,v.duration||target);$('#viewer').classList.add('has-video');if(playing)v.play().catch(()=>{})};v.load()}
  else{
    $('#viewer').classList.add('has-video');
    if(!fromPlayback||Math.abs((v.currentTime||0)-target)>.35){try{v.currentTime=target}catch(_){}}
    if(playing&&v.paused)v.play().catch(()=>{});if(!playing&&!v.paused)v.pause();
  }
}
function playbackFrame(now){if(!playing)return;const elapsed=(now-playStartPerf)/1000;let t=playStartHead+elapsed;if(t>=DURATION){pausePlayback();setPlayhead(0);return}setPlayhead(t,true);raf=requestAnimationFrame(playbackFrame)}
function togglePlay(){if(playing){pausePlayback();return}playing=true;$('#playBtn').textContent='❚❚';playStartPerf=performance.now();playStartHead=playhead;raf=requestAnimationFrame(playbackFrame);syncProgramMonitor(true)}
function pausePlayback(){playing=false;$('#playBtn').textContent='▶';if(raf)cancelAnimationFrame(raf);raf=null;$('#video').pause();audioPlayers.forEach(p=>p.pause())}
function trackCollision(c,ignore){return clips.find(x=>x.id!==ignore&&x.track===c.track&&c.start<x.start+x.duration&&c.start+c.duration>x.start&&!(typeof audioCrossfadeAllowed==='function'&&audioCrossfadeAllowed(c,x)))}
function allowedTrackIds(c){if(c.mediaId||c.track==='video')return ['video'];if(c.track==='titles')return ['titles'];if(c.audioId)return ['vo','music','sfx'];return ['vo','music','sfx']}
function validate(c,ignore){if(!allowedTrackIds(c).includes(c.track))return 'Type de piste incompatible';if(c.start<HARD_END)return 'HARD LOCK 00:00–00:03';if(c.duration<MIN_CLIP)return `Durée minimale ${MIN_CLIP}s`;if(c.start+c.duration>DURATION+1e-6)return 'Dépasse 30 s';const t=getTrack(c.track);if(t?.locked)return `Piste ${t.name} verrouillée`;if(c.mediaId){const m=getMedia(c.mediaId);if(c.sourceStart<0||c.sourceStart+c.duration>m.duration+1e-6)return 'Dépasse les bornes du rush source'}if(c.audioId){const a=getAudio(c.audioId);if(!a)return 'Source audio introuvable';if(c.sourceStart<0||c.sourceStart+c.duration>a.duration+1e-6)return 'Dépasse les bornes audio source';if((c.fadeIn||0)+(c.fadeOut||0)>c.duration+1e-6)return 'Fades supérieurs à la durée du clip';if(c.gainDb==null&&((c.gain??1)<0||(c.gain??1)>1))return 'Gain legacy hors plage 0–100 %'}const hit=trackCollision(c,ignore);if(hit)return `Collision avec ${hit.label}`;return null}
function renderTracks(){
  const root=$('#tracks');root.innerHTML='';
  tracks.forEach(t=>{
    const row=document.createElement('div');row.className='track';
    row.innerHTML=`<div class="track-head"><strong>${t.name}</strong><div class="track-controls"><button class="${t.muted?'on':''}" onclick="toggleMute('${t.id}')">M</button><button class="${t.locked?'on':''}" onclick="toggleTrackLock('${t.id}')">L</button></div></div><div class="lane" id="lane-${t.id}" data-track="${t.id}"><div class="lock-zone" style="${HARD_END>0?`width:${HARD_END/DURATION*100}%`:`display:none`}"></div></div>`;
    root.appendChild(row);const lane=row.querySelector('.lane');
    lane.addEventListener('dragover',e=>{const can=t.id==='video'||['vo','music','sfx'].includes(t.id);if(can){e.preventDefault();lane.classList.add('dragover')}});lane.addEventListener('dragleave',()=>lane.classList.remove('dragover'));lane.addEventListener('drop',e=>dropLibraryOnLane(e,t.id,lane));
    clips.filter(c=>c.track===t.id).sort((a,b)=>a.start-b.start).forEach(c=>{
      const e=document.createElement('div');e.className=`clip ${t.kind}${c.id===selectedClip?' selected':''}`;e.dataset.clip=c.id;e.style.left=`${c.start/DURATION*100}%`;e.style.width=`${c.duration/DURATION*100}%`;
      e.innerHTML=`<span class="handle left" data-edge="left"></span><b>${c.label}</b><small>${fmt(c.start)} · ${c.duration.toFixed(1)}s${c.audioId?` · ${Math.round((c.gain??1)*100)}%`:''}</small>${c.audioId?`<canvas class="waveform-canvas" data-clip-wave="${c.id}"></canvas>`:''}<span class="handle right" data-edge="right"></span>`;
      e.addEventListener('pointerdown',ev=>beginClipInteraction(ev,c.id,lane));e.addEventListener('click',ev=>{ev.stopPropagation();selectedClip=c.id;selectedMedia=c.mediaId||selectedMedia;renderTracks();renderInspector();setPlayhead(c.start);if(c.mediaId)renderMedia()});lane.appendChild(e)
    });
  });renderInspector();requestAnimationFrame(drawAllWaveforms)
}
function laneTimeFromEvent(ev,lane){const box=lane.getBoundingClientRect();return Math.max(0,Math.min(DURATION,((ev.clientX-box.left)/box.width)*DURATION))}
function beginClipInteraction(ev,clipId,lane){
  if(ev.button!==0)return;const c=getClip(clipId),track=getTrack(c.track);if(track.locked){toast(`Piste ${track.name} verrouillée`,true);return}
  ev.preventDefault();ev.stopPropagation();selectedClip=clipId;selectedMedia=c.mediaId||selectedMedia;const edge=ev.target.dataset.edge||'move';
  interaction={clipId,mode:edge,startX:ev.clientX,lane,start:{...c},element:ev.currentTarget,valid:true};interaction.element.classList.add('selected');
  document.addEventListener('pointermove',onClipPointerMove);document.addEventListener('pointerup',endClipInteraction,{once:true});renderInspector();$('#interactionReadout').textContent=edge==='move'?'Déplacement…':edge==='left'?'Trim IN…':'Trim OUT…'
}
function onClipPointerMove(ev){
  if(!interaction)return;const c=getClip(interaction.clipId),box=interaction.lane.getBoundingClientRect();const dt=(ev.clientX-interaction.startX)/box.width*DURATION;const base=interaction.start;let next={...base};
  if(interaction.mode==='move'){next.start=snapTime(base.start+dt)}
  else if(interaction.mode==='left'){
    let newStart=snapTime(base.start+dt);let delta=newStart-base.start;next.start=newStart;next.duration=base.duration-delta;if(next.mediaId||next.audioId)next.sourceStart=(base.sourceStart||0)+delta
  }else{next.duration=snapTime(base.duration+dt)}
  next.start=Math.max(0,next.start);next.duration=Math.max(MIN_CLIP,next.duration);
  const err=validate(next,c.id);interaction.valid=!err;interaction.preview=next;interaction.error=err;
  const el=interaction.element;el.classList.toggle('invalid',!!err);el.style.left=`${next.start/DURATION*100}%`;el.style.width=`${next.duration/DURATION*100}%`;el.querySelector('small').textContent=`${fmt(next.start)} · ${next.duration.toFixed(1)}s`;$('#interactionReadout').textContent=err||`${interaction.mode==='move'?'MOVE':interaction.mode==='left'?'IN':'OUT'} · ${fmt(next.start)} · ${next.duration.toFixed(1)}s`
}
function endClipInteraction(){
  document.removeEventListener('pointermove',onClipPointerMove);if(!interaction)return;const c=getClip(interaction.clipId);
  if(interaction.preview&&interaction.valid){Object.assign(c,interaction.preview);toast(interaction.mode==='move'?'Clip déplacé':'Trim appliqué')}else if(interaction.error){toast(interaction.error,true)}
  interaction=null;$('#interactionReadout').textContent='Glisser · rogner · déposer';renderTracks();setPlayhead(c.start)
}
function dropLibraryOnLane(e,trackId,lane){
  e.preventDefault();lane.classList.remove('dragover');const start=snapTime(laneTimeFromEvent(e,lane));
  const mid=e.dataTransfer.getData('text/piste-media');if(mid){if(trackId!=='video')return toast('Un rush vidéo se dépose sur VIDEO',true);const m=getMedia(mid);if(!m)return;const d=Math.max(MIN_CLIP,m.out-m.in);const c={id:'v'+Date.now(),track:'video',mediaId:m.id,label:m.label,start,duration:d,sourceStart:m.in};const err=validate(c);if(err)return toast(err,true);clips.push(c);selectedClip=c.id;selectedMedia=m.id;renderTracks();setPlayhead(c.start);return toast(`${m.label} déposé à ${fmt(c.start)}`)}
  const aid=e.dataTransfer.getData('text/piste-audio');if(aid){if(!['vo','music','sfx'].includes(trackId))return toast('Une source audio se dépose sur VO / MUSIC / SFX',true);const a=getAudio(aid);if(!a)return;const d=Math.min(a.duration,Math.max(MIN_CLIP,a.duration));const c={id:'a'+Date.now(),track:trackId,audioId:a.id,label:a.label,start,duration:d,sourceStart:0,gain:1,fadeIn:.1,fadeOut:.2};const err=validate(c);if(err)return toast(err,true);clips.push(c);selectedClip=c.id;selectedAudio=a.id;renderTracks();setPlayhead(c.start);toast(`${a.label} déposé sur ${getTrack(trackId).name}`)}
}
function renderMedia(){
  const q=$('#mediaSearch').value.toLowerCase().trim(),root=$('#mediaList');root.innerHTML='';
  $$('.libtab').forEach(b=>b.classList.toggle('active',b.dataset.lib===libraryMode));
  $('#libraryHelp').innerHTML=libraryMode==='video'?'Glisse un rush vers la piste <b>VIDEO</b>. Les fichiers locaux portant le même nom sont associés automatiquement.':'Glisse une source vers <b>VO / MUSIC / SFX</b>. La forme d’onde est calculée localement après import.';
  if(libraryMode==='video'){const list=media.filter(m=>(m.file+' '+m.label+' '+m.tags.join(' ')).toLowerCase().includes(q));$('#mediaCount').textContent=list.length;
    list.forEach(m=>{const e=document.createElement('div');e.className='media-row'+(selectedMedia===m.id?' selected':'')+(m.url?' bound':'');e.draggable=true;e.innerHTML=`<div class="mini-thumb">${m.label}<span>${m.duration.toFixed(1)}s</span></div><div><b>${m.file}</b><p>${m.tags.join(' · ')}</p><div class="badges">${m.canon?'<span class="badge canon">CANON</span>':''}${m.safe?'<span class="badge safe">SAFE</span>':''}<span class="badge">S${m.spoiler}</span>${m.url?'<span class="badge local">LOCAL</span>':''}</div></div>`;e.ondragstart=ev=>{ev.dataTransfer.setData('text/piste-media',m.id);ev.dataTransfer.effectAllowed='copy'};e.onclick=()=>{selectedMedia=m.id;selectedClip=null;renderMedia();renderMediaInspector();previewMedia(m.id)};root.appendChild(e)})
  }else{const list=audioAssets.filter(a=>(a.file+' '+a.label+' '+a.tags.join(' ')).toLowerCase().includes(q));$('#mediaCount').textContent=list.length;
    list.forEach(a=>{const e=document.createElement('div');e.className=`media-row audio-row ${a.role==='music'?'music-row':a.role==='sfx'?'sfx-row':''}${selectedAudio===a.id?' selected':''}${a.url?' audio-bound':''}`;e.draggable=true;e.innerHTML=`<div class="mini-thumb">${a.role.toUpperCase()}<span>${a.duration.toFixed(1)}s</span></div><div><b>${a.file}</b><p>${a.tags.join(' · ')}</p><div class="badges"><span class="badge">${a.role.toUpperCase()}</span>${a.url?'<span class="badge local">LOCAL</span>':''}</div><div class="asset-wave"><canvas data-asset-wave="${a.id}"></canvas></div></div>`;e.ondragstart=ev=>{ev.dataTransfer.setData('text/piste-audio',a.id);ev.dataTransfer.effectAllowed='copy'};e.onclick=()=>{selectedAudio=a.id;selectedClip=null;renderMedia();renderAudioInspector()};root.appendChild(e)});requestAnimationFrame(drawAllWaveforms)
  }updateLocalStatus()
}
function renderMediaInspector(){
  const m=getMedia(selectedMedia);if(!m)return;$('#selectionKind').textContent='MÉDIA';$('#inspector').innerHTML=`<h3>${m.file}</h3><p>${m.note}</p><div class="badges">${m.canon?'<span class="badge canon">CANON</span>':''}${m.safe?'<span class="badge safe">TRAILER-SAFE</span>':''}<span class="badge">S${m.spoiler}</span>${m.url?'<span class="badge local">FICHIER LOCAL ASSOCIÉ</span>':''}</div><div class="form-grid" style="margin-top:10px"><div class="row"><label>Source IN</label><input id="mi" type="number" value="${m.in}" min="0" max="${m.duration}" step="0.1"></div><div class="row"><label>Source OUT</label><input id="mo" type="number" value="${m.out}" min="0.1" max="${m.duration}" step="0.1"></div></div><div class="ins-actions"><button class="btn primary" onclick="addMedia()">Ajouter VIDEO</button><button class="btn" onclick="bindSelectedMedia()">${m.url?'Remplacer fichier local':'Associer fichier local'}</button></div><div class="${m.url?'okbox':'hint'}" style="margin-top:8px">${m.url?'Le viewer peut prévisualiser ce rush sur la timeline.':'Tu peux aussi glisser ce rush directement sur la piste VIDEO.'}</div>`;
  $('#mi').onchange=updateMediaRange;$('#mo').onchange=updateMediaRange
}
function renderAudioInspector(){const a=getAudio(selectedAudio);if(!a)return;$('#selectionKind').textContent='AUDIO';$('#inspector').innerHTML=`<h3>${a.file}</h3><p>${a.note}</p><div class="badges"><span class="badge">${a.role.toUpperCase()}</span>${a.url?'<span class="badge local">FICHIER LOCAL</span>':''}</div><div class="asset-wave" style="height:58px;margin-top:10px"><canvas data-asset-wave="${a.id}"></canvas></div><div class="ins-actions"><button class="btn primary" onclick="addAudioAssetToTimeline()">Ajouter ${a.role.toUpperCase()}</button><button class="btn" onclick="bindSelectedAudio()">${a.url?'Remplacer fichier':'Associer fichier local'}</button><button class="btn" onclick="previewAudioAsset()">▶ Écouter</button></div><div class="${a.url?'okbox':'hint'}" style="margin-top:8px">${a.url?'Audio décodé localement · durée '+a.duration.toFixed(2)+' s':'Associe un WAV/MP3/M4A pour calculer la forme d’onde et activer le mix.'}</div>`;requestAnimationFrame(drawAllWaveforms)}
function addAudioAssetToTimeline(){const a=getAudio(selectedAudio);if(!a)return;let track=a.role;let start=HARD_END;const same=clips.filter(c=>c.track===track);if(same.length)start=Math.max(HARD_END,...same.map(c=>c.start+c.duration));const c={id:'a'+Date.now(),track,audioId:a.id,label:a.label,start:snapTime(start),duration:Math.min(a.duration,DURATION-start),sourceStart:0,gain:1,fadeIn:.1,fadeOut:.2};const err=validate(c);if(err)return toast(err,true);clips.push(c);selectedClip=c.id;renderTracks();setPlayhead(c.start);toast(a.label+' ajouté à '+getTrack(track).name)}
function bindSelectedAudio(){window.__bindAudioTarget=selectedAudio;$('#singleAudioInput').value='';$('#singleAudioInput').click()}
function previewAudioAsset(){const a=getAudio(selectedAudio);if(!a?.url)return toast('Associe d’abord le fichier audio local',true);pausePlayback();let p=new Audio(a.url);p.volume=.9;p.play().catch(()=>toast('Lecture audio bloquée par le navigateur',true));setTimeout(()=>p.pause(),Math.min(a.duration,8)*1000)}
function updateMediaRange(){const m=getMedia(selectedMedia);if(!m)return false;const i=+$('#mi').value,o=+$('#mo').value;if(i<0||o>m.duration||o-i<MIN_CLIP){toast('Plage IN/OUT invalide',true);renderMediaInspector();return false}m.in=i;m.out=o;return true}
function renderInspector(){
  const c=getClip(selectedClip);if(!c){libraryMode==='audio'?renderAudioInspector():renderMediaInspector();return}const t=getTrack(c.track),m=c.mediaId?getMedia(c.mediaId):null,a=c.audioId?getAudio(c.audioId):null;$('#selectionKind').textContent=t.name;$('#inspector').innerHTML=`<h3>${c.label}</h3><p>${m?m.note:a?a.note:'Élément '+t.name.toLowerCase()+' de la timeline.'}</p><div class="form-grid"><div class="row"><label>Piste</label><select id="ct">${tracks.filter(x=>allowedTrackIds(c).includes(x.id)).map(x=>`<option value="${x.id}" ${x.id===c.track?'selected':''}>${x.name}</option>`).join('')}</select></div><div class="row"><label>Début</label><input id="cs" type="number" value="${c.start}" min="0" max="30" step="0.1"></div><div class="row"><label>Durée</label><input id="cd" type="number" value="${c.duration}" min="0.2" max="30" step="0.1"></div>${m?`<div class="row"><label>Source IN</label><input id="ci" type="number" value="${c.sourceStart||0}" min="0" max="${m.duration}" step="0.1"></div>`:''}${c.audioId?`<div class="row"><label>Source IN</label><input id="ci" type="number" value="${c.sourceStart||0}" min="0" max="${getAudio(c.audioId)?.duration||30}" step="0.1"></div><div class="row"><label>Gain %</label><input id="cg" type="number" value="${Math.round((c.gain??1)*100)}" min="0" max="100" step="1"></div><div class="row"><label>Fade in</label><input id="cfi" type="number" value="${c.fadeIn||0}" min="0" max="${c.duration}" step="0.05"></div><div class="row"><label>Fade out</label><input id="cfo" type="number" value="${c.fadeOut||0}" min="0" max="${c.duration}" step="0.05"></div>`:''}${c.track==='titles'?`<div class="row full"><label>Texte</label><input id="cx" value="${c.text||c.label}"></div>`:''}</div><div class="ins-actions"><button class="btn primary" onclick="applyEdit()">Appliquer PATCH</button><button class="btn" onclick="duplicateClip()">Dupliquer</button><button class="btn danger" onclick="removeClip()">Supprimer</button></div><div class="hint" style="margin-top:8px"><span class="kbd">drag</span> déplace · poignées gauche/droite = trim IN/OUT · snap ${snapValue()} s.</div><div class="warn">HARD LOCK, collisions et bornes source sont contrôlés avant validation.</div>`
}
function applyEdit(){const c=getClip(selectedClip);if(!c)return;const next={...c,track:$('#ct').value,start:+$('#cs').value,duration:+$('#cd').value};if(c.mediaId||c.audioId)next.sourceStart=+$('#ci').value;if(c.audioId){next.gain=+$('#cg').value/100;next.fadeIn=+$('#cfi').value;next.fadeOut=+$('#cfo').value}if(c.track==='titles')next.text=$('#cx').value;const err=validate(next,c.id);if(err){toast(err,true);return}Object.assign(c,next);renderTracks();setPlayhead(c.start);toast('PATCH local appliqué')}
function addMedia(){const m=getMedia(selectedMedia);if(!m)return;if(!updateMediaRange())return;const d=m.out-m.in;const same=clips.filter(c=>c.track==='video');let start=Math.max(HARD_END,...same.map(c=>c.start+c.duration));start=snapTime(start);const c={id:'v'+Date.now(),track:'video',mediaId:m.id,label:m.label,start,duration:d,sourceStart:m.in};const err=validate(c);if(err){toast(err,true);return}clips.push(c);selectedClip=c.id;renderTracks();setPlayhead(c.start);toast(m.label+' ajouté à VIDEO')}
function addTitle(){const c={id:'t'+Date.now(),track:'titles',label:'Nouveau titre',text:'Nouveau titre',start:24,duration:2};while(validate(c)&&c.start<28)c.start+=snapValue();const err=validate(c);if(err){toast(err,true);return}clips.push(c);selectedClip=c.id;renderTracks();toast('Titre ajouté')}
function addAudio(track){const a=audioAssets.find(x=>x.role===track)||audioAssets[0];const label=track==='vo'?'Nouvelle VO':track==='music'?'Nouvelle musique':'Nouveau SFX';const c={id:'a'+Date.now(),track,audioId:a?.id,label:a?.label||label,start:20,duration:Math.min(2,a?.duration||2),sourceStart:0,gain:1,fadeIn:.1,fadeOut:.2};while(validate(c)&&c.start<28)c.start+=snapValue();const err=validate(c);if(err){toast(err,true);return}clips.push(c);selectedClip=c.id;renderTracks();toast(label+' ajouté')}
function nudge(d){const c=getClip(selectedClip);if(!c)return;const next={...c,start:snapTime(c.start+d)},err=validate(next,c.id);if(err){toast(err,true);return}c.start=next.start;renderTracks();setPlayhead(c.start)}
function duplicateClip(){const c=getClip(selectedClip);if(!c)return;const n={...c,id:'x'+Date.now(),start:snapTime(c.start+c.duration)};const err=validate(n);if(err){toast(err,true);return}clips.push(n);selectedClip=n.id;renderTracks();toast('Clip dupliqué')}
function removeClip(){const p=audioPlayers.get(selectedClip);if(p){p.pause();audioPlayers.delete(selectedClip)}clips=clips.filter(c=>c.id!==selectedClip);selectedClip=clips[0]?.id||null;renderTracks();syncProgramMonitor();syncAudio();toast('Clip supprimé')}
function toggleMute(id){const t=getTrack(id);t.muted=!t.muted;renderTracks();toast(`${t.name} ${t.muted?'mutée':'active'}`)}
function toggleTrackLock(id){const t=getTrack(id);t.locked=!t.locked;renderTracks();toast(`${t.name} ${t.locked?'verrouillée':'déverrouillée'}`)}
function previewMedia(id){pausePlayback();const m=getMedia(id);if(!m)return;if(!m.url){setPlaceholder(m.label,`Rush local non associé.<br><small>${m.file}</small>`);$('#viewerSource').textContent=m.file;return}const v=$('#video');currentMonitorMedia=m.id;v.src=m.url;v.onloadedmetadata=()=>{v.currentTime=m.in;$('#viewer').classList.add('has-video');$('#viewerSource').textContent=`MEDIA · ${m.file}`};v.load()}
function bindSelectedMedia(){window.__bindTarget=selectedMedia;$('#singleFileInput').value='';$('#singleFileInput').click()}
function bindFileToMedia(m,file){if(m.url)URL.revokeObjectURL(m.url);m.url=URL.createObjectURL(file);m.localName=file.name}
function updateLocalStatus(){const nv=media.filter(m=>m.url).length,na=audioAssets.filter(a=>a.url).length,e=$('#localStatus');e.textContent=`${nv}/${media.length} vidéo · ${na}/${audioAssets.length} audio`;e.classList.toggle('warn',nv<media.length||na<audioAssets.length)}
function envelopeGain(c,t){const local=t-c.start;let g=c.gain??1;if((c.fadeIn||0)>0&&local<c.fadeIn)g*=Math.max(0,local/c.fadeIn);const rem=c.start+c.duration-t;if((c.fadeOut||0)>0&&rem<c.fadeOut)g*=Math.max(0,rem/c.fadeOut);return Math.max(0,Math.min(1,g))}
function ensureAudioPlayer(c){let p=audioPlayers.get(c.id),a=getAudio(c.audioId);if(!a?.url)return null;if(!p||p.dataset.url!==a.url){if(p)p.pause();p=new Audio(a.url);p.preload='auto';p.dataset.url=a.url;audioPlayers.set(c.id,p)}return p}
function syncAudio(fromPlayback=false){let active=0;clips.filter(c=>c.audioId).forEach(c=>{const tr=getTrack(c.track),a=getAudio(c.audioId),p=ensureAudioPlayer(c),on=!tr?.muted&&playhead>=c.start&&playhead<c.start+c.duration;if(!p||!a||!on){if(p&&!p.paused)p.pause();return}active++;const target=Math.max(0,Math.min(a.duration-.01,(c.sourceStart||0)+(playhead-c.start)));p.volume=envelopeGain(c,playhead);if(!fromPlayback||Math.abs((p.currentTime||0)-target)>.28){try{p.currentTime=target}catch(_){}}if(playing&&p.paused)p.play().catch(()=>{});if(!playing&&!p.paused)p.pause()});$('#mixMeter').textContent=`MIX · ${active} source${active>1?'s':''} active${active>1?'s':''}`}
async function bindAudioFile(a,file){if(a.url)URL.revokeObjectURL(a.url);a.url=URL.createObjectURL(file);a.localName=file.name;try{audioContext=audioContext||new (window.AudioContext||window.webkitAudioContext)();const buf=await audioContext.decodeAudioData(await file.arrayBuffer());a.duration=buf.duration;a.peaks=makePeaks(buf,160)}catch(err){a.peaks=null;toast('Audio associé, forme d’onde indisponible',true)}clips.filter(c=>c.audioId===a.id).forEach(c=>{c.sourceStart=Math.max(0,Math.min(c.sourceStart||0,Math.max(0,a.duration-MIN_CLIP)));c.duration=Math.min(c.duration,Math.max(MIN_CLIP,a.duration-c.sourceStart));c.fadeIn=Math.min(c.fadeIn||0,c.duration);c.fadeOut=Math.min(c.fadeOut||0,Math.max(0,c.duration-c.fadeIn))})}
function makePeaks(buffer,count){const chans=Array.from({length:buffer.numberOfChannels},(_,i)=>buffer.getChannelData(i)),len=buffer.length,step=Math.max(1,Math.floor(len/count)),out=[];for(let i=0;i<count;i++){let peak=0,start=i*step,end=Math.min(len,start+step);for(let j=start;j<end;j++){for(const ch of chans)peak=Math.max(peak,Math.abs(ch[j]||0))}out.push(peak)}return out}
function drawWave(canvas,peaks,startRatio=0,endRatio=1){if(!canvas||!peaks?.length)return;const dpr=devicePixelRatio||1,w=Math.max(10,canvas.clientWidth),h=Math.max(8,canvas.clientHeight);canvas.width=w*dpr;canvas.height=h*dpr;const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);ctx.strokeStyle='rgba(165,220,198,.9)';ctx.lineWidth=1;const i0=Math.floor(peaks.length*startRatio),i1=Math.max(i0+1,Math.ceil(peaks.length*endRatio)),slice=peaks.slice(i0,i1);for(let x=0;x<w;x++){const i=Math.min(slice.length-1,Math.floor(x/w*slice.length)),amp=slice[i]||0,y=amp*(h*.46);ctx.beginPath();ctx.moveTo(x,h/2-y);ctx.lineTo(x,h/2+y);ctx.stroke()}}
function drawAllWaveforms(){$$('[data-asset-wave]').forEach(c=>{const a=getAudio(c.dataset.assetWave);drawWave(c,a?.peaks)});$$('[data-clip-wave]').forEach(c=>{const clip=getClip(c.dataset.clipWave),a=clip&&getAudio(clip.audioId);if(!a?.peaks)return;drawWave(c,a.peaks,(clip.sourceStart||0)/a.duration,Math.min(1,((clip.sourceStart||0)+clip.duration)/a.duration))})}
