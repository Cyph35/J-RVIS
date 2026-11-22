//! JARVIS launcher: starts the local MLX model server and the OpenJarvis API for the desktop app.
//!
//! A Finder-launched app does not inherit the Terminal environment, so every path and variable the working
//! setup needs (see /Volumes/Acer/JARVIS/env.sh) is set explicitly here. Anything already running (for
//! example started from Terminal) is reused, and only processes this app started are stopped on quit.

use std::fs::OpenOptions;
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use tokio::process::{Child, Command};
use tokio::sync::Mutex;

pub const MLX_PORT: u16 = 8080;
pub const API_PORT: u16 = 8000;
pub const VOICE_PORT: u16 = 8090;
const MODEL: &str = "mlx-community/Qwen3.5-4B-MLX-4bit";

#[derive(serde::Serialize, Clone, Debug, Default, PartialEq)]
pub struct LaunchStatus {
    /// checking_volume | checking_engine | starting_model | starting_backend | ready | error
    pub phase: String,
    pub detail: String,
    pub ready: bool,
    /// volume_unavailable | project_missing | python_missing | model_not_found | port_busy | model_failed | backend_failed
    pub error_kind: Option<String>,
    pub error: Option<String>,
    pub hint: Option<String>,
    /// Set when everything else is ready but the voice could not start. JARVIS still works silently.
    pub voice_note: Option<String>,
}

#[derive(Clone, Debug)]
pub struct Paths {
    pub volume: PathBuf,
    pub root: PathBuf,
    pub repo: PathBuf,
    pub data: PathBuf,
    pub hf_home: PathBuf,
    pub python: PathBuf,
    pub jarvis: PathBuf,
    pub voice_python: PathBuf,
    pub voice_server: PathBuf,
    pub voice_config: PathBuf,
}

impl Paths {
    pub fn new(root: &Path) -> Self {
        let mut parts = root.components();
        // /Volumes/<name>/... -> the mount point is /Volumes/<name>
        let volume = match (parts.next(), parts.next(), parts.next()) {
            (Some(a), Some(b), Some(c)) if b.as_os_str() == "Volumes" => {
                PathBuf::from(a.as_os_str()).join(b.as_os_str()).join(c.as_os_str())
            }
            _ => root.to_path_buf(),
        };
        let repo = root.join("OpenJarvis");
        let data = root.join("data");
        Self {
            volume,
            hf_home: data.join("hf"),
            python: repo.join(".venv/bin/python"),
            jarvis: repo.join(".venv/bin/jarvis"),
            voice_python: root.join("voice-lab/bin/python"),
            voice_server: root.join("voice-lab/tts_server.py"),
            voice_config: data.join("voice/jarvis-voice.json"),
            repo,
            data,
            root: root.to_path_buf(),
        }
    }

    pub fn from_env() -> Self {
        let root = std::env::var("JARVIS_ROOT").unwrap_or_else(|_| "/Volumes/Acer/JARVIS".into());
        Self::new(Path::new(&root))
    }

    fn model_cache(&self) -> PathBuf {
        self.hf_home
            .join("hub")
            .join(format!("models--{}", MODEL.replace('/', "--")))
            .join("snapshots")
    }

    fn logs(&self) -> PathBuf {
        self.data.join("logs")
    }
}

fn err(kind: &str, message: &str, hint: &str) -> LaunchStatus {
    LaunchStatus {
        phase: "error".into(),
        detail: message.into(),
        ready: false,
        error_kind: Some(kind.into()),
        error: Some(message.into()),
        hint: Some(hint.into()),
        voice_note: None,
    }
}

/// Everything that must exist before anything is started. Never creates folders and never downloads a model.
pub fn preflight(p: &Paths) -> Result<(), LaunchStatus> {
    if !p.volume.exists() {
        return Err(err(
            "volume_unavailable",
            &format!("The JARVIS drive ({}) is not available.", p.volume.display()),
            "Connect the drive and wait for it to appear in Finder, then press Retry. JARVIS will not create a new data folder or download the model again.",
        ));
    }
    if !p.repo.exists() || !p.data.exists() {
        return Err(err(
            "project_missing",
            &format!("The JARVIS project folder was not found at {}.", p.root.display()),
            "The drive is connected but the OpenJarvis folder or its data folder is missing.",
        ));
    }
    if !p.python.exists() || !p.jarvis.exists() {
        return Err(err(
            "python_missing",
            "The JARVIS Python environment is missing.",
            "Run `uv sync --extra server --extra inference-mlx` inside the OpenJarvis folder, then press Retry.",
        ));
    }
    let has_model = std::fs::read_dir(p.model_cache())
        .map(|mut d| d.next().is_some())
        .unwrap_or(false);
    if !has_model {
        return Err(err(
            "model_not_found",
            "The Qwen3.5 4B model is not in the JARVIS model cache.",
            &format!("Expected it under {}. JARVIS never downloads models on its own.", p.hf_home.display()),
        ));
    }
    Ok(())
}

fn port_in_use(port: u16) -> bool {
    let addr: SocketAddr = ([127, 0, 0, 1], port).into();
    TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
}

async fn http_ok(url: &str) -> bool {
    let Ok(client) = reqwest::Client::builder().timeout(Duration::from_secs(2)).build() else {
        return false;
    };
    matches!(client.get(url).send().await, Ok(r) if r.status().is_success())
}

fn log_tail(path: &Path) -> String {
    let text = std::fs::read_to_string(path).unwrap_or_default();
    let lines: Vec<&str> = text.lines().rev().take(6).collect();
    lines.into_iter().rev().collect::<Vec<_>>().join("\n")
}

fn spawn_logged(cmd: &mut Command, log: &Path) -> std::io::Result<Child> {
    if let Some(dir) = log.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let file = OpenOptions::new().create(true).append(true).open(log)?;
    cmd.stdin(Stdio::null())
        .stdout(Stdio::from(file.try_clone()?))
        .stderr(Stdio::from(file))
        .kill_on_drop(true);
    cmd.spawn()
}

#[derive(Default)]
pub struct Launcher {
    pub status: LaunchStatus,
    mlx: Option<Child>,
    api: Option<Child>,
    voice: Option<Child>,
    task: Option<tauri::async_runtime::JoinHandle<()>>,
}

pub type Shared = Arc<Mutex<Launcher>>;

async fn set(state: &Shared, phase: &str, detail: &str) {
    state.lock().await.status = LaunchStatus { phase: phase.into(), detail: detail.into(), ..Default::default() };
}

async fn fail(state: &Shared, s: LaunchStatus) {
    state.lock().await.status = s;
}

/// Wait for `url`, failing early if the child we started exits. Returns the exit message on failure.
async fn wait_up(state: &Shared, which: u8, url: &str, secs: u64) -> Result<(), String> {
    let deadline = tokio::time::Instant::now() + Duration::from_secs(secs);
    while tokio::time::Instant::now() < deadline {
        if http_ok(url).await {
            return Ok(());
        }
        let mut l = state.lock().await;
        let child = if which == 0 { l.mlx.as_mut() } else { l.api.as_mut() };
        if let Some(c) = child {
            if let Ok(Some(code)) = c.try_wait() {
                return Err(format!("the process exited with {code}"));
            }
        }
        drop(l);
        tokio::time::sleep(Duration::from_millis(700)).await;
    }
    Err(format!("it did not answer within {secs} seconds"))
}

pub async fn boot(state: Shared) {
    let p = Paths::from_env();
    set(&state, "checking_volume", "Checking the JARVIS drive...").await;
    if let Err(e) = preflight(&p) {
        return fail(&state, e).await;
    }

    // ---- model server (MLX)
    set(&state, "checking_engine", "Checking the AI engine...").await;
    let mlx_url = format!("http://127.0.0.1:{MLX_PORT}/v1/models");
    if !http_ok(&mlx_url).await {
        if port_in_use(MLX_PORT) {
            return fail(&state, err("port_busy", &format!("Port {MLX_PORT} is used by another program."),
                "Quit whatever is using that port (for example a model server that is stuck) and press Retry.")).await;
        }
        set(&state, "starting_model", "Loading Qwen3.5 4B...").await;
        let log = p.logs().join("launcher-mlx.log");
        let mut cmd = Command::new(&p.python);
        cmd.args(["-m", "mlx_lm", "server", "--model", MODEL, "--host", "127.0.0.1", "--port", &MLX_PORT.to_string(),
            "--chat-template-args", r#"{"enable_thinking": false}"#])
            .current_dir(&p.repo)
            .env("HF_HOME", &p.hf_home)
            .env("HF_HUB_OFFLINE", "1") // the model is already cached; never download
            .env("HF_HUB_DISABLE_XET", "1")
            .env("HF_HUB_DISABLE_TELEMETRY", "1")
            .env("OPENJARVIS_HOME", &p.data);
        match spawn_logged(&mut cmd, &log) {
            Ok(child) => state.lock().await.mlx = Some(child),
            Err(e) => return fail(&state, err("model_failed", &format!("Could not start the model server: {e}"), "Check the JARVIS Python environment.")).await,
        }
        if let Err(why) = wait_up(&state, 0, &mlx_url, 240).await {
            let tail = log_tail(&log);
            return fail(&state, err("model_failed", &format!("The model server failed to start: {why}."),
                &format!("Log: {}\n{tail}", log.display()))).await;
        }
    }

    // ---- OpenJarvis API
    set(&state, "starting_backend", "Starting assistant services...").await;
    let api_url = format!("http://127.0.0.1:{API_PORT}/health");
    if !http_ok(&api_url).await {
        if port_in_use(API_PORT) {
            return fail(&state, err("port_busy", &format!("Port {API_PORT} is used by another program."),
                "Quit whatever is using that port and press Retry.")).await;
        }
        let log = p.logs().join("launcher-api.log");
        let mut cmd = Command::new(&p.jarvis);
        cmd.args(["serve", "--host", "127.0.0.1", "--port", &API_PORT.to_string()])
            .current_dir(&p.repo)
            .env("OPENJARVIS_HOME", &p.data)
            .env("HF_HOME", &p.hf_home)
            .env("PLAYWRIGHT_BROWSERS_PATH", p.data.join("playwright")) // browser tools use the copy on the Acer drive
            .env("HF_HUB_DISABLE_XET", "1")
            .env("PATH", format!("{}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", p.repo.join(".venv/bin").display()));
        match spawn_logged(&mut cmd, &log) {
            Ok(child) => state.lock().await.api = Some(child),
            Err(e) => return fail(&state, err("backend_failed", &format!("Could not start the assistant services: {e}"), "Check the JARVIS Python environment.")).await,
        }
        if let Err(why) = wait_up(&state, 1, &api_url, 120).await {
            let tail = log_tail(&log);
            return fail(&state, err("backend_failed", &format!("The assistant services failed to start: {why}."),
                &format!("Log: {}\n{tail}", log.display()))).await;
        }
    }

    let voice_note = start_voice(&state, &p).await;
    {
        let l = state.lock().await;
        let pids: Vec<u32> = [l.mlx.as_ref(), l.api.as_ref(), l.voice.as_ref()]
            .into_iter().flatten().filter_map(|c| c.id()).collect();
        spawn_watchdog(&pids);
    }
    state.lock().await.status = LaunchStatus { phase: "ready".into(), detail: "JARVIS is ready.".into(), ready: true, voice_note, ..Default::default() };
}

/// The voice server is optional: any problem is reported as a note, never as a startup failure.
async fn start_voice(state: &Shared, p: &Paths) -> Option<String> {
    let url = format!("http://127.0.0.1:{VOICE_PORT}/health");
    if http_ok(&url).await {
        return None; // already running (reuse it)
    }
    if !p.voice_python.exists() || !p.voice_server.exists() || !p.voice_config.exists() {
        return Some("The voice engine is not installed, so JARVIS will not speak.".into());
    }
    if port_in_use(VOICE_PORT) {
        return Some(format!("Port {VOICE_PORT} is used by another program, so JARVIS will not speak."));
    }
    let log = p.logs().join("launcher-voice.log");
    let mut cmd = Command::new(&p.voice_python);
    cmd.arg(&p.voice_server)
        .current_dir(&p.root)
        .env("HF_HOME", &p.hf_home)
        .env("HF_HUB_OFFLINE", "1") // never download a voice model on its own
        .env("HF_HUB_DISABLE_XET", "1")
        .env("JARVIS_VOICE_CONFIG", &p.voice_config)
        .env("JARVIS_VOICE_PORT", VOICE_PORT.to_string());
    match spawn_logged(&mut cmd, &log) {
        Ok(child) => state.lock().await.voice = Some(child),
        Err(e) => return Some(format!("The voice engine could not start: {e}")),
    }
    for _ in 0..40 {
        if http_ok(&url).await {
            return None;
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    Some(format!("The voice engine did not start. See {}", log.display()))
}

/// A tiny detached watcher: when this app dies for ANY reason (quit, crash, force-quit), it stops the
/// processes this app started, and only those. Without it a crash leaves model servers running.
pub fn spawn_watchdog(pids: &[u32]) {
    if pids.is_empty() {
        return;
    }
    let list = pids.iter().map(|p| p.to_string()).collect::<Vec<_>>().join(" ");
    let script = format!(
        "while kill -0 {app} 2>/dev/null; do sleep 1; done; kill {list} 2>/dev/null; sleep 4; kill -9 {list} 2>/dev/null",
        app = std::process::id(),
        list = list
    );
    let _ = std::process::Command::new("/bin/sh")
        .arg("-c")
        .arg(script)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn();
}

/// Stop only the processes this app started. Anything already running before launch is left alone.
pub async fn shutdown(state: &Shared) {
    let mut l = state.lock().await;
    if let Some(t) = l.task.take() {
        t.abort();
    }
    for child in [l.voice.take(), l.api.take(), l.mlx.take()].into_iter().flatten() {
        let mut c = child;
        let _ = c.kill().await;
    }
}

pub async fn start(state: &Shared) {
    shutdown(state).await;
    let s = state.clone();
    let task = tauri::async_runtime::spawn(boot(s));
    state.lock().await.task = Some(task);
}

#[tauri::command]
pub async fn get_launch_status(state: tauri::State<'_, Shared>) -> Result<LaunchStatus, String> {
    Ok(state.lock().await.status.clone())
}

#[tauri::command]
pub async fn retry_launch(state: tauri::State<'_, Shared>) -> Result<(), String> {
    start(&state).await;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(label: &str) -> PathBuf {
        let n = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
        std::env::temp_dir().join(format!("jarvis-launcher-{label}-{n}"))
    }

    #[test]
    fn missing_volume_is_reported_and_nothing_is_created() {
        let p = Paths::new(Path::new("/Volumes/__no_such_drive__/JARVIS"));
        let e = preflight(&p).unwrap_err();
        assert_eq!(e.error_kind.as_deref(), Some("volume_unavailable"));
        assert!(!Path::new("/Volumes/__no_such_drive__").exists());
    }

    #[test]
    fn volume_is_the_mount_point_under_volumes() {
        assert_eq!(Paths::new(Path::new("/Volumes/Acer/JARVIS")).volume, PathBuf::from("/Volumes/Acer"));
    }

    #[test]
    fn missing_model_is_reported_not_downloaded() {
        let root = tmp("model");
        let p = Paths::new(&root);
        std::fs::create_dir_all(p.repo.join(".venv/bin")).unwrap();
        std::fs::create_dir_all(&p.data).unwrap();
        std::fs::write(&p.python, "").unwrap();
        std::fs::write(&p.jarvis, "").unwrap();
        assert_eq!(preflight(&p).unwrap_err().error_kind.as_deref(), Some("model_not_found"));
        std::fs::create_dir_all(p.model_cache().join("abc")).unwrap();
        assert!(preflight(&p).is_ok());
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn missing_python_is_reported() {
        let root = tmp("py");
        let p = Paths::new(&root);
        std::fs::create_dir_all(&p.repo).unwrap();
        std::fs::create_dir_all(&p.data).unwrap();
        assert_eq!(preflight(&p).unwrap_err().error_kind.as_deref(), Some("python_missing"));
        let _ = std::fs::remove_dir_all(&root);
    }
}
