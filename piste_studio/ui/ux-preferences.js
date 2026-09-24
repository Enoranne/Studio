(() => {
  const KEYS = {
    density: "piste.ui.density",
    colors: "piste.ui.contextColors",
    actions: "piste.ui.contextActions",
  };
  const VALID_DENSITY = new Set(["comfortable", "compact"]);

  function storedBool(key, fallback) {
    const value = localStorage.getItem(key);
    if (value === null) return fallback;
    return value !== "false";
  }

  function apply() {
    const densityRaw = localStorage.getItem(KEYS.density) || "comfortable";
    const density = VALID_DENSITY.has(densityRaw) ? densityRaw : "comfortable";
    const colors = storedBool(KEYS.colors, true);
    const actions = storedBool(KEYS.actions, true);

    document.body.dataset.density = density;
    document.body.dataset.contextColors = colors ? "on" : "off";
    document.body.dataset.contextActions = actions ? "on" : "off";

    window.PisteState?.set("uiDensity", density);
    window.PisteState?.set("contextColors", colors);
    window.PisteState?.set("contextActions", actions);

    document.querySelectorAll('input[name="uiDensity"]').forEach(input => {
      input.checked = input.value === density;
    });
    const colorToggle = document.getElementById("contextColorsToggle");
    const actionToggle = document.getElementById("contextActionsToggle");
    if (colorToggle) colorToggle.checked = colors;
    if (actionToggle) actionToggle.checked = actions;
    return { density, colors, actions };
  }

  function position() {
    const button = document.getElementById("preferencesBtn");
    const menu = document.getElementById("preferencesMenu");
    if (!button || !menu) return;
    const rect = button.getBoundingClientRect();
    menu.style.top = String(rect.bottom + 7) + "px";
    menu.style.left = String(Math.max(10, rect.right - menu.offsetWidth)) + "px";
  }

  function toggle() {
    const menu = document.getElementById("preferencesMenu");
    if (!menu) return;
    menu.hidden = !menu.hidden;
    if (!menu.hidden) {
      apply();
      requestAnimationFrame(position);
    }
  }

  document.getElementById("preferencesBtn")?.addEventListener("click", event => {
    event.stopPropagation();
    toggle();
  });
  document.querySelectorAll('input[name="uiDensity"]').forEach(input => {
    input.addEventListener("change", () => {
      localStorage.setItem(KEYS.density, input.value);
      const state = apply();
      window.PisteHelp?.narrate("Densité " + (state.density === "compact" ? "compacte" : "confort") + " activée.");
    });
  });
  document.getElementById("contextColorsToggle")?.addEventListener("change", event => {
    localStorage.setItem(KEYS.colors, String(event.target.checked));
    apply();
    window.PisteHelp?.narrate(event.target.checked ? "Nuances contextuelles activées." : "Nuances contextuelles neutralisées.");
  });
  document.getElementById("contextActionsToggle")?.addEventListener("change", event => {
    localStorage.setItem(KEYS.actions, String(event.target.checked));
    apply();
    window.PisteHelp?.narrate(event.target.checked ? "Actions contextuelles visibles." : "Actions contextuelles masquées.");
  });
  document.addEventListener("pointerdown", event => {
    const menu = document.getElementById("preferencesMenu");
    if (menu && !menu.hidden && !event.target.closest("#preferencesMenu") && !event.target.closest("#preferencesBtn")) {
      menu.hidden = true;
    }
  });
  window.addEventListener("resize", () => {
    const menu = document.getElementById("preferencesMenu");
    if (menu && !menu.hidden) position();
  });

  window.PistePreferences = { apply };
  apply();
})();
