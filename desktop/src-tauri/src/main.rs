use serde::Serialize;
use std::{
    net::{SocketAddr, TcpListener, TcpStream},
    path::Path,
    sync::Mutex,
    thread,
    time::Duration,
};
use tauri::{Manager, State};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

struct BackendState(Mutex<Option<CommandChild>>);

#[derive(Serialize)]
struct LaunchResult {
    url: String,
    port: u16,
    project_path: String,
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
        if TcpStream::connect_timeout(&address, Duration::from_millis(100)).is_ok() {
            ready = true;
            break;
        }
        thread::sleep(Duration::from_millis(50));
    }

    if !ready {
        stop_backend(&state);
        return Err("Le backend PISTE Studio n’a pas répondu au démarrage.".into());
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
        .invoke_handler(tauri::generate_handler![launch_project])
        .on_window_event(|window, event| {
            if window.label() == "studio" && matches!(event, tauri::WindowEvent::Destroyed) {
                let state = window.app_handle().state::<BackendState>();
                stop_backend(&state);
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running PISTE Studio desktop");
}
