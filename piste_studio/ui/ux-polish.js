let lastFocusPane='viewer',commandIndex=0;

function focusClass(name){return name?`focus-${name}`:''}
function exitFocus(){
  ['browser','viewer','inspector','timeline'].forEach(n=>document.body.classList.remove(focusClass(n)));
  PisteState.set('focusPane',null);
  const exit=$('#focusExit');if(exit)exit.hidden=true;
  requestAnimationFrame(()=>{renderTracks();drawAllWaveforms()});
}
function setFocusPane(name){
  if(!['browser','viewer','inspector','timeline'].includes(name))return exitFocus();
  const current=PisteState.get('focusPane');
  if(current===name)return exitFocus();
  exitFocus();
  document.body.classList.add(focusClass(name));
  PisteState.set('focusPane',name);
  lastFocusPane=name;
  const exit=$('#focusExit');if(exit){exit.hidden=false;exit.textContent=`~ Quitter · ${name.toUpperCase()}`}
  requestAnimationFrame(()=>{renderTracks();drawAllWaveforms()});
}
function toggleFocusPane(){setFocusPane(PisteState.get('focusPane')?null:lastFocusPane)}

[
  ['#browserPanel','browser'],
  ['.viewer-panel','viewer'],
  ['#inspectorPanel','inspector'],
  ['.timeline-zone','timeline'],
].forEach(([selector,name])=>{
  const el=$(selector);if(!el)return;
  el.addEventListener('pointerenter',()=>lastFocusPane=name);
  el.addEventListener('dblclick',ev=>{
    if(ev.target.closest('button,input,select,.clip,.media-row'))return;
    setFocusPane(name);
  });
});
$$('.focus-trigger').forEach(b=>b.onclick=e=>{e.stopPropagation();setFocusPane(b.dataset.focusPane)});
$('#focusExit').onclick=exitFocus;

function applyOverlayState(){
  const viewer=$('#viewer');if(!viewer)return;
  const hud=PisteState.get('overlayHud')!==false;
  const mix=PisteState.get('overlayMix')===true;
  const range=PisteState.get('overlayRange')!==false;
  viewer.classList.toggle('hide-hud',!hud);
  viewer.classList.toggle('hide-mix',!mix);
  viewer.classList.toggle('hide-source-range',!range);
  if($('#overlayHud'))$('#overlayHud').checked=hud;
  if($('#overlayMix'))$('#overlayMix').checked=mix;
  if($('#overlayRange'))$('#overlayRange').checked=range;
}
function positionOverlayMenu(){
  const btn=$('#overlayBtn'),menu=$('#overlayMenu');if(!btn||!menu)return;
  const r=btn.getBoundingClientRect();
  menu.style.top=`${r.bottom+7}px`;
  menu.style.left=`${Math.max(10,r.right-menu.offsetWidth)}px`;
}
function toggleOverlayMenu(){
  const menu=$('#overlayMenu');if(!menu)return;
  menu.hidden=!menu.hidden;
  if(!menu.hidden)requestAnimationFrame(positionOverlayMenu);
}
$('#overlayBtn').onclick=e=>{e.stopPropagation();toggleOverlayMenu()};
[['#overlayHud','overlayHud'],['#overlayMix','overlayMix'],['#overlayRange','overlayRange']].forEach(([selector,key])=>{
  $(selector).onchange=e=>{PisteState.set(key,e.target.checked);applyOverlayState()}
});
document.addEventListener('pointerdown',e=>{
  const menu=$('#overlayMenu');if(menu&&!menu.hidden&&!e.target.closest('#overlayMenu')&&!e.target.closest('#overlayBtn'))menu.hidden=true;
});
window.addEventListener('resize',()=>{if(!$('#overlayMenu').hidden)positionOverlayMenu()});
applyOverlayState();

const commands=[
  {label:'Espace · Assemble',hint:'1',keywords:'workspace media browser',run:()=>setWorkspace('assemble')},
  {label:'Espace · Edit',hint:'2',keywords:'workspace montage timeline',run:()=>setWorkspace('edit')},
  {label:'Espace · Review',hint:'3',keywords:'workspace lecture review',run:()=>setWorkspace('review')},
  {label:'Viewer · Source',hint:'P',keywords:'source rush',run:()=>setViewerMode('source')},
  {label:'Viewer · Program',hint:'P',keywords:'program timeline montage',run:()=>setViewerMode('program')},
  {label:'Focus · Viewer',hint:'~',keywords:'fullscreen viewer cinema',run:()=>setFocusPane('viewer')},
  {label:'Focus · Timeline',hint:'~',keywords:'fullscreen timeline montage',run:()=>setFocusPane('timeline')},
  {label:'Focus · Browser',hint:'~',keywords:'fullscreen browser rushes',run:()=>setFocusPane('browser')},
  {label:'Focus · Inspecteur',hint:'~',keywords:'fullscreen inspector',run:()=>setFocusPane('inspector')},
  {label:'Panneau · Browser',hint:'B',keywords:'toggle media browser',run:toggleBrowser},
  {label:'Panneau · Inspecteur',hint:'I',keywords:'toggle inspector',run:toggleInspector},
  {label:'Panneau · Index',hint:'',keywords:'toggle index decisions locks',run:toggleIndex},
  {label:'Montage · Undo',hint:'⌘Z',keywords:'undo annuler checkpoint',run:()=>undoLastEdit()},
  {label:'Montage · Enregistrer',hint:'',keywords:'save timeline',run:()=>$('#saveBackendBtn')?.click()},
  {label:'Montage · Publier',hint:'',keywords:'publish version',run:()=>typeof publishVersion==='function'&&publishVersion()},
  {label:'Viewer · Overlays',hint:'',keywords:'overlay timecode mix in out',run:toggleOverlayMenu},
  {label:'Editorial · Ajouter un marqueur',hint:'M',keywords:'marker note decision beat vigilance',run:()=>typeof openMarkerComposer==='function'&&openMarkerComposer()},
  {label:'Editorial · Trouver des alternatives',hint:'',keywords:'source selector alternatives prise rush',run:()=>typeof openSourceSelector==='function'&&openSourceSelector()},
  {label:'Média · Analyser le catalogue',hint:'',keywords:'analyze analyse ffmpeg filmstrip media intelligence',run:()=>typeof analyzeMediaCatalog==='function'&&analyzeMediaCatalog()},
  {label:'Média · Prises proches',hint:'',keywords:'similar take duplicate proche visual',run:()=>typeof openSimilarTakes==='function'&&openSimilarTakes()},
  {label:'Vision · Analyser le rush',hint:'',keywords:'semantic clip local vision analyse',run:()=>typeof analyzeSemanticSelected==='function'&&analyzeSemanticSelected(false)},
  {label:'Vision · Proposer continuité',hint:'',keywords:'semantic continuity character prop decor look',run:()=>typeof openSemanticContinuity==='function'&&openSemanticContinuity()},
];
function filteredCommands(){
  const q=($('#commandSearch')?.value||'').trim().toLowerCase();
  return commands.filter(c=>(c.label+' '+c.keywords).toLowerCase().includes(q));
}
function renderCommandPalette(){
  const root=$('#commandResults');if(!root)return;
  const list=filteredCommands();if(commandIndex>=list.length)commandIndex=Math.max(0,list.length-1);
  root.innerHTML=list.length?list.map((c,i)=>`<button class="command-item ${i===commandIndex?'active':''}" data-command-index="${i}"><span>${c.label}</span><kbd>${c.hint||''}</kbd></button>`).join(''):'<div class="command-empty">Aucune commande</div>';
  $$('.command-item').forEach(el=>el.onclick=()=>executeCommand(+el.dataset.commandIndex));
}
function openCommandPalette(){
  const p=$('#commandPalette');if(!p)return;
  p.hidden=false;commandIndex=0;$('#commandSearch').value='';renderCommandPalette();
  requestAnimationFrame(()=>$('#commandSearch').focus());
}
function closeCommandPalette(){const p=$('#commandPalette');if(p)p.hidden=true}
function executeCommand(index){
  const list=filteredCommands(),cmd=list[index];if(!cmd)return;
  closeCommandPalette();cmd.run();
}
$('#commandSearch').addEventListener('input',()=>{commandIndex=0;renderCommandPalette()});
$('#commandSearch').addEventListener('keydown',e=>{
  const list=filteredCommands();
  if(e.key==='ArrowDown'){e.preventDefault();commandIndex=Math.min(list.length-1,commandIndex+1);renderCommandPalette()}
  if(e.key==='ArrowUp'){e.preventDefault();commandIndex=Math.max(0,commandIndex-1);renderCommandPalette()}
  if(e.key==='Enter'){e.preventDefault();executeCommand(commandIndex)}
  if(e.key==='Escape'){e.preventDefault();closeCommandPalette()}
});
$('#commandPalette').addEventListener('pointerdown',e=>{if(e.target===$('#commandPalette'))closeCommandPalette()});

const _v014SetWorkspace=setWorkspace;
setWorkspace=function(name){
  if(PisteState.get('focusPane'))exitFocus();
  _v014SetWorkspace(name);
};

document.addEventListener('keydown',e=>{
  const editable=e.target.matches('input,select,textarea');
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){
    e.preventDefault();openCommandPalette();return
  }
  if(e.key==='Escape'){
    if(!$('#commandPalette').hidden){closeCommandPalette();return}
    if(!$('#overlayMenu').hidden){$('#overlayMenu').hidden=true;return}
    if(PisteState.get('focusPane')){exitFocus();return}
  }
  if(editable)return;
  if(e.key==='~'||e.key==='²'||e.code==='Backquote'){e.preventDefault();toggleFocusPane()}
});

function refineWorkspacePanels(name){
  if(name==='assemble'){
    document.body.classList.remove('browser-collapsed');
    document.body.classList.add('inspector-collapsed','index-collapsed');
  }else if(name==='edit'){
    document.body.classList.remove('browser-collapsed','inspector-collapsed','index-collapsed');
  }else if(name==='review'){
    document.body.classList.add('browser-collapsed','inspector-collapsed');
    document.body.classList.remove('index-collapsed');
  }
}
const _workspaceWithFocus=setWorkspace;
setWorkspace=function(name){
  _workspaceWithFocus(name);
  refineWorkspacePanels(name);
  requestAnimationFrame(()=>{renderTracks();drawAllWaveforms()});
};
refineWorkspacePanels(activeWorkspace);
