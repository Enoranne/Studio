const TITLE_DEFAULTS={
  titlePreset:'center',
  fontFamily:'sans',
  fontSize:64,
  fontWeight:700,
  textAlign:'center',
  positionX:.5,
  positionY:.5,
  boxWidth:.8,
  color:'#FFFFFF',
  backgroundColor:'#000000',
  backgroundOpacity:0,
  opacity:1,
  padding:.02,
  cornerRadius:0,
  titleRole:'overlay',
  canvasBackgroundColor:'#000000',
  canvasBackgroundOpacity:0,
  blackTailSeconds:0,
};

function normalizeTitleClip(c){
  if(!c||c.track!=='titles')return c;
  const hadCanvasOpacity=c.canvasBackgroundOpacity!==undefined&&c.canvasBackgroundOpacity!==null&&c.canvasBackgroundOpacity!=='';
  Object.entries(TITLE_DEFAULTS).forEach(([k,v])=>{
    if(c[k]===undefined||c[k]===null||c[k]==='')c[k]=v;
  });
  if(c.titleRole==='final_card'&&!hadCanvasOpacity)c.canvasBackgroundOpacity=1;
  if(!c.text)c.text=c.label||'Nouveau titre';
  return c;
}

function titleFontStack(value){
  if(value==='serif')return 'Georgia, "Times New Roman", serif';
  if(value==='mono')return 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
  return 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif';
}

function hexToRgba(hex,alpha){
  const clean=String(hex||'#000000').replace('#','');
  const value=parseInt(clean,16);
  if(!Number.isFinite(value))return `rgba(0,0,0,${alpha})`;
  return `rgba(${(value>>16)&255},${(value>>8)&255},${value&255},${alpha})`;
}

function applyViewerTitleStyle(title){
  const el=$('#viewerTitle');
  const backdrop=$('#viewerTitleBackdrop');
  if(!el)return;
  if(!title){
    el.classList.remove('show');
    el.removeAttribute('style');
    if(backdrop){
      backdrop.classList.remove('show');
      backdrop.removeAttribute('style');
    }
    return;
  }
  normalizeTitleClip(title);
  const stage=$('#viewer');
  const stageHeight=Math.max(1,stage?.clientHeight||540);
  const stageWidth=Math.max(1,stage?.clientWidth||960);
  const isFinal=title.titleRole==='final_card';
  const localTime=Math.max(0,playhead-(+title.start||0));
  const blackTail=Math.max(0,+title.blackTailSeconds||0);
  const inBlackTail=isFinal&&blackTail>0&&localTime>=Math.max(0,(+title.duration||0)-blackTail);
  if(backdrop){
    backdrop.classList.toggle('show',isFinal);
    backdrop.style.background=isFinal?hexToRgba(title.canvasBackgroundColor,+title.canvasBackgroundOpacity):'transparent';
  }
  el.classList.toggle('show',!inBlackTail);
  el.textContent=inBlackTail?'':(title.text||title.label||'');
  el.style.left=(+title.positionX*100)+'%';
  el.style.top=(+title.positionY*100)+'%';
  el.style.bottom='auto';
  el.style.transform='translate(-50%,-50%)';
  el.style.width=(+title.boxWidth*100)+'%';
  el.style.fontFamily=titleFontStack(title.fontFamily);
  el.style.fontSize=Math.max(8,(+title.fontSize/1080)*stageHeight)+'px';
  el.style.fontWeight=String(title.fontWeight);
  el.style.textAlign=title.textAlign;
  el.style.color=title.color;
  el.style.opacity=String(title.opacity);
  el.style.background=hexToRgba(title.backgroundColor,+title.backgroundOpacity);
  el.style.padding=Math.max(0,+title.padding*stageWidth)+'px';
  el.style.borderRadius=Math.max(0,+title.cornerRadius*stageWidth)+'px';
  el.style.textShadow=+title.backgroundOpacity>.4?'none':'0 2px 16px rgba(0,0,0,.85)';
  el.style.whiteSpace='pre-wrap';
  el.style.lineHeight='1.12';
  el.style.pointerEvents='none';
}

syncTitle=function(){
  applyViewerTitleStyle(activeTitle());
};

function titleInspectorMarkup(c){
  normalizeTitleClip(c);
  const isFinal=c.titleRole==='final_card';
  const finalCardControls=isFinal?`
      <div class="final-card-chip">CARTON FINAL · FIN DE TIMELINE</div>
      <div class="form-grid">
        <div class="row"><label>Fond canvas</label><input id="titleCanvasBackgroundColor" type="color" value="${c.canvasBackgroundColor}"></div>
        <div class="row"><label>Fond canvas %</label><input id="titleCanvasBackgroundOpacity" type="number" min="0" max="100" step="1" value="${Math.round(+c.canvasBackgroundOpacity*100)}"></div>
        <div class="row full"><label>Noir / fond seul final (s)</label><input id="titleBlackTailSeconds" type="number" min="0" max="${Math.max(0,(+c.duration||0)-.1)}" step=".05" value="${+c.blackTailSeconds||0}"></div>
      </div>
      <div class="hint">Le fond canvas couvre l’image. Pendant le noir final, seul ce fond reste visible ; le texte est masqué sans créer de clip séparé.</div>`:'';
  return `
    <div class="inspector-section title-style-section">
      <div class="inspector-section-title">${isFinal?'CARTON FINAL':'TITRE / OVERLAY'}</div>
      ${finalCardControls}
      <div class="row full"><label>Texte</label><textarea id="titleText" rows="3">${c.text||''}</textarea></div>
      <div class="form-grid">
        <div class="row"><label>Preset</label><select id="titlePreset"><option value="center" ${c.titlePreset==='center'?'selected':''}>Centre</option><option value="lower_third" ${c.titlePreset==='lower_third'?'selected':''}>Lower third</option><option value="top" ${c.titlePreset==='top'?'selected':''}>Haut</option><option value="custom" ${c.titlePreset==='custom'?'selected':''}>Personnalisé</option></select></div>
        <div class="row"><label>Famille</label><select id="titleFontFamily"><option value="sans" ${c.fontFamily==='sans'?'selected':''}>Sans</option><option value="serif" ${c.fontFamily==='serif'?'selected':''}>Serif</option><option value="mono" ${c.fontFamily==='mono'?'selected':''}>Mono</option></select></div>
        <div class="row"><label>Taille</label><input id="titleFontSize" type="number" min="12" max="240" step="1" value="${c.fontSize}"></div>
        <div class="row"><label>Graisse</label><select id="titleFontWeight">${[100,200,300,400,500,600,700,800,900].map(w=>`<option value="${w}" ${+c.fontWeight===w?'selected':''}>${w}</option>`).join('')}</select></div>
        <div class="row"><label>Alignement</label><select id="titleTextAlign"><option value="left" ${c.textAlign==='left'?'selected':''}>Gauche</option><option value="center" ${c.textAlign==='center'?'selected':''}>Centre</option><option value="right" ${c.textAlign==='right'?'selected':''}>Droite</option></select></div>
        <div class="row"><label>Largeur %</label><input id="titleBoxWidth" type="number" min="10" max="100" step="1" value="${Math.round(+c.boxWidth*100)}"></div>
        <div class="row"><label>Position X %</label><input id="titlePositionX" type="number" min="0" max="100" step="1" value="${Math.round(+c.positionX*100)}"></div>
        <div class="row"><label>Position Y %</label><input id="titlePositionY" type="number" min="0" max="100" step="1" value="${Math.round(+c.positionY*100)}"></div>
        <div class="row"><label>Couleur</label><input id="titleColor" type="color" value="${c.color}"></div>
        <div class="row"><label>Opacité %</label><input id="titleOpacity" type="number" min="0" max="100" step="1" value="${Math.round(+c.opacity*100)}"></div>
        <div class="row"><label>Fond</label><input id="titleBackgroundColor" type="color" value="${c.backgroundColor}"></div>
        <div class="row"><label>Fond opacité %</label><input id="titleBackgroundOpacity" type="number" min="0" max="100" step="1" value="${Math.round(+c.backgroundOpacity*100)}"></div>
        <div class="row"><label>Marge %</label><input id="titlePadding" type="number" min="0" max="20" step=".5" value="${(+c.padding*100).toFixed(1)}"></div>
        <div class="row"><label>Arrondi %</label><input id="titleCornerRadius" type="number" min="0" max="20" step=".5" value="${(+c.cornerRadius*100).toFixed(1)}"></div>
      </div>
      <div class="hint">Coordonnées et dimensions normalisées : l’overlay reste proportionnel au format de sortie. Familles génériques pour éviter une dépendance à une police locale.</div>
    </div>`;
}

function readTitleInspector(c){
  const preset=$('#titlePreset')?.value||'center';
  const presetPositions={center:[.5,.5],lower_third:[.5,.82],top:[.5,.16]};
  const next={...c,
    text:($('#titleText')?.value||'').trim(),
    titlePreset:preset,
    fontFamily:$('#titleFontFamily')?.value||'sans',
    fontSize:+$('#titleFontSize')?.value||64,
    fontWeight:+$('#titleFontWeight')?.value||700,
    textAlign:$('#titleTextAlign')?.value||'center',
    positionX:(+$('#titlePositionX')?.value||0)/100,
    positionY:(+$('#titlePositionY')?.value||0)/100,
    boxWidth:(+$('#titleBoxWidth')?.value||80)/100,
    color:$('#titleColor')?.value||'#FFFFFF',
    opacity:(+$('#titleOpacity')?.value||0)/100,
    backgroundColor:$('#titleBackgroundColor')?.value||'#000000',
    backgroundOpacity:(+$('#titleBackgroundOpacity')?.value||0)/100,
    padding:(+$('#titlePadding')?.value||0)/100,
    cornerRadius:(+$('#titleCornerRadius')?.value||0)/100,
    titleRole:c.titleRole||'overlay',
    canvasBackgroundColor:$('#titleCanvasBackgroundColor')?.value||c.canvasBackgroundColor||'#000000',
    canvasBackgroundOpacity:$('#titleCanvasBackgroundOpacity')?Math.max(0,Math.min(1,(+$('#titleCanvasBackgroundOpacity').value||0)/100)):(+c.canvasBackgroundOpacity||0),
    blackTailSeconds:$('#titleBlackTailSeconds')?Math.max(0,+$('#titleBlackTailSeconds').value||0):(+c.blackTailSeconds||0),
  };
  if(preset!=='custom'&&presetPositions[preset]){
    next.positionX=presetPositions[preset][0];
    next.positionY=presetPositions[preset][1];
  }
  return next;
}

const _v0231RenderInspector=renderInspector;
renderInspector=function(){
  _v0231RenderInspector();
  const c=getClip(selectedClip);
  if(!c||c.track!=='titles')return;
  normalizeTitleClip(c);
  const root=$('#inspector');
  [...root.querySelectorAll('.inspector-section')].forEach(section=>{
    const title=section.querySelector('.inspector-section-title')?.textContent?.trim();
    if(title==='TEXTE')section.remove();
  });
  const action=root.querySelector('.inspector-section:last-child');
  if(action)action.insertAdjacentHTML('beforebegin',titleInspectorMarkup(c));
  else root.insertAdjacentHTML('beforeend',titleInspectorMarkup(c));
  const refresh=()=>{
    const preview=readTitleInspector(c);
    applyViewerTitleStyle(preview);
  };
  root.querySelectorAll('.title-style-section input,.title-style-section select,.title-style-section textarea').forEach(el=>el.addEventListener('input',refresh));
};

const _v0231ApplyEdit=applyEdit;
applyEdit=function(){
  const c=getClip(selectedClip);
  if(!c||c.track!=='titles')return _v0231ApplyEdit();
  const next=readTitleInspector(c);
  next.track=$('#ct')?.value||c.track;
  next.start=+$('#cs')?.value;
  next.duration=+$('#cd')?.value;
  if(!next.text){toast('Le texte du titre ne peut pas être vide',true);return}
  if(next.fontSize<12||next.fontSize>240){toast('Taille titre invalide',true);return}
  if(next.positionX<0||next.positionX>1||next.positionY<0||next.positionY>1){toast('Position titre invalide',true);return}
  if(next.titleRole==='final_card'&&next.blackTailSeconds>=next.duration){toast('Le noir final doit être plus court que le carton',true);return}
  const err=validate(next,c.id);
  if(err){toast(err,true);return}
  Object.assign(c,next,{label:next.text.split(/\n/)[0].slice(0,48)||'Titre'});
  renderTracks();
  setPlayhead(c.start);
  toast(next.titleRole==='final_card'?'Carton final mis à jour':'Titre / overlay mis à jour');
};

addTitle=function(){
  const start=Math.max(0,Math.min(DURATION-2,playhead));
  const c={
    id:'t'+Date.now(),
    track:'titles',
    label:'Nouveau titre',
    text:'Nouveau titre',
    start:snapTime(start),
    duration:2,
    ...TITLE_DEFAULTS,
  };
  while(validate(c)&&c.start+snapValue()+c.duration<=DURATION)c.start=snapTime(c.start+snapValue());
  const err=validate(c);
  if(err){toast(err,true);return}
  clips.push(c);
  selectedClip=c.id;
  setViewerMode('program',{silent:true});
  renderTracks();
  setPlayhead(c.start);
  toast('Titre / overlay ajouté');
};

addFinalCard=function(){
  const duration=Math.min(3.5,DURATION);
  const start=snapTime(Math.max(0,DURATION-duration));
  const c={
    id:'fc'+Date.now(),
    track:'titles',
    label:'Carton final',
    text:'Carton final',
    start,
    duration,
    ...TITLE_DEFAULTS,
    titleRole:'final_card',
    titlePreset:'center',
    fontSize:56,
    fontWeight:600,
    positionX:.5,
    positionY:.5,
    boxWidth:.78,
    backgroundOpacity:0,
    padding:0,
    cornerRadius:0,
    canvasBackgroundColor:'#000000',
    canvasBackgroundOpacity:1,
    blackTailSeconds:Math.min(.75,Math.max(0,duration-.2)),
  };
  const err=validate(c);
  if(err){
    toast('Impossible de placer le carton final : '+err,true);
    return;
  }
  clips.push(c);
  selectedClip=c.id;
  setViewerMode('program',{silent:true});
  renderTracks();
  setPlayhead(c.start);
  toast('Carton final ajouté · texte à personnaliser');
};

window.addEventListener('resize',()=>syncTitle());


if(typeof commands!=='undefined'&&!commands.some(c=>c.label==='Titre · Ajouter un carton final')){
  commands.splice(
    Math.min(commands.length,18),
    0,
    {
      label:'Titre · Ajouter un carton final',
      hint:'',
      keywords:'titre final card end slate credits noir fin',
      run:()=>addFinalCard(),
    }
  );
}
