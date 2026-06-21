use std::fs;
use std::path::Path;
use std::str::FromStr;
use std::sync::Mutex;

use app_core::{
    AreaId, CreateTaskInput, ErrorCode, MoveTaskInput, ReorderTaskInput, SiftqError,
    SiftqResult, SqliteTaskRepository, Task, TaskService, UpdateTaskTitleInput,
    UuidGenerator,
};
use serde::Serialize;
use tauri::{Manager, State};

const DB_FILE_NAME: &str = "tasks.sqlite3";

type LiveTaskService = TaskService<SqliteTaskRepository, UuidGenerator>;

pub enum StorageState {
    Ready(Mutex<LiveTaskService>),
    Failed(CommandErrorDto),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CommandErrorDto {
    pub code: String,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct StorageHealthDto {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub code: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TaskDto {
    pub id: String,
    pub title: String,
    pub area_id: String,
    pub status: String,
    pub order: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateTaskRequest {
    pub title: String,
    pub area_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MoveTaskRequest {
    pub task_id: String,
    pub to_area_id: String,
    pub insert_at: Option<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReorderTaskRequest {
    pub task_id: String,
    pub to_index: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateTaskTitleRequest {
    pub task_id: String,
    pub title: String,
}

impl StorageState {
    fn ready(service: LiveTaskService) -> Self {
        Self::Ready(Mutex::new(service))
    }

    fn failed(error: CommandErrorDto) -> Self {
        Self::Failed(error)
    }
}

impl From<SiftqError> for CommandErrorDto {
    fn from(error: SiftqError) -> Self {
        Self {
            code: error.code().as_str().to_owned(),
            message: error.message().to_owned(),
        }
    }
}

impl From<CommandErrorDto> for StorageHealthDto {
    fn from(error: CommandErrorDto) -> Self {
        Self {
            ok: false,
            code: Some(error.code),
            message: Some(error.message),
        }
    }
}

impl From<Task> for TaskDto {
    fn from(task: Task) -> Self {
        Self {
            id: task.id,
            title: task.title,
            area_id: task.area_id.as_str().to_owned(),
            status: task.status.as_str().to_owned(),
            order: task.order_index,
        }
    }
}

pub fn run() {
    init_logging();
    tracing::info!("starting SIFTQ desktop app");

    tauri::Builder::default()
        .setup(|app| {
            app.manage(initialize_storage_for_app(app));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_storage_health,
            create_task,
            list_tasks,
            move_task,
            reorder_task,
            update_task_title
        ])
        .run(tauri::generate_context!())
        .expect("error while running desktop app");
}

fn init_logging() {
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .try_init();
}

fn initialize_storage_for_app(app: &tauri::App) -> StorageState {
    match resolve_db_path(app).and_then(|path| initialize_storage_at(&path)) {
        Ok(service) => {
            tracing::info!("storage initialized");
            StorageState::ready(service)
        }
        Err(error) => {
            tracing::error!(
                code = error.code().as_str(),
                error_message = error.message(),
                "storage initialization failed"
            );
            StorageState::failed(error.into())
        }
    }
}

fn resolve_db_path(app: &tauri::App) -> SiftqResult<std::path::PathBuf> {
    app.path()
        .app_data_dir()
        .map(|app_data_dir| app_data_dir.join(DB_FILE_NAME))
        .map_err(|error| {
            SiftqError::storage(format!("Failed to resolve app data directory: {error}"))
        })
}

fn initialize_storage_at(db_path: &Path) -> SiftqResult<LiveTaskService> {
    if let Some(parent) = db_path.parent() {
        fs::create_dir_all(parent).map_err(|error| {
            SiftqError::storage(format!("Failed to create app data directory: {error}"))
        })?;
    }

    let repository = SqliteTaskRepository::open(db_path)?;
    Ok(TaskService::new(repository, UuidGenerator))
}

#[tauri::command]
fn get_storage_health(storage: State<'_, StorageState>) -> StorageHealthDto {
    get_storage_health_handler(&storage)
}

#[tauri::command]
fn create_task(
    storage: State<'_, StorageState>,
    input: CreateTaskRequest,
) -> Result<TaskDto, CommandErrorDto> {
    create_task_handler(&storage, input)
}

#[tauri::command]
fn list_tasks(storage: State<'_, StorageState>) -> Result<Vec<TaskDto>, CommandErrorDto> {
    list_tasks_handler(&storage)
}

#[tauri::command]
fn move_task(
    storage: State<'_, StorageState>,
    input: MoveTaskRequest,
) -> Result<TaskDto, CommandErrorDto> {
    move_task_handler(&storage, input)
}

#[tauri::command]
fn reorder_task(
    storage: State<'_, StorageState>,
    input: ReorderTaskRequest,
) -> Result<TaskDto, CommandErrorDto> {
    reorder_task_handler(&storage, input)
}

#[tauri::command]
fn update_task_title(
    storage: State<'_, StorageState>,
    input: UpdateTaskTitleRequest,
) -> Result<TaskDto, CommandErrorDto> {
    update_task_title_handler(&storage, input)
}

fn get_storage_health_handler(storage: &StorageState) -> StorageHealthDto {
    match storage {
        StorageState::Ready(_) => StorageHealthDto {
            ok: true,
            code: None,
            message: None,
        },
        StorageState::Failed(error) => error.clone().into(),
    }
}

fn create_task_handler(
    storage: &StorageState,
    input: CreateTaskRequest,
) -> Result<TaskDto, CommandErrorDto> {
    let area_id = parse_area_id(&input.area_id)?;
    with_service(storage, |service| {
        service.create_task(CreateTaskInput {
            title: input.title,
            area_id,
        })
    })
    .map(TaskDto::from)
}

fn list_tasks_handler(storage: &StorageState) -> Result<Vec<TaskDto>, CommandErrorDto> {
    with_service(storage, |service| service.list_tasks())
        .map(|tasks| tasks.into_iter().map(TaskDto::from).collect())
}

fn move_task_handler(
    storage: &StorageState,
    input: MoveTaskRequest,
) -> Result<TaskDto, CommandErrorDto> {
    let to_area_id = parse_area_id(&input.to_area_id)?;
    with_service(storage, |service| {
        service.move_task(MoveTaskInput {
            task_id: input.task_id,
            to_area_id,
            insert_at: input.insert_at,
        })
    })
    .map(TaskDto::from)
}

fn reorder_task_handler(
    storage: &StorageState,
    input: ReorderTaskRequest,
) -> Result<TaskDto, CommandErrorDto> {
    with_service(storage, |service| {
        service.reorder_task(ReorderTaskInput {
            task_id: input.task_id,
            to_index: input.to_index,
        })
    })
    .map(TaskDto::from)
}

fn update_task_title_handler(
    storage: &StorageState,
    input: UpdateTaskTitleRequest,
) -> Result<TaskDto, CommandErrorDto> {
    with_service(storage, |service| {
        service.update_task_title(UpdateTaskTitleInput {
            task_id: input.task_id,
            title: input.title,
        })
    })
    .map(TaskDto::from)
}

fn with_service<T>(
    storage: &StorageState,
    operation: impl FnOnce(&mut LiveTaskService) -> SiftqResult<T>,
) -> Result<T, CommandErrorDto> {
    match storage {
        StorageState::Ready(service) => {
            let mut service = service.lock().map_err(|_| CommandErrorDto {
                code: ErrorCode::Internal.as_str().to_owned(),
                message: "Storage state lock is unavailable.".to_owned(),
            })?;

            operation(&mut service).map_err(CommandErrorDto::from)
        }
        StorageState::Failed(error) => Err(error.clone()),
    }
}

fn parse_area_id(value: &str) -> Result<AreaId, CommandErrorDto> {
    AreaId::from_str(value).map_err(|_| CommandErrorDto {
        code: ErrorCode::Validation.as_str().to_owned(),
        message: format!("Unknown task area: {value}"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use app_core::TaskRepository;
    use tempfile::tempdir;

    #[test]
    fn initializes_storage_at_app_data_db_path() {
        let temp_dir = tempdir().expect("temp dir should be created");
        let db_path = temp_dir.path().join("nested").join(DB_FILE_NAME);

        let mut service = initialize_storage_at(&db_path).expect("storage should initialize");
        let task = service
            .create_task(CreateTaskInput {
                title: " Persisted ".to_owned(),
                area_id: AreaId::Do,
            })
            .expect("task should be created");

        drop(service);

        let reopened_repository =
            SqliteTaskRepository::open(&db_path).expect("database should reopen");
        let reopened_tasks = reopened_repository
            .list_tasks()
            .expect("tasks should be restored");

        assert!(db_path.exists());
        assert_eq!(task.title, "Persisted");
        assert_eq!(reopened_tasks, vec![task]);
    }

    #[test]
    fn get_storage_health_returns_success_without_db_path() {
        let (_temp_dir, storage) = ready_storage();

        let health = get_storage_health_handler(&storage);

        assert_eq!(
            health,
            StorageHealthDto {
                ok: true,
                code: None,
                message: None,
            }
        );
    }

    #[test]
    fn get_storage_health_returns_failed_code_and_message() {
        let storage = StorageState::failed(CommandErrorDto {
            code: "MIGRATION".to_owned(),
            message: "Unsupported SQLite schema version: 2".to_owned(),
        });

        let health = get_storage_health_handler(&storage);

        assert_eq!(
            health,
            StorageHealthDto {
                ok: false,
                code: Some("MIGRATION".to_owned()),
                message: Some("Unsupported SQLite schema version: 2".to_owned()),
            }
        );
    }

    #[test]
    fn task_handlers_use_real_core_and_sqlite() {
        let (_temp_dir, storage) = ready_storage();

        let created = create_task_handler(
            &storage,
            CreateTaskRequest {
                title: " First ".to_owned(),
                area_id: "do".to_owned(),
            },
        )
        .expect("task should be created");
        let second = create_task_handler(
            &storage,
            CreateTaskRequest {
                title: " Second ".to_owned(),
                area_id: "do".to_owned(),
            },
        )
        .expect("second task should be created");
        let reordered = reorder_task_handler(
            &storage,
            ReorderTaskRequest {
                task_id: second.id.clone(),
                to_index: 0,
            },
        )
        .expect("task should reorder");
        let moved = move_task_handler(
            &storage,
            MoveTaskRequest {
                task_id: created.id.clone(),
                to_area_id: "done".to_owned(),
                insert_at: Some(0),
            },
        )
        .expect("task should move");
        let updated = update_task_title_handler(
            &storage,
            UpdateTaskTitleRequest {
                task_id: created.id.clone(),
                title: " Completed ".to_owned(),
            },
        )
        .expect("terminal task title should update");
        let tasks = list_tasks_handler(&storage).expect("tasks should list");

        assert_eq!(created.title, "First");
        assert_eq!(reordered.id, second.id);
        assert_eq!(reordered.order, 0);
        assert_eq!(moved.area_id, "done");
        assert_eq!(moved.status, "done");
        assert_eq!(updated.title, "Completed");
        assert_eq!(tasks.len(), 2);
        assert_eq!(tasks[0], reordered);
        assert_eq!(tasks[1], updated);
    }

    #[test]
    fn command_errors_are_structured() {
        let (_temp_dir, storage) = ready_storage();

        let error = create_task_handler(
            &storage,
            CreateTaskRequest {
                title: " ".to_owned(),
                area_id: "do".to_owned(),
            },
        )
        .expect_err("blank title should fail");

        assert_eq!(
            error,
            CommandErrorDto {
                code: "VALIDATION".to_owned(),
                message: "Task title must not be empty.".to_owned(),
            }
        );
    }

    #[test]
    fn task_commands_return_storage_initialization_error_when_failed() {
        let storage = StorageState::failed(CommandErrorDto {
            code: "STORAGE".to_owned(),
            message: "Failed to open SQLite database.".to_owned(),
        });

        let error = list_tasks_handler(&storage).expect_err("failed storage should fail");

        assert_eq!(
            error,
            CommandErrorDto {
                code: "STORAGE".to_owned(),
                message: "Failed to open SQLite database.".to_owned(),
            }
        );
    }

    #[test]
    fn command_boundary_maps_unknown_area_to_validation_error() {
        let (_temp_dir, storage) = ready_storage();

        let error = create_task_handler(
            &storage,
            CreateTaskRequest {
                title: "Task".to_owned(),
                area_id: "later".to_owned(),
            },
        )
        .expect_err("unknown area should fail");

        assert_eq!(
            error,
            CommandErrorDto {
                code: "VALIDATION".to_owned(),
                message: "Unknown task area: later".to_owned(),
            }
        );
    }

    fn ready_storage() -> (tempfile::TempDir, StorageState) {
        let temp_dir = tempdir().expect("temp dir should be created");
        let db_path = temp_dir.path().join(DB_FILE_NAME);
        let repository = SqliteTaskRepository::open(db_path).expect("database should open");
        let service = TaskService::new(repository, UuidGenerator);

        (temp_dir, StorageState::ready(service))
    }
}
