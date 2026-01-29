use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::collections::HashMap;
use tauri::{AppHandle, Emitter, Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

/// Holds the sidecar child process for lifecycle management
pub struct ServerState(pub Mutex<Option<CommandChild>>);

pub struct AppLifecycleState {
    pub is_quitting: AtomicBool,
}

/// HTTP client for proxying requests to backend (with redirect following enabled)
pub struct HttpClient(pub reqwest::Client);

impl HttpClient {
    pub fn new() -> Self {
        let client = reqwest::Client::builder()
            .redirect(reqwest::redirect::Policy::limited(10))
            .build()
            .expect("Failed to create HTTP client");
        HttpClient(client)
    }
}

/// Proxy a GET request to the backend
#[tauri::command]
async fn api_get(
    client: tauri::State<'_, HttpClient>,
    path: String,
) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:9527{}", path);
    println!("[Proxy] GET {}", url);

    let response = client.0
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("HTTP {}: {}", status, text));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse JSON: {}", e))
}

/// Proxy a POST request to the backend
#[tauri::command]
async fn api_post(
    client: tauri::State<'_, HttpClient>,
    path: String,
    body: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:9527{}", path);
    println!("[Proxy] POST {}", url);

    let mut request = client.0.post(&url);
    if let Some(b) = body {
        request = request.json(&b);
    }

    let response = request
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("HTTP {}: {}", status, text));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse JSON: {}", e))
}

/// Proxy a PUT request to the backend
#[tauri::command]
async fn api_put(
    client: tauri::State<'_, HttpClient>,
    path: String,
    body: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:9527{}", path);
    println!("[Proxy] PUT {}", url);

    let mut request = client.0.put(&url);
    if let Some(b) = body {
        request = request.json(&b);
    }

    let response = request
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("HTTP {}: {}", status, text));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse JSON: {}", e))
}

/// Proxy a PATCH request to the backend
#[tauri::command]
async fn api_patch(
    client: tauri::State<'_, HttpClient>,
    path: String,
    body: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:9527{}", path);
    println!("[Proxy] PATCH {}", url);

    let mut request = client.0.patch(&url);
    if let Some(b) = body {
        request = request.json(&b);
    }

    let response = request
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("HTTP {}: {}", status, text));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse JSON: {}", e))
}

/// Proxy a DELETE request to the backend
#[tauri::command]
async fn api_delete(
    client: tauri::State<'_, HttpClient>,
    path: String,
) -> Result<serde_json::Value, String> {
    let url = format!("http://127.0.0.1:9527{}", path);
    println!("[Proxy] DELETE {}", url);

    let response = client.0
        .delete(&url)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("HTTP {}: {}", status, text));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse JSON: {}", e))
}

/// Proxy a streaming request to the backend and emit events
#[tauri::command]
async fn api_stream(
    app: AppHandle,
    client: tauri::State<'_, HttpClient>,
    path: String,
    method: Option<String>,
    body: Option<serde_json::Value>,
    event_id: String,
) -> Result<(), String> {
    let url = format!("http://127.0.0.1:9527{}", path);
    println!("[Proxy] STREAM {} to event {}", url, event_id);

    let method = method.unwrap_or_else(|| "GET".to_string()).to_uppercase();
    
    let mut request = match method.as_str() {
        "GET" => client.0.get(&url),
        "POST" => client.0.post(&url),
        _ => return Err(format!("Unsupported method: {}", method)),
    };

    if let Some(b) = body {
        request = request.json(&b);
    }

    let mut response = request
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    let status = response.status();
    if !status.is_success() {
        let text = response.text().await.unwrap_or_default();
        return Err(format!("HTTP {}: {}", status, text));
    }

    tauri::async_runtime::spawn(async move {
        loop {
            match response.chunk().await {
                Ok(Some(chunk)) => {
                    let text = String::from_utf8_lossy(&chunk).to_string();
                    let _ = app.emit(&format!("stream-event-{}", event_id), serde_json::json!({
                        "type": "chunk",
                        "data": text
                    }));
                }
                Ok(None) => break, // End of stream
                Err(e) => {
                     let _ = app.emit(&format!("stream-event-{}", event_id), serde_json::json!({
                        "type": "error",
                        "message": e.to_string()
                    }));
                    return;
                }
            }
        }
        
        let _ = app.emit(&format!("stream-event-{}", event_id), serde_json::json!({
            "type": "done"
        }));
    });

    Ok(())
}

/// Start the Python FastAPI server as a sidecar process
#[tauri::command]
async fn start_server(app: AppHandle, state: tauri::State<'_, ServerState>) -> Result<String, String> {
    // Check if server is already running
    if state.0.lock().unwrap().is_some() {
        return Ok("Server already running".to_string());
    }

    let sidecar = app
        .shell()
        .sidecar("search-ads-server")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .args(["--port", "9527", "--host", "127.0.0.1"]);

    let (mut rx, child) = sidecar
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    // Store child process for later shutdown
    *state.0.lock().unwrap() = Some(child);

    // Monitor stdout/stderr in background
    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_shell::process::CommandEvent;
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let output = String::from_utf8_lossy(&line);
                    println!("[Server] {}", output);
                    let _ = app_handle.emit("server-log", output.to_string());
                }
                CommandEvent::Stderr(line) => {
                    let output = String::from_utf8_lossy(&line);
                    eprintln!("[Server Error] {}", output);
                    let _ = app_handle.emit("server-error", output.to_string());
                }
                CommandEvent::Terminated(status) => {
                    println!("[Server] Process terminated with status: {:?}", status);
                    let _ = app_handle.emit("server-terminated", format!("{:?}", status));
                    break;
                }
                _ => {}
            }
        }
    });

    Ok("Server started successfully".to_string())
}

/// Stop the Python server gracefully
#[tauri::command]
async fn stop_server(state: tauri::State<'_, ServerState>) -> Result<String, String> {
    let mut guard = state.0.lock().unwrap();
    if let Some(mut child) = guard.take() {
        // Send shutdown command via stdin
        if let Err(e) = child.write(b"SHUTDOWN\n") {
            eprintln!("Failed to send shutdown command: {}", e);
            // Try to kill if graceful shutdown fails
            let _ = child.kill();
        }
        Ok("Server stopped".to_string())
    } else {
        Ok("Server was not running".to_string())
    }
}

/// Get server status
#[tauri::command]
fn server_status(state: tauri::State<'_, ServerState>) -> bool {
    state.0.lock().unwrap().is_some()
}

/// Internal function to start the server (not a command)
async fn do_start_server(app: AppHandle, state: tauri::State<'_, ServerState>) -> Result<String, String> {
    start_server(app, state).await
}

/// Setup function to run when app starts
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .manage(ServerState(Mutex::new(None)))
        .manage(AppLifecycleState { is_quitting: AtomicBool::new(false) })
        .manage(HttpClient::new())
        .invoke_handler(tauri::generate_handler![
            start_server, stop_server, server_status,
            api_get, api_post, api_put, api_patch, api_delete,
            api_stream
        ])
        .setup(|app| {
            // Auto-start server on app launch
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Small delay to ensure app is ready
                std::thread::sleep(std::time::Duration::from_millis(500));

                let state = handle.state::<ServerState>();
                match do_start_server(handle.clone(), state).await {
                    Ok(msg) => println!("Server startup: {}", msg),
                    Err(e) => eprintln!("Failed to start server: {}", e),
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            match event {
                RunEvent::ExitRequested { code: _, api: _, .. } => {
                    let state = app_handle.state::<AppLifecycleState>();
                    state.is_quitting.store(true, Ordering::Relaxed);
                }
                RunEvent::WindowEvent { label, event: win_event, .. } => {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = win_event {
                        #[cfg(target_os = "macos")]
                        {
                            let state = app_handle.state::<AppLifecycleState>();
                            if !state.is_quitting.load(Ordering::Relaxed) {
                                // On macOS, hide the window instead of closing
                                api.prevent_close();
                                if let Some(window) = app_handle.get_webview_window(&label) {
                                    let _ = window.hide();
                                }
                            }
                        }
                    }
                }
                #[cfg(target_os = "macos")]
                RunEvent::Reopen { .. } => {
                     if let Some(window) = app_handle.get_webview_window("main") {
                         let _ = window.show();
                         let _ = window.set_focus();
                     }
                }
                RunEvent::Exit => {
                    // Graceful shutdown on app exit
                    let state = app_handle.state::<ServerState>();
                    let mut guard = state.0.lock().unwrap();
                    if let Some(mut child) = guard.take() {
                        println!("Shutting down server...");
                        let _ = child.write(b"SHUTDOWN\n");
                        // Give it a moment to shutdown gracefully
                        std::thread::sleep(std::time::Duration::from_millis(500));
                        let _ = child.kill();
                    }
                }
                _ => {}
            }
        });
}

