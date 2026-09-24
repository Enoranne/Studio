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
