use std::fs::File;
use std::net::TcpStream;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent};

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: u16 = 8010;
const BACKEND_READY_TIMEOUT: Duration = Duration::from_secs(60);

struct BackendProcess(Mutex<Option<Child>>);

// A forced kill of the Tauri process (task manager, a crash, Alt+F4 racing
// shutdown) skips our RunEvent::Exit handler entirely, which would leave the
// bundled Django server running forever in the background. A Windows Job
// Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE ties the child's lifetime to
// ours at the OS level: when this process's last handle to the job closes —
// including on an abnormal exit, where no Rust code runs at all — Windows
// itself kills every process still assigned to it.
#[cfg(windows)]
struct BackendJob(windows::Win32::Foundation::HANDLE);

#[cfg(windows)]
impl BackendJob {
    fn create_and_assign(child: &Child) -> windows::core::Result<Self> {
        use std::os::windows::io::AsRawHandle;
        use windows::Win32::Foundation::HANDLE;
        use windows::Win32::System::JobObjects::{
            AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
            SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
        };

        unsafe {
            let job = CreateJobObjectW(None, None)?;

            let mut info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const _,
                std::mem::size_of_val(&info) as u32,
            )?;

            let process_handle = HANDLE(child.as_raw_handle());
            AssignProcessToJobObject(job, process_handle)?;

            Ok(BackendJob(job))
        }
    }
}

#[cfg(windows)]
impl Drop for BackendJob {
    fn drop(&mut self) {
        unsafe {
            let _ = windows::Win32::Foundation::CloseHandle(self.0);
        }
    }
}

fn backend_is_ready() -> bool {
    TcpStream::connect((BACKEND_HOST, BACKEND_PORT)).is_ok()
}

fn spawn_backend(app: &tauri::App) -> std::io::Result<Child> {
    let resource_dir = app
        .path()
        .resource_dir()
        .expect("resource directory must resolve");
    let python_exe = resource_dir.join("python-runtime").join("python.exe");
    let backend_dir = resource_dir.join("backend");

    let log_dir = app
        .path()
        .app_log_dir()
        .unwrap_or_else(|_| std::env::temp_dir());
    let _ = std::fs::create_dir_all(&log_dir);
    let stdout_log = File::create(log_dir.join("backend-stdout.log"))?;
    let stderr_log = File::create(log_dir.join("backend-stderr.log"))?;

    // The install directory (Program Files-equivalent) isn't reliably
    // writable and shouldn't hold user data anyway — point the database and
    // uploaded documents at the same per-user app-data root Tauri itself uses.
    let data_dir = app
        .path()
        .app_data_dir()
        .expect("app data directory must resolve");

    #[cfg(windows)]
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    let mut command = Command::new(python_exe);
    command
        .arg("desktop_server.py")
        .current_dir(&backend_dir)
        .env("MONIKA_DESKTOP_DATA_DIR", &data_dir)
        .stdout(Stdio::from(stdout_log))
        .stderr(Stdio::from(stderr_log));
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    command.spawn()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_http::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if !backend_is_ready() {
                let child = spawn_backend(app).expect("failed to launch bundled backend");

                #[cfg(windows)]
                {
                    match BackendJob::create_and_assign(&child) {
                        Ok(job) => {
                            // Leaked deliberately: this job object must outlive
                            // setup() and stay alive for the whole app lifetime,
                            // which `app.manage` (Send + Sync only) can't hold
                            // since HANDLE isn't Send. A process-lifetime leak
                            // of one handle is the trade-off for kill-on-close
                            // working even when we're not around to run cleanup.
                            std::mem::forget(job);
                        }
                        Err(err) => {
                            log::warn!("failed to attach backend to job object: {err}");
                        }
                    }
                }

                app.state::<BackendProcess>().0.lock().unwrap().replace(child);

                let deadline = Instant::now() + BACKEND_READY_TIMEOUT;
                while Instant::now() < deadline {
                    if backend_is_ready() {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(200));
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                if let Some(mut child) = app.state::<BackendProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
