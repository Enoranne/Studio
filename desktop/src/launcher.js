const button = document.getElementById("openProject");
const status = document.getElementById("status");

function setStatus(message, kind = "") {
  status.textContent = message;
  status.className = "status" + (kind ? " " + kind : "");
}

async function openProject() {
  button.disabled = true;
  setStatus("Sélection du projet…");
  try {
    const selected = await window.__TAURI__.dialog.open({
      directory: true,
      multiple: false,
      title: "Ouvrir un projet PISTE Studio"
    });
    if (!selected) {
      setStatus("Ouverture annulée.");
      return;
    }

    setStatus("Démarrage du moteur local…");
    const result = await window.__TAURI__.core.invoke("launch_project", {
      projectPath: selected
    });

    setStatus("Ouverture de PISTE Studio…", "ok");
    const StudioWindow = window.__TAURI__.webviewWindow.WebviewWindow;
    const studio = new StudioWindow("studio", {
      url: result.url,
      title: "PISTE Studio",
      width: 1440,
      height: 900,
      minWidth: 1024,
      minHeight: 700,
      resizable: true,
      center: true
    });

    studio.once("tauri://created", async () => {
      await window.__TAURI__.window.getCurrentWindow().hide();
    });
    studio.once("tauri://error", (event) => {
      setStatus("Impossible d’ouvrir la fenêtre Studio : " + event.payload, "error");
      button.disabled = false;
    });
  } catch (error) {
    setStatus(String(error), "error");
  } finally {
    if (!status.classList.contains("ok")) button.disabled = false;
  }
}

button.addEventListener("click", openProject);
