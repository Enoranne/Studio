(() => {
  const STORAGE_KEY = "piste.ui.helpMode";
  const VALID = new Set(["guided", "minimal", "off"]);
  const COPY = [
    [/scanner/i, "Scanne les dossiers du projet et met le catalogue à jour. Aucun média source n’est modifié."],
    [/analyser/i, "Analyse les médias localement pour préparer filmstrips, informations techniques et intelligence éditoriale."],
    [/rushes/i, "Associe les fichiers vidéo locaux au catalogue du projet."],
    [/^audio$/i, "Passe à la bibliothèque audio et aux outils de mixage."],
    [/preview/i, "Crée une prévisualisation depuis la version de travail sans altérer les sources."],
    [/readiness/i, "Vérifie l’état réel du projet, de Tesseract et de la chaîne de livraison."],
    [/agent/i, "Ouvre l’Editorial Agent. Il analyse et propose ; la Storyline ne change qu’après validation explicite."],
    [/export/i, "Ouvre Delivery pour contrôler puis produire le fichier de sortie."],
    [/undo/i, "Restaure le dernier checkpoint disponible."],
    [/enregistrer/i, "Enregistre la Storyline de travail actuelle."],
    [/publier/i, "Crée une version publiée à partir de la Storyline validée."],
    [/tesseract/i, "Prépare ou exécute la chaîne Tesseract sur une version publiée."],
    [/\+ titre/i, "Ajoute un titre éditable à la timeline."],
    [/carton final/i, "Ajoute un carton spécialisé aligné sur la fin du montage."],
    [/\+ vo/i, "Ajoute une source voix off sans modifier son fichier original."],
    [/\+ music/i, "Ajoute une source musicale sur sa piste dédiée."],
    [/\+ sfx/i, "Ajoute un effet sonore sur sa piste dédiée."],
    [/marker/i, "Ajoute un repère éditorial sans modifier le montage."],
    [/transcrire/i, "Prépare un transcript. Un fournisseur externe n’est utilisé qu’après consentement explicite."],
    [/edl virtuelle|proposer montage/i, "Crée une proposition virtuelle. La Storyline reste inchangée jusqu’à Apply."],
    [/valider et appliquer|appliquer/i, "Crée un checkpoint, vérifie les locks puis applique uniquement après confirmation."],
    [/master critic/i, "Analyse le rendu final et signale les points à revoir sans corriger automatiquement."],
  ];

  function currentMode() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return VALID.has(saved) ? saved : "guided";
  }

  function setMode(mode) {
    const clean = VALID.has(mode) ? mode : "guided";
    localStorage.setItem(STORAGE_KEY, clean);
    document.body.dataset.helpMode = clean;
    window.PisteState?.set("helpMode", clean);
    document.querySelectorAll('input[name="helpMode"]').forEach(input => {
      input.checked = input.value === clean;
    });
    const label = clean === "guided" ? "Guidée" : clean === "minimal" ? "Minimale" : "Désactivée";
    const button = document.getElementById("helpModeBtn");
    if (button) {
      button.classList.toggle("active", clean !== "off");
      button.title = `Aide contextuelle · ${label}`;
    }
    narrate(
      clean === "off"
        ? ""
        : clean === "minimal"
          ? "Aide minimale active · seules les conséquences importantes restent visibles."
          : "Aide guidée active · les actions importantes sont expliquées brièvement.",
      true
    );
    return clean;
  }

  function classifyAction(label) {
    const value = String(label || "").toLowerCase();
    if (/analy|transcri|compare|vérifi|critic|readiness/.test(value)) return ["analysis", "ANALYSE"];
    if (/propos|edl|fenêtres candidates|alternatives/.test(value)) return ["proposal", "PROPOSITION"];
    if (/appli|publier|enregistrer|ajouter|normaliser/.test(value)) return ["apply", "APPLICATION"];
    if (/export|tesseract|preview|rendu|delivery/.test(value)) return ["render", "RENDU"];
    return ["ready", "PRÊT"];
  }

  function setActionState(label) {
    const badge = document.getElementById("actionStateBadge");
    if (!badge) return;
    const [state, text] = classifyAction(label);
    badge.dataset.state = state;
    badge.textContent = text;
  }

  function narrate(message, force = false) {
    const host = document.getElementById("actionNarration");
    if (!host) return;
    if (!force && currentMode() === "off") return;
    host.textContent = message || "";
  }

  function copyForButton(button) {
    const explicit = button.dataset.actionCopy;
    if (explicit) return explicit;
    const label = [
      button.textContent || "",
      button.getAttribute("aria-label") || "",
      button.getAttribute("title") || "",
    ].join(" ").trim();
    for (const [pattern, copy] of COPY) {
      if (pattern.test(label)) return copy;
    }
    return "";
  }

  function positionMenu() {
    const button = document.getElementById("helpModeBtn");
    const menu = document.getElementById("helpModeMenu");
    if (!button || !menu) return;
    const rect = button.getBoundingClientRect();
    menu.style.top = `${rect.bottom + 7}px`;
    menu.style.left = `${Math.max(10, rect.right - menu.offsetWidth)}px`;
  }

  function toggleMenu() {
    const menu = document.getElementById("helpModeMenu");
    if (!menu) return;
    menu.hidden = !menu.hidden;
    if (!menu.hidden) requestAnimationFrame(positionMenu);
  }

  document.getElementById("helpModeBtn")?.addEventListener("click", event => {
    event.stopPropagation();
    toggleMenu();
  });
  document.querySelectorAll('input[name="helpMode"]').forEach(input => {
    input.addEventListener("change", () => setMode(input.value));
  });
  document.addEventListener("pointerdown", event => {
    const menu = document.getElementById("helpModeMenu");
    if (menu && !menu.hidden && !event.target.closest("#helpModeMenu") && !event.target.closest("#helpModeBtn")) {
      menu.hidden = true;
    }
  });
  document.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button) return;
    const label = [button.textContent || "", button.title || ""].join(" ");
    setActionState(label);
    const copy = copyForButton(button);
    if (copy) narrate(copy);
  }, true);
  document.addEventListener("focusin", event => {
    const button = event.target.closest?.("button");
    if (!button || currentMode() !== "guided") return;
    const copy = copyForButton(button);
    if (copy) narrate(copy);
  });
  window.addEventListener("resize", () => {
    const menu = document.getElementById("helpModeMenu");
    if (menu && !menu.hidden) positionMenu();
  });

  document.getElementById("openHelpCenterBtn")?.addEventListener("click", () => {
    const menu = document.getElementById("helpModeMenu");
    if (menu) menu.hidden = true;
    window.PisteSearch?.open("", "help");
  });
  document.getElementById("openResourcesBtn")?.addEventListener("click", () => {
    const menu = document.getElementById("helpModeMenu");
    if (menu) menu.hidden = true;
    window.PisteSearch?.open("", "resource");
  });

  window.PisteHelp = { setMode, mode: currentMode, narrate, setActionState };
  setMode(currentMode());
})();
