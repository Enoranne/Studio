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
function trackCollision(c,ignore){return clips.find(x=>x.id!==ignore&&x.track===c.track&&c.start<x.start+x.duration&&c.start+c.duration>x.start)}
function allowedTrackIds(c){if(c.mediaId||c.track==='video')return ['video'];if(c.track==='titles')return ['titles'];if(c.audioId)return ['vo','music','sfx'];return ['vo','music','sfx']}
function validate(c,ignore){if(!allowedTrackIds(c).includes(c.track))return 'Type de piste incompatible';if(c.start<HARD_END)return 'HARD LOCK 00:00–00:03';if(c.duration<MIN_CLIP)return `Durée minimale ${MIN_CLIP}s`;if(c.start+c.duration>DURATION+1e-6)return 'Dépasse 30 s';const t=getTrack(c.track);if(t?.locked)return `Piste ${t.name} verrouillée`;if(c.mediaId){const m=getMedia(c.mediaId);if(c.sourceStart<0||c.sourceStart+c.duration>m.duration+1e-6)return 'Dépasse les bornes du rush source'}if(c.audioId){const a=getAudio(c.audioId);if(!a)return 'Source audio introuvable';if(c.sourceStart<0||c.sourceStart+c.duration>a.duration+1e-6)return 'Dépasse les bornes audio source';if((c.fadeIn||0)+(c.fadeOut||0)>c.duration+1e-6)return 'Fades supérieurs à la durée du clip';if((c.gain??1)<0||(c.gain??1)>1)return 'Gain hors plage 0–100 %'}const hit=trackCollision(c,ignore);if(hit)return `Collision avec ${hit.label}`;return null}
function renderTracks(){
  const root=$('#tracks');root.innerHTML='';
  tracks.forEach(t=>{
    const row=document.createElement('div');row.className='track';
    row.innerHTML=`<div class="track-head"><strong>${t.name}</strong><div class="track-controls"><button class="${t.muted?'on':''}" onclick="toggleMute('${t.id}')">M</button><button class="${t.locked?'on':''}" onclick="toggleTrackLock('${t.id}')">L</button></div></div><div class="lane" id="lane-${t.id}" data-track="${t.id}"><div class="lock-zone" style="${HARD_END>0?`width:${HARD_END/DURATION*100}%`:`display:none`}"></div></div>`;
    root.appendChild(row);const lane=row.querySelector('.lane');
    lane.addEventListener('dragover',e=>{const can=t.id==='video'||['vo','music','sfx'].includes(t.id);if(can){e.preventDefault();lane.classList.add('dragover')}});lane.addEventListener('dragleave',()=>lane.classList.remove('dragover'));lane.addEventListener('drop',e=>dropLibraryOnLane(e,t.id,lane));
    clips.filter(c=>c.track===t.id).sort((a,b)=>a.start-b.start).forEach(c=>{
      const e=document.createElement('div');e.className=`clip ${t.kind}${c.id===selectedClip?' selected':''}