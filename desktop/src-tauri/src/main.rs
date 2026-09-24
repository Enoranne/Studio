use serde::{Deserialize, Serialize};
use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::{Path, PathBuf},
    sync::Mutex,
    thread,
    time::Duration,
};
use tauri::{Manager, State};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

const APP_VERSION: &str = "0.25.0";

struct BackendState(Mutex<Option<CommandChild>>);

#[derive(Serialize)]
struct LaunchResult {
    url: String,
    port: u16,
    project_path: String,
}

#[derive(Serialize)]
struct CreateResult {
    project_path: String,
}

#[derive(Deserialize)]
struct HealthResponse {
    ok: bool,
    version: String,
    project_root: String,
}

fn free_local_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|e| format!("Impossible de réserver un port local : {e}"))?;
    listener
        .local_addr()
        .map(|addr| addr.port())
        .map_err(|e| format!("Impossible de lire le port local : {e}"))
}

fn stop_backend(state: &State<'_, BackendState>) {
    if let Ok(mut guard) = state.0.lock() {
        if let Some(child) = guard.take() {
            let _ = child.kill();
        }
    }
}

fn normalize_existing_path(path: &Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

fn backend_health_matches(address: &SocketAddr, expected_project: &Path) -> bool {
    let Ok(mut stream) = TcpStream::connect_timeout(address, Duration::from_millis(150)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(350)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(350)));
    if stream
        .write_all(b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }
    let Some((head, body)) = response.split_once("\r\n\r\n") else {
        return false;
    };
    if !(head.starts_with("HTTP/1.1 200") || head.starts_with("HTTP/1.0 200")) {
        return false;
    }
    let Ok(health) = serde_json::from_str::<HealthResponse>(body) else {
        return false;
    };
    if !health.ok || health.version.trim().is_empty() {
        return false;
    }

    normalize_existing_path(Path::new(&health.project_root))
        == normalize_existing_path(expected_project)
}

fn safe_project_folder_name(name: &str) -> Result<String, String> {
    let cleaned: String = name
        .trim()
        .chars()
        .map(|c| {
            if c == '/' || c == '\\' || c == ':' || c.is_control() {
                ' '
            } else {
                c
            }
        })
        .collect();
    let compact = cleaned.split_whitespace().collect::<Vec<_>>().join(" ");
    let folder = compact
        .trim_matches(|c: char| c == '.' || c == ' ')
        .trim()
        .to_string();
    if folder.is_empty() {
        return Err("Donne un nom au projet avant de le créer.".into());
    }
    Ok(folder)
}

#[tauri::command]
async fn create_project(
    app: tauri::AppHandle,
    parent_path: String,
    project_name: String,
) -> Result<CreateResult, String> {
    let parent = Path::new(&parent_path);
    if !parent.is_dir() {
        return Err("Le dossier de destination n’existe pas.".into());
    }
    let folder_name = safe_project_folder_name(&project_name)?;
    let project = parent.join(folder_name);
    let project_path = project.to_string_lossy().to_string();

    let output = app
        .shell()
        .sidecar("piste-studio-backend")
        .map_err(|e| format!("Sidecar PISTE Studio indisponible : {e}"))?
        .args([
            "--init-project",
            "--root",
            project_path.as_str(),
            "--name",
            project_name.trim(),
        ])
        .output()
        .await
        .map_err(|e| format!("Impossible de créer le projet : {e}"))?;

    if !output.status.success() {
        let message = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if message.is_empty() {
            "La création du projet a échoué.".into()
        } else {
            message
        });
    }
    if !project.join("project.yaml").is_file() {
        return Err("Le projet a été créé sans project.yaml : création incomplète.".into());
    }

    Ok(CreateResult { project_path })
}

#[tauri::command]
fn launch_project(
    app: tauri::AppHandle,
    state: State<'_, BackendState>,
    project_path: String,
) -> Result<LaunchResult, String> {
    let project = Path::new(&project_path);
    if !project.is_dir() {
        return Err("Le dossier sélectionné n’existe pas.".into());
    }
    if !project.join("project.yaml").is_file() {
        return Err("Ce dossier n’est pas un projet PISTE Studio : project.yaml est absent.".into());
    }

    stop_backend(&state);
    let port = free_local_port()?;
    let args = vec![
        "--project".to_string(),
        project_path.clone(),
        "--host".to_string(),
        "127.0.0.1".to_string(),
        "--port".to_string(),
        port.to_string(),
        "--no-open".to_string(),
    ];

    let sidecar = app
        .shell()
        .sidecar("piste-studio-backend")
        .map_err(|e| format!("Sidecar PISTE Studio indisponible : {e}"))?;

    let (mut events, child) = sidecar
        .args(args)
        .spawn()
        .map_err(|e| format!("Impossible de démarrer le backend PISTE Studio : {e}"))?;

    {
        let mut guard = state
            .0
            .lock()
            .map_err(|_| "État backend indisponible.".to_string())?;
        *guard = Some(child);
    }

    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    eprintln!("[PISTE backend] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[PISTE backend] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Error(message) => {
                    eprintln!("[PISTE backend error] {message}");
                }
                CommandEvent::Terminated(payload) => {
                    eprintln!("[PISTE backend terminated] {:?}", payload.code);
                }
                _ => {}
            }
        }
    });

    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let mut ready = false;
    for _ in 0..120 {
        if backend_health_matches(&address, project) {
            ready = true;
            break;
        }
        thread::sleep(Duration::from_millis(50));
    }

    if !ready {
        stop_backend(&state);
        return Err("Le moteur local n’a pas confirmé l’ouverture de ce projet.".into());
    }

    Ok(LaunchResult {
        url: format!("http://127.0.0.1:{port}/"),
        port,
        project_path,
    })
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(BackendState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![create_project, launch_project])
        .on_window_event(|window, event| {
            if window.label() == "studio" && matches!(event, tauri::WindowEvent::Destroyed) {
                let state = window.app_handle().state::<BackendState>();
                stop_backend(&state);
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .unwrap_or_else(|e| panic!("error while running PISTE Studio {APP_VERSION}: {e}"));
}
