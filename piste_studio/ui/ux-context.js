(() => {
  const LABELS = {
    video: "VIDEO",
    audio: "AUDIO",
    transcript: "TRANSCRIPT",
    editorial: "EDITORIAL",
    delivery: "DELIVERY",
    project: "PROJET",
  };
  const VALID = new Set(Object.keys(LABELS));
  const QUICK_A11Y = {
    "SOURCE": "Afficher le moniteur source contextuel",
    "Fenêtres": "Proposer des segments visuels contextuels",
    "Alternatives": "Ouvrir le sélecteur de prises contextuel",
    "Écouter": "Préécouter la source sonore contextuelle",
    "Loudness": "Mesurer le niveau sonore contextuel",
    "Master Check": "Contrôler le mix final contextuel",
    "Agent": "Ouvrir l’assistant éditorial contextuel",
    "VO → Image": "Ouvrir le pont voix vers image contextuel",
    "Marqueur": "Créer un repère éditorial contextuel",
    "Index": "Afficher l’index de montage contextuel",
    "Readiness": "Vérifier la préparation production contextuelle",
    "Export": "Ouvrir la livraison contextuelle",
    "Canon": "Ouvrir les règles du projet contextuelles",
    "Versions": "Ouvrir l’historique du projet contextuel",
    "Enregistrer": "Sauvegarder le montage contextuellement",
  };

  const QUICK_ACTIONS = {
    video: [
      ["SOURCE", "video", () => typeof setViewerMode === "function" && setViewerMode("source")],
      ["Fenêtres", "video", () => typeof openEditorialWindows === "function" && openEditorialWindows()],
      ["Alternatives", "editorial", () => typeof openSourceSelector === "function" && openSourceSelector()],
    ],
    audio: [
      ["Écouter", "audio", () => typeof previewAudioAsset === "function" && previewAudioAsset()],
      ["Loudness", "audio", () => typeof analyzeSelectedAudioLoudness === "function" && analyzeSelectedAudioLoudness()],
      ["Master Check", "audio", () => typeof openMasterCheck === "function" && openMasterCheck()],
    ],
    transcript: [
      ["Agent", "editorial", () => typeof openEditorialAgent === "function" && openEditorialAgent()],
      ["VO → Image", "editorial", () => typeof openEditorialAgent === "function" && openEditorialAgent()],
    ],
    editorial: [
      ["Agent", "editorial", () => typeof openEditorialAgent === "function" && openEditorialAgent()],
      ["Marqueur", "editorial", () => typeof openMarkerComposer === "function" && openMarkerComposer()],
      ["Index", "editorial", () => typeof toggleIndex === "function" && toggleIndex()],
    ],
    delivery: [
      ["Readiness", "delivery", () => typeof openProductionReadiness === "function" && openProductionReadiness()],
      ["Master Check", "audio", () => typeof openMasterCheck === "function" && openMasterCheck()],
      ["Export", "delivery", () => typeof openDeliveryCenter === "function" && openDeliveryCenter()],
    ],
    project: [
      ["Canon", "project", () => document.querySelector('.nav-tab[data-view="canon"]')?.click()],
      ["Versions", "project", () => document.querySelector('.nav-tab[data-view="versions"]')?.click()],
      ["Enregistrer", "project", () => document.getElementById("saveBackendBtn")?.click()],
    ],
  };

  function selectedClipDomain() {
    if (typeof clips === "undefined" || typeof selectedClip === "undefined") return null;
    const clip = (clips || []).find(x => x.id === selectedClip);
    if (!clip) return null;
    const track = String(clip.track || "").toLowerCase();
    if (track === "video") return "video";
    if (["vo", "music", "sfx", "dialogue", "ambience"].includes(track)) return "audio";
    if (["titles", "title"].includes(track)) return "editorial";
    return null;
  }

  function inferDomain() {
    const delivery = document.querySelector(
      '.delivery-drawer:not([hidden]), #deliveryDrawer:not([hidden]), #productionReadinessDrawer:not([hidden])'
    );
    if (delivery) return "delivery";
    const agent = document.getElementById("editorialAgentDrawer");
    if (agent && !agent.hidden) return "editorial";

    const activeView = document.querySelector(".view.active")?.id || "";
    if (activeView === "view-canon" || activeView === "view-versions") return "project";

    if (typeof libraryMode !== "undefined" && libraryMode === "audio") return "audio";
    const clipDomain = selectedClipDomain();
    if (clipDomain) return clipDomain;

    const activeLib = document.querySelector(".libtab.active")?.dataset?.lib;
    if (activeLib === "audio") return "audio";
    return "video";
  }

  function renderQuickActions(domain) {
    const host = document.getElementById("contextQuickActions");
    if (!host) return;
    host.innerHTML = "";
    const actions = QUICK_ACTIONS[domain] || [];
    if (!actions.length) return;
    const label = document.createElement("span");
    label.className = "context-quick-label";
    label.textContent = "UTILE ICI";
    host.appendChild(label);
    actions.forEach(([title, itemDomain, run]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = title;
      button.setAttribute("aria-label", QUICK_A11Y[title] || ("Ouvrir une action contextuelle " + itemDomain));
      button.title = "Action contextuelle · " + title;
      button.dataset.domain = itemDomain;
      button.addEventListener("click", event => {
        event.stopPropagation();
        run();
        window.PisteHelp?.narrate(title + " · action contextuelle " + (LABELS[domain] || domain));
      });
      host.appendChild(button);
    });
  }

  function applyPaneAccent(domain) {
    document.querySelectorAll(".pane.context-active").forEach(el => el.classList.remove("context-active"));
    if (domain === "video" || domain === "audio") {
      document.getElementById("browserPanel")?.classList.add("context-active");
      document.querySelector(".viewer-panel")?.classList.add("context-active");
      document.getElementById("inspectorPanel")?.classList.add("context-active");
    } else if (domain === "editorial" || domain === "transcript") {
      document.getElementById("inspectorPanel")?.classList.add("context-active");
    }
  }

  function set(domain, reason = "") {
    const next = VALID.has(domain) ? domain : "video";
    document.body.dataset.context = next;
    document.body.dataset.contextReason = reason || "";
    const chip = document.getElementById("contextDomainChip");
    if (chip) {
      chip.textContent = LABELS[next];
      chip.dataset.domain = next;
      chip.title = reason ? `Contexte actif · ${reason}` : `Contexte actif · ${LABELS[next]}`;
    }
    applyPaneAccent(next);
    renderQuickActions(next);
    if (window.PisteState?.get("contextDomain") !== next) {
      window.PisteState?.set("contextDomain", next);
    }
    return next;
  }

  function refresh(reason = "sélection courante") {
    return set(inferDomain(), reason);
  }

  window.PisteContext = { set, refresh, infer: inferDomain, labels: { ...LABELS } };

  document.addEventListener("click", event => {
    const domainTarget = event.target.closest("[data-domain]");
    if (domainTarget?.dataset?.domain && VALID.has(domainTarget.dataset.domain)) {
      requestAnimationFrame(() => set(domainTarget.dataset.domain, "outil actif"));
    }
    const lib = event.target.closest(".libtab");
    if (lib?.dataset?.lib) {
      requestAnimationFrame(() => set(lib.dataset.lib === "audio" ? "audio" : "video", "bibliothèque"));
      return;
    }
    if (event.target.closest("#editorialAgentBtn")) {
      requestAnimationFrame(() => set("editorial", "Editorial Agent"));
      return;
    }
    if (event.target.closest('[onclick*="openDeliveryCenter"], #readinessBtn')) {
      requestAnimationFrame(() => set("delivery", "livraison"));
      return;
    }
    if (event.target.closest(".nav-tab")) {
      requestAnimationFrame(() => refresh("navigation"));
      return;
    }
    if (event.target.closest(".clip,.media-row,.audio-row")) {
      requestAnimationFrame(() => refresh("sélection"));
    }
  }, true);

  const observer = new MutationObserver(() => refresh("interface"));
  ["editorialAgentDrawer", "selectionKind"].forEach(id => {
    const node = document.getElementById(id);
    if (node) observer.observe(node, { attributes: true, childList: true, subtree: true });
  });

  window.addEventListener("piste:context", event => {
    const detail = event.detail || {};
    set(detail.domain, detail.reason || "outil");
  });

  document.addEventListener("DOMContentLoaded", () => refresh("démarrage"), { once: true });
  requestAnimationFrame(() => refresh("démarrage"));
})();
