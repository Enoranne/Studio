(() => {
  let activeFilter = "all";
  let detailEntry = null;

  const kindLabels = {
    action: "ACTION",
    goto: "ALLER À",
    help: "AIDE",
    resource: "RESSOURCE",
  };

  const universalEntries = [
    {kind:"action",domain:"project",label:"Espace · Assemble",hint:"1",keywords:"workspace media browser assembler organiser",summary:"Ouvrir l’espace de préparation des médias.",run:()=>setWorkspace("assemble")},
    {kind:"action",domain:"editorial",label:"Espace · Edit",hint:"2",keywords:"workspace montage timeline edit monter",summary:"Revenir à l’espace principal de montage.",run:()=>setWorkspace("edit")},
    {kind:"action",domain:"video",label:"Espace · Review",hint:"3",keywords:"workspace lecture review verifier visionner",summary:"Passer en espace de revue et lecture.",run:()=>setWorkspace("review")},
    {kind:"action",domain:"video",label:"Viewer · Source",hint:"P",keywords:"source rush viewer original",summary:"Afficher le média source sélectionné.",run:()=>setViewerMode("source")},
    {kind:"action",domain:"video",label:"Viewer · Program",hint:"P",keywords:"program timeline montage viewer",summary:"Afficher le montage sous le playhead.",run:()=>setViewerMode("program")},
    {kind:"action",domain:"video",label:"Focus · Viewer",hint:"~",keywords:"fullscreen viewer cinema plein ecran",summary:"Agrandir le Viewer.",run:()=>setFocusPane("viewer")},
    {kind:"action",domain:"editorial",label:"Focus · Timeline",hint:"~",keywords:"fullscreen timeline montage plein ecran",summary:"Agrandir la Timeline.",run:()=>setFocusPane("timeline")},
    {kind:"action",domain:"video",label:"Focus · Browser",hint:"~",keywords:"fullscreen browser rushes media",summary:"Agrandir le Browser.",run:()=>setFocusPane("browser")},
    {kind:"action",domain:"project",label:"Focus · Inspecteur",hint:"~",keywords:"fullscreen inspector inspecteur",summary:"Agrandir l’Inspecteur.",run:()=>setFocusPane("inspector")},
    {kind:"action",domain:"video",label:"Panneau · Browser",hint:"B",keywords:"toggle media browser afficher masquer",summary:"Afficher ou masquer le Browser.",run:toggleBrowser},
    {kind:"action",domain:"project",label:"Panneau · Inspecteur",hint:"I",keywords:"toggle inspector inspecteur afficher masquer",summary:"Afficher ou masquer l’Inspecteur.",run:toggleInspector},
    {kind:"action",domain:"editorial",label:"Panneau · Index",hint:"",keywords:"toggle index decisions locks clips",summary:"Afficher ou masquer l’Index de timeline.",run:toggleIndex},
    {kind:"action",domain:"editorial",label:"Montage · Undo",hint:"⌘Z",keywords:"undo annuler checkpoint retour",summary:"Restaurer le dernier checkpoint.",run:()=>undoLastEdit()},
    {kind:"action",domain:"project",label:"Montage · Enregistrer",hint:"",keywords:"save timeline enregistrer sauvegarder",summary:"Enregistrer la Storyline de travail.",run:()=>document.querySelector("#saveBackendBtn")?.click()},
    {kind:"action",domain:"project",label:"Montage · Publier",hint:"",keywords:"publish version publier version",summary:"Créer une version publiée depuis le montage validé.",run:()=>typeof publishVersion==="function"&&publishVersion()},
    {kind:"action",domain:"video",label:"Viewer · Overlays",hint:"",keywords:"overlay timecode mix in out viewer",summary:"Choisir les informations affichées sur le Viewer.",run:toggleOverlayMenu},
    {kind:"action",domain:"editorial",label:"Editorial · Ajouter un marqueur",hint:"M",keywords:"marker marqueur note decision beat vigilance",summary:"Ajouter un repère sans modifier le montage.",run:()=>typeof openMarkerComposer==="function"&&openMarkerComposer()},
    {kind:"action",domain:"editorial",label:"Editorial · Trouver des alternatives",hint:"",keywords:"source selector alternatives prise rush remplacer plan",summary:"Comparer d’autres prises avant décision.",run:()=>typeof openSourceSelector==="function"&&openSourceSelector()},
    {kind:"action",domain:"video",label:"Média · Analyser le catalogue",hint:"",keywords:"analyze analyse ffmpeg filmstrip media intelligence rushes",summary:"Calculer les informations techniques et visuelles locales.",run:()=>typeof analyzeMediaCatalog==="function"&&analyzeMediaCatalog()},
    {kind:"action",domain:"video",label:"Média · Prises proches",hint:"",keywords:"similar take duplicate proche visual prises similaires",summary:"Chercher des prises visuellement proches.",run:()=>typeof openSimilarTakes==="function"&&openSimilarTakes()},
    {kind:"action",domain:"video",label:"Vision · Fenêtres IN/OUT",hint:"",keywords:"scene cut rupture source in out editorial window fenetre",summary:"Proposer des fenêtres SOURCE entre ruptures visuelles.",run:()=>typeof openEditorialWindows==="function"&&openEditorialWindows()},
    {kind:"action",domain:"video",label:"Vision · Référence ciblée",hint:"",keywords:"frame roi zone reference character prop decor look reference ciblee",summary:"Créer une référence visuelle sur un frame ou une zone.",run:()=>typeof openTargetedReferenceManager==="function"&&openTargetedReferenceManager()},
    {kind:"action",domain:"video",label:"Vision · Analyser le rush",hint:"",keywords:"semantic clip local vision analyse embedding",summary:"Calculer le profil Semantic Vision du rush.",run:()=>typeof analyzeSemanticSelected==="function"&&analyzeSemanticSelected(false)},
    {kind:"action",domain:"editorial",label:"Vision · Proposer continuité",hint:"",keywords:"semantic continuity character prop decor look raccord",summary:"Comparer des preuves de continuité visuelle.",run:()=>typeof openSemanticContinuity==="function"&&openSemanticContinuity()},
    {kind:"action",domain:"audio",label:"Audio · Ajouter un point de volume",hint:"",keywords:"audio automation keyframe gain volume point",summary:"Ajouter une keyframe de volume non destructive.",run:()=>typeof addAudioAutomationPoint==="function"&&addAudioAutomationPoint()},
    {kind:"action",domain:"audio",label:"Audio · Effacer automation",hint:"",keywords:"audio clear automation volume supprimer",summary:"Retirer l’automation de volume du clip.",run:()=>typeof clearAudioAutomation==="function"&&clearAudioAutomation()},
    {kind:"action",domain:"audio",label:"Audio · Analyser loudness",hint:"",keywords:"lufs loudness true peak analyse audio niveau",summary:"Mesurer LUFS, true peak et silences.",run:()=>typeof analyzeSelectedAudioLoudness==="function"&&analyzeSelectedAudioLoudness()},
    {kind:"action",domain:"audio",label:"Audio · Normaliser",hint:"",keywords:"normalize normaliser lufs gain niveau",summary:"Calculer un ajustement de gain proposé.",run:()=>typeof openNormalizationProposal==="function"&&openNormalizationProposal()},
    {kind:"action",domain:"audio",label:"Audio · Vérifier clipping",hint:"",keywords:"clipping true peak headroom saturation",summary:"Évaluer le risque de dépassement par clip.",run:()=>typeof openClippingReport==="function"&&openClippingReport()},
    {kind:"action",domain:"audio",label:"Audio · Ducking VO",hint:"",keywords:"ducking voice vo music musique dialogue",summary:"Proposer une baisse de musique sous VO/dialogue.",run:()=>typeof openDuckingProposal==="function"&&openDuckingProposal()},
    {kind:"action",domain:"audio",label:"Audio · Master Check",hint:"",keywords:"master delivery lufs true peak export rapport mix",summary:"Mesurer le mix rendu avant livraison.",run:()=>typeof openMasterCheck==="function"&&openMasterCheck()},
    {kind:"action",domain:"delivery",label:"Production · Readiness",hint:"",keywords:"production readiness preflight tesseract delivery validation pret",summary:"Vérifier l’état réel de la chaîne de production.",run:()=>typeof openProductionReadiness==="function"&&openProductionReadiness()},
    {kind:"action",domain:"editorial",label:"Editorial · Ouvrir Agent",hint:"",keywords:"agent ai ia transcript proposition edl vo image",summary:"Ouvrir Transcript Intelligence et les propositions éditoriales.",run:()=>typeof openEditorialAgent==="function"&&openEditorialAgent()},
    {kind:"action",domain:"delivery",label:"Delivery · Export",hint:"",keywords:"export delivery festival social prores h264 livrer",summary:"Ouvrir le Delivery Center.",run:()=>typeof openDeliveryCenter==="function"&&openDeliveryCenter()},

    {kind:"goto",domain:"video",label:"Aller à · Browser vidéo",keywords:"menu browser video rushes media aller",summary:"Afficher le catalogue vidéo.",run:()=>{document.querySelector('[data-workspace="edit"]')?.click();document.querySelector('.libtab[data-lib="video"]')?.click();}},
    {kind:"goto",domain:"audio",label:"Aller à · Browser audio",keywords:"menu browser audio sons musique vo aller",summary:"Afficher le catalogue audio.",run:()=>{document.querySelector('[data-workspace="edit"]')?.click();document.querySelector('.libtab[data-lib="audio"]')?.click();}},
    {kind:"goto",domain:"project",label:"Aller à · Canon & Locks",keywords:"menu canon locks hard soft open regles aller",summary:"Ouvrir les règles Canon et Locks.",run:()=>document.querySelector('.nav-tab[data-view="canon"]')?.click()},
    {kind:"goto",domain:"project",label:"Aller à · Versions",keywords:"menu historique versions publier aller",summary:"Ouvrir l’historique des versions.",run:()=>document.querySelector('.nav-tab[data-view="versions"]')?.click()},
    {kind:"goto",domain:"editorial",label:"Aller à · Editorial Agent",keywords:"menu agent transcript vo image edl proposition aller",summary:"Ouvrir le panneau Editorial Agent.",run:()=>typeof openEditorialAgent==="function"&&openEditorialAgent()},
    {kind:"goto",domain:"delivery",label:"Aller à · Delivery",keywords:"menu export delivery festival social aller",summary:"Ouvrir le centre de livraison.",run:()=>typeof openDeliveryCenter==="function"&&openDeliveryCenter()},
    {kind:"goto",domain:"delivery",label:"Aller à · Production Readiness",keywords:"menu readiness production tesseract aller",summary:"Ouvrir le diagnostic de production.",run:()=>typeof openProductionReadiness==="function"&&openProductionReadiness()},

    {kind:"help",domain:"editorial",label:"Aide · Analyse, proposition ou application ?",keywords:"faq aide ia ai analyse proposer appliquer difference",summary:"Comprendre quand PISTE observe, suggère ou modifie réellement.",body:"PISTE sépare volontairement trois niveaux. Une analyse lit l’état du projet. Une proposition fabrique une alternative virtuelle. Une application modifie la Storyline seulement après votre confirmation et les contrôles de sécurité.",points:["ANALYSE : aucun montage modifié.","PROPOSITION : EDL ou réglage virtuel, encore sans effet.","APPLICATION : checkpoint + locks + validation, puis transaction Storyline."]},
    {kind:"help",domain:"project",label:"Aide · À quoi sert la Storyline ?",keywords:"faq aide storyline magnetic magnetique timeline montage",summary:"Le fil vidéo principal et source de vérité du montage.",body:"La Storyline est le fil vidéo principal. En mode magnétique, les plans restent contigus et les éléments connectés suivent leur parent. PISTE valide ses contraintes avant chaque modification persistante.",points:["Les rushes source ne sont jamais réécrits.","VO, titres et SFX peuvent être connectés à un plan.","Undo repose sur des checkpoints persistants."]},
    {kind:"help",domain:"project",label:"Aide · HARD, SOFT et OPEN Locks",keywords:"faq aide hard soft open lock verrou canon",summary:"Comprendre les niveaux de protection du projet.",body:"Les locks encadrent les opérations autorisées sur une zone. HARD protège strictement, SOFT demande une décision explicite et OPEN laisse travailler normalement.",points:["HARD : une opération interdite est refusée.","SOFT : avertissement ou acquittement explicite.","OPEN : aucune protection supplémentaire."]},
    {kind:"help",domain:"transcript",label:"Aide · Transcrire une VO",keywords:"faq aide transcript transcription vo voix elevenlabs scribe",summary:"Choisir la piste puis créer un transcript synchronisé.",body:"Sélectionnez la source VO, analysez ses pistes, choisissez explicitement la piste de transcription puis lancez ou importez le transcript. Un service externe n’est contacté qu’après consentement explicite.",points:["Le transcript conserve timestamps et locuteurs lorsqu’ils existent.","L’import local/externe est possible sans appel réseau.","Le fichier audio source reste inchangé."]},
    {kind:"help",domain:"editorial",label:"Aide · VO vers image",keywords:"faq aide vo image voice visual phrase intention plans v027",summary:"Utiliser une phrase de VO pour trouver des images candidates.",body:"V0.27 relie une phrase ou une intention à des fenêtres visuelles. Le score sert à trier et expliquer les candidats ; il ne choisit jamais artistiquement le plan à votre place.",points:["Phrase/intention → métadonnées + vision + Favorite/Reject.","Comparer et prévisualiser les plans candidats.","Créer ensuite une EDL virtuelle, à valider humainement."]},
    {kind:"help",domain:"audio",label:"Aide · Contrôler le niveau audio",keywords:"faq aide lufs true peak master check loudness son niveau",summary:"Distinguer analyse source, gain proposé et Master Check.",body:"L’analyse source mesure un média. La normalisation propose un gain de clip. Le Master Check mesure le mix réellement rendu : ce sont trois étapes différentes.",points:["Aucun fichier source n’est normalisé destructivement.","Le limiteur master reste opt-in.","Le Master Check peut devenir STALE si le mix change."]},
    {kind:"help",domain:"delivery",label:"Aide · Préparer un export festival",keywords:"faq aide festival export delivery prores h264 master",summary:"Passer du montage validé au fichier de livraison.",body:"Publiez d’abord une version, contrôlez Readiness et le Master Check, puis choisissez un preset Delivery adapté au diffuseur. Le preset reste un profil technique, pas une norme universelle.",points:["Vérifier titres, cadrage et audio avant export.","FIT préserve l’image ; FILL/CROP nécessite un choix explicite.","Conserver le rapport de livraison avec le master."]},

    {kind:"resource",domain:"project",label:"Ressource · Raccourcis essentiels",keywords:"ressources raccourcis clavier keyboard shortcuts cmd ctrl",summary:"Les gestes principaux de navigation et montage.",body:"Les raccourcis accélèrent l’usage sans rendre la souris obligatoire.",points:["1 / 2 / 3 : Assemble / Edit / Review","⌘/Ctrl + K : recherche universelle","~ : Focus du panneau actif","F : Favorite · X : Reject","⌘/Ctrl + Z : Undo"]},
    {kind:"resource",domain:"project",label:"Ressource · Workflow PISTE",keywords:"ressources workflow flux piste canon storyline tesseract critic delivery",summary:"Le chemin recommandé du projet jusqu’au master.",body:"PISTE sépare intention, montage, rendu et contrôle pour conserver une trace claire des décisions.",points:["Canon + médias → Storyline","Intelligence → propositions → validation humaine","Version publiée → Tesseract","Master rendu → Critic / Master Check","Delivery → rapport de livraison"]},
    {kind:"resource",domain:"project",label:"Ressource · Glossaire PISTE",keywords:"ressources glossaire definitions storyline edl canon critic tesseract",summary:"Retrouver rapidement les notions propres au logiciel.",body:"Storyline = fil vidéo principal ; EDL virtuelle = proposition non appliquée ; Canon = règles du projet ; Master Critic = diagnostic du rendu ; Tesseract = moteur externe de rendu/authoring.",points:["Favorite / Reject : signal éditorial humain.","Semantic Vision : preuves visuelles locales.","Checkpoint : état restaurable avant modification.","Readiness : diagnostic de la chaîne de production."]},
    {kind:"resource",domain:"project",label:"Ressource · Principes de sécurité",keywords:"ressources securite non destructif source master humain locks",summary:"Les garanties qui encadrent les automatisations.",body:"PISTE Studio reste non destructif et humain-dans-la-boucle.",points:["Sources et master protégés.","Pas d’Apply silencieux pour les propositions éditoriales.","Réseau externe opt-in pour transcription/modèles.","Locks et checkpoints contrôlés avant mutation."]},
  ];

  function normalize(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  }

  function score(entry, query) {
    const q = normalize(query);
    const context = window.PisteContext?.infer?.() || window.PisteState?.get("contextDomain") || "video";
    if (!q) return entry.domain === context ? 8 : 0;
    const label = normalize(entry.label);
    const hay = normalize([
      entry.label,
      entry.keywords,
      entry.summary,
      entry.body,
      (entry.points || []).join(" "),
    ].join(" "));
    if (label === q) return 140;
    if (label.startsWith(q)) return 115;
    if (label.includes(q)) return 95;
    if (hay.includes(q)) return 80;
    const tokens = q.split(/\s+/).filter(Boolean);
    const matched = tokens.filter(token => hay.includes(token)).length;
    if (!matched) return -1;
    if (matched === tokens.length) return 55 + matched * 5 + (entry.domain === context ? 5 : 0);
    return matched / tokens.length >= 0.6 ? 20 + matched * 3 : -1;
  }

  window.filteredCommands = function filteredCommands() {
    const query = document.getElementById("commandSearch")?.value || "";
    return universalEntries
      .filter(entry => activeFilter === "all" || entry.kind === activeFilter)
      .map((entry, order) => ({ entry, order, score: score(entry, query) }))
      .filter(row => row.score >= 0)
      .sort((a, b) => b.score - a.score || a.order - b.order)
      .map(row => row.entry);
  };

  function renderDetail(entry) {
    const root = document.getElementById("commandResults");
    if (!root) return;
    const points = (entry.points || []).map(item => "<li>" + item + "</li>").join("");
    root.innerHTML =
      '<div class="command-detail" data-domain="' + (entry.domain || "project") + '">' +
        '<div class="command-detail-head">' +
          '<div><span class="command-detail-kind">' + (kindLabels[entry.kind] || entry.kind) + '</span><h3>' + entry.label.replace(/^[^·]+·\s*/, "") + '</h3></div>' +
          '<button class="command-back" type="button" id="commandBack">← Résultats</button>' +
        '</div>' +
        '<p>' + (entry.body || entry.summary || "") + '</p>' +
        (points ? "<ul>" + points + "</ul>" : "") +
        (entry.run ? '<div class="command-detail-actions"><button class="btn primary" id="commandRelatedAction">Ouvrir l’outil associé</button></div>' : "") +
      "</div>";
    document.getElementById("commandBack").onclick = () => {
      detailEntry = null;
      window.renderCommandPalette();
    };
    const related = document.getElementById("commandRelatedAction");
    if (related) related.onclick = () => {
      window.closeCommandPalette();
      entry.run();
    };
    window.PisteHelp?.narrate(entry.summary || entry.label);
  }

  window.renderCommandPalette = function renderCommandPalette() {
    const root = document.getElementById("commandResults");
    if (!root) return;
    document.querySelectorAll(".command-filters button").forEach(button => {
      button.classList.toggle("active", button.dataset.commandFilter === activeFilter);
    });
    if (detailEntry) {
      renderDetail(detailEntry);
      return;
    }
    const list = window.filteredCommands();
    if (commandIndex >= list.length) commandIndex = Math.max(0, list.length - 1);
    let lastKind = null;
    let markup = "";
    list.forEach((entry, index) => {
      if (entry.kind !== lastKind) {
        markup += '<div class="command-group-title">' + (kindLabels[entry.kind] || entry.kind) + "</div>";
        lastKind = entry.kind;
      }
      markup +=
        '<button class="command-item ' + (index === commandIndex ? "active" : "") + '" data-command-index="' + index + '" data-domain="' + (entry.domain || "project") + '">' +
          '<span class="command-item-kind">' + (kindLabels[entry.kind] || entry.kind) + "</span>" +
          '<span class="command-item-copy"><b>' + entry.label + "</b><small>" + (entry.summary || "") + "</small></span>" +
          (entry.hint ? "<kbd>" + entry.hint + "</kbd>" : '<i class="command-match-domain"></i>') +
        "</button>";
    });
    root.innerHTML = markup || '<div class="command-empty">Aucun résultat. Essaie « audio », « export », « VO » ou « locks ».</div>';
    root.querySelectorAll(".command-item").forEach(element => {
      element.onclick = () => window.executeCommand(Number(element.dataset.commandIndex));
    });
  };

  window.openCommandPalette = function openCommandPalette(seed = "", filter = "all") {
    const palette = document.getElementById("commandPalette");
    if (!palette) return;
    palette.hidden = false;
    commandIndex = 0;
    detailEntry = null;
    activeFilter = ["all", "action", "goto", "help", "resource"].includes(filter) ? filter : "all";
    document.getElementById("commandSearch").value = seed || "";
    window.renderCommandPalette();
    requestAnimationFrame(() => document.getElementById("commandSearch").focus());
  };

  window.closeCommandPalette = function closeCommandPalette() {
    const palette = document.getElementById("commandPalette");
    if (palette) palette.hidden = true;
    detailEntry = null;
  };

  window.executeCommand = function executeCommand(index) {
    const list = window.filteredCommands();
    const entry = list[index];
    if (!entry) return;
    if (entry.kind === "help" || entry.kind === "resource") {
      detailEntry = entry;
      renderDetail(entry);
      return;
    }
    window.closeCommandPalette();
    entry.run?.();
  };

  document.querySelectorAll(".command-filters button").forEach(button => {
    button.onclick = () => {
      activeFilter = button.dataset.commandFilter || "all";
      commandIndex = 0;
      detailEntry = null;
      window.renderCommandPalette();
      document.getElementById("commandSearch").focus();
    };
  });

  const search = document.getElementById("commandSearch");
  search.oninput = () => {
    commandIndex = 0;
    detailEntry = null;
    window.renderCommandPalette();
  };
  search.onkeydown = event => {
    if (detailEntry) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        detailEntry = null;
        window.renderCommandPalette();
      }
      return;
    }
    const list = window.filteredCommands();
    if (event.key === "ArrowDown") {
      event.preventDefault();
      commandIndex = Math.min(list.length - 1, commandIndex + 1);
      window.renderCommandPalette();
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      commandIndex = Math.max(0, commandIndex - 1);
      window.renderCommandPalette();
    }
    if (event.key === "Enter") {
      event.preventDefault();
      window.executeCommand(commandIndex);
    }
    if (event.key === "Escape") {
      event.preventDefault();
      window.closeCommandPalette();
    }
  };

  document.getElementById("universalSearchBtn")?.addEventListener("click", () => window.openCommandPalette());

  window.PisteSearch = {
    open: (seed = "", filter = "all") => window.openCommandPalette(seed, filter),
    search: (query, filter = "all") => window.openCommandPalette(query, filter),
    entries: () => universalEntries.map(({ run, ...entry }) => ({ ...entry })),
  };
})();
