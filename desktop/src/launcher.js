const openButton = document.getElementById("openProject");
const newButton = document.getElementById("newProject");
const createPanel = document.getElementById("createPanel");
const createForm = document.getElementById("createPanel");
const projectName = document.getElementById("projectName");
const createButton = document.getElementById("createProject");
const cancelCreate = document.getElementById("cancelCreate");
const status = document.getElementById("status");

function setStatus(message, kind = "") {
  status.textContent = message;
  status.className = "status" + (kind ? " " + kind : "");
}

function setBusy(busy) {
  openButton.disabled = busy;
  newButton.disabled = busy;
  createButton.disabled = busy;
  projectName.disabled = busy;
}

async function showStudio(projectPath) {
  setStatus("Démarrage et vérification du moteur local…");
  const result = await window.__TAURI__.core.invoke("launch_project", {
    projectPath
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
    setBusy(false);
  });
}

async function openProject() {
  setBusy(true);
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
    await showStudio(selected);
  } catch (error) {
    setStatus(String(error), "error");
  } finally {
    if (!status.classList.contains("ok")) setBusy(false);
  }
}

function toggleCreatePanel(show) {
  createPanel.hidden = !show;
  if (show) {
    projectName.focus();
    setStatus("Donne un nom au projet puis choisis son emplacement.");
  } else {
    setStatus("Prêt.");
  }
}

async function createProject(event) {
  event.preventDefault();
  const name = projectName.value.trim();
  if (!name) {
    setStatus("Donne d’abord un nom au projet.", "error");
    projectName.focus();
    return;
  }

  setBusy(true);
  setStatus("Choisis le dossier qui contiendra le nouveau projet…");
  try {
    const parent = await window.__TAURI__.dialog.open({
      directory: true,
      multiple: false,
      title: "Emplacement du nouveau projet"
    });
    if (!parent) {
      setStatus("Création annulée.");
      return;
    }

    setStatus("Création de la structure du projet…");
    const created = await window.__TAURI__.core.invoke("create_project", {
      parentPath: parent,
      projectName: name
    });
    await showStudio(created.project_path);
  } catch (error) {
    setStatus(String(error), "error");
  } finally {
    if (!status.classList.contains("ok")) setBusy(false);
  }
}

openButton.addEventListener("click", openProject);
newButton.addEventListener("click", () => toggleCreatePanel(true));
cancelCreate.addEventListener("click", () => toggleCreatePanel(false));
createForm.addEventListener("submit", createProject);
