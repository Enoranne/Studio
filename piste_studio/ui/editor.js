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
function activeTitle(t=playhead){return clips.find(c=>c.track==='titles'&&t>=c.start&&t<c.start+c.