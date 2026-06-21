pub mod domain;
pub mod error;
pub mod id;
pub mod repository;
pub mod service;
pub mod sqlite;

pub use domain::{
    normalize_task_title, status_for_area, AreaId, Task, TaskId, TaskStatus, TASK_TITLE_MAX_CHARS,
};
pub use error::{ErrorCode, SiftqError, SiftqResult};
pub use id::{IdGenerator, UuidGenerator};
pub use repository::TaskRepository;
pub use service::{
    CreateTaskInput, MoveTaskInput, ReorderTaskInput, TaskService, UpdateTaskTitleInput,
};
pub use sqlite::SqliteTaskRepository;
