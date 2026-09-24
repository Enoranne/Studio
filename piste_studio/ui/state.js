(() => {
  const data = {
    workspace: "edit",
    viewerMode: "program",
    browserFilter: "all",
    indexMode: "clips",
    focusPane: null,
    overlayHud: true,
    overlayMix: true,
    overlayRange: true,
    contextDomain: "video",
    helpMode: "guided",
    uiDensity: "comfortable",
    contextColors: true,
    contextActions: true,
  };
  const listeners = new Set();

  window.PisteState = {
    get(key) {
      return data[key];
    },
    set(key, value) {
      if (data[key] === value) return value;
      data[key] = value;
      listeners.forEach((fn) => fn(key, value, { ...data }));
      return value;
    },
    snapshot() {
      return { ...data };
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
})();
