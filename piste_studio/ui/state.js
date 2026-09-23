(() => {
  const data = {
    workspace: "edit",
    viewerMode: "program",
    browserFilter: "all",
    indexMode: "clips",
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
