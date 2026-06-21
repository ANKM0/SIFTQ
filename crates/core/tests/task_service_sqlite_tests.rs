use app_core::{
    AreaId, CreateTaskInput, ErrorCode, IdGenerator, MoveTaskInput, ReorderTaskInput,
    SiftqResult, SqliteTaskRepository, Task, TaskRepository, TaskService, TaskStatus,
    UpdateTaskTitleInput,
};
use rusqlite::{params, Connection};
use tempfile::tempdir;

#[test]
fn create_and_list_tasks_with_trimmed_titles_and_area_order() {
    let mut service = service_with_ids(["task-1", "task-2", "task-3"]);

    let first = service
        .create_task(create_input("  First  ", AreaId::Do))
        .expect("first task should be created");
    service
        .create_task(create_input("Other area", AreaId::Schedule))
        .expect("other area task should be created");
    let second = service
        .create_task(create_input("Second", AreaId::Do))
        .expect("second task should be created");

    assert_eq!(
        first,
        Task {
            id: "task-1".to_owned(),
            title: "First".to_owned(),
            area_id: AreaId::Do,
            status: TaskStatus::Active,
            order_index: 0,
        }
    );
    assert_eq!(second.order_index, 1);
    assert_task_shape(
        service.list_tasks().expect("tasks should list"),
        [
            ("task-1", "First", AreaId::Do, TaskStatus::Active, 0),
            ("task-3", "Second", AreaId::Do, TaskStatus::Active, 1),
            (
                "task-2",
                "Other area",
                AreaId::Schedule,
                TaskStatus::Active,
                0,
            ),
        ],
    );
}

#[test]
fn create_rejects_terminal_area_and_invalid_titles() {
    let mut service = service_with_ids(["task-1"]);

    assert_error_code(
        service.create_task(create_input("Terminal", AreaId::Done)),
        ErrorCode::Validation,
        "Tasks can only be created in matrix areas.",
    );
    assert_error_code(
        service.create_task(create_input("   ", AreaId::Do)),
        ErrorCode::Validation,
        "Task title must not be empty.",
    );
    assert_error_code(
        service.create_task(create_input(&"a".repeat(257), AreaId::Do)),
        ErrorCode::Validation,
        "Task title must be 256 characters or less.",
    );
    assert!(service
        .list_tasks()
        .expect("empty repository should list")
        .is_empty());
}

#[test]
fn move_and_reorder_clamp_indexes_and_normalize_affected_areas() {
    let mut service = service_with_ids(["task-1", "task-2", "task-3", "task-4"]);
    service
        .create_task(create_input("First", AreaId::Do))
        .expect("task should be created");
    service
        .create_task(create_input("Second", AreaId::Do))
        .expect("task should be created");
    service
        .create_task(create_input("Target top", AreaId::Schedule))
        .expect("task should be created");
    service
        .create_task(create_input("Target bottom", AreaId::Schedule))
        .expect("task should be created");

    service
        .move_task(MoveTaskInput {
            task_id: "task-2".to_owned(),
            to_area_id: AreaId::Schedule,
            insert_at: Some(1),
        })
        .expect("task should move into target area");
    service
        .move_task(MoveTaskInput {
            task_id: "task-1".to_owned(),
            to_area_id: AreaId::Schedule,
            insert_at: Some(99),
        })
        .expect("oversized insert should clamp to end");
    service
        .reorder_task(ReorderTaskInput {
            task_id: "task-1".to_owned(),
            to_index: -5,
        })
        .expect("negative reorder should clamp to start");

    assert_task_shape(
        service.list_tasks().expect("tasks should list"),
        [
            (
                "task-1",
                "First",
                AreaId::Schedule,
                TaskStatus::Active,
                0,
            ),
            (
                "task-3",
                "Target top",
                AreaId::Schedule,
                TaskStatus::Active,
                1,
            ),
            (
                "task-2",
                "Second",
                AreaId::Schedule,
                TaskStatus::Active,
                2,
            ),
            (
                "task-4",
                "Target bottom",
                AreaId::Schedule,
                TaskStatus::Active,
                3,
            ),
        ],
    );
}

#[test]
fn done_and_skipped_tasks_are_retained_but_cannot_be_restored_to_matrix() {
    let mut service = service_with_ids(["task-1", "task-2"]);
    service
        .create_task(create_input("Finish", AreaId::Do))
        .expect("task should be created");
    service
        .create_task(create_input("Drop", AreaId::Delegate))
        .expect("task should be created");

    service
        .move_task(MoveTaskInput {
            task_id: "task-1".to_owned(),
            to_area_id: AreaId::Done,
            insert_at: None,
        })
        .expect("task should move to done");
    service
        .move_task(MoveTaskInput {
            task_id: "task-2".to_owned(),
            to_area_id: AreaId::Skipped,
            insert_at: None,
        })
        .expect("task should move to skipped");

    assert_task_shape(
        service.list_tasks().expect("terminal tasks should list"),
        [
            (
                "task-2",
                "Drop",
                AreaId::Skipped,
                TaskStatus::Skipped,
                0,
            ),
            ("task-1", "Finish", AreaId::Done, TaskStatus::Done, 0),
        ],
    );
    assert_error_code(
        service.move_task(MoveTaskInput {
            task_id: "task-1".to_owned(),
            to_area_id: AreaId::Do,
            insert_at: None,
        }),
        ErrorCode::Validation,
        "Terminal tasks cannot be restored to matrix areas.",
    );
}

#[test]
fn update_title_allows_terminal_tasks_and_rejects_invalid_titles_without_mutation() {
    let mut service = service_with_ids(["task-1"]);
    service
        .create_task(create_input("Finish", AreaId::Do))
        .expect("task should be created");
    service
        .move_task(MoveTaskInput {
            task_id: "task-1".to_owned(),
            to_area_id: AreaId::Done,
            insert_at: None,
        })
        .expect("task should move to done");

    let updated = service
        .update_task_title(UpdateTaskTitleInput {
            task_id: "task-1".to_owned(),
            title: "  Finished  ".to_owned(),
        })
        .expect("terminal title should update");

    assert_eq!(updated.title, "Finished");
    assert_eq!(updated.status, TaskStatus::Done);
    assert_error_code(
        service.update_task_title(UpdateTaskTitleInput {
            task_id: "task-1".to_owned(),
            title: " ".to_owned(),
        }),
        ErrorCode::Validation,
        "Task title must not be empty.",
    );
    assert_eq!(
        service
            .list_tasks()
            .expect("tasks should list")
            .first()
            .expect("task should exist")
            .title,
        "Finished"
    );
}

#[test]
fn migration_creates_initial_schema_and_accepts_user_version_one() {
    let repository = SqliteTaskRepository::open_in_memory().expect("migration should run");
    assert_eq!(repository.user_version().expect("version should read"), 1);

    let connection = Connection::open_in_memory().expect("connection should open");
    connection
        .execute_batch(
            "CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                area_id TEXT NOT NULL,
                status TEXT NOT NULL,
                order_index INTEGER NOT NULL
            );
            PRAGMA user_version = 1;",
        )
        .expect("version one schema should be prepared");

    let repository =
        SqliteTaskRepository::from_connection(connection).expect("version one should open");
    assert_eq!(repository.user_version().expect("version should read"), 1);
}

#[test]
fn unknown_schema_version_is_a_migration_error() {
    let connection = Connection::open_in_memory().expect("connection should open");
    connection
        .execute_batch("PRAGMA user_version = 99;")
        .expect("version should be set");

    assert_error_code(
        SqliteTaskRepository::from_connection(connection),
        ErrorCode::Migration,
        "Unsupported SQLite schema version: 99",
    );
}

#[test]
fn sqlite_file_reopen_restores_task_area_status_and_order() {
    let directory = tempdir().expect("tempdir should be created");
    let database_path = directory.path().join("tasks.sqlite3");

    {
        let repository =
            SqliteTaskRepository::open(&database_path).expect("file repository should open");
        let mut service =
            TaskService::new(repository, FixedIdGenerator::new(["task-1", "task-2"]));
        service
            .create_task(create_input("First", AreaId::Do))
            .expect("task should be created");
        service
            .create_task(create_input("Second", AreaId::Do))
            .expect("task should be created");
        service
            .move_task(MoveTaskInput {
                task_id: "task-2".to_owned(),
                to_area_id: AreaId::Skipped,
                insert_at: None,
            })
            .expect("task should move to skipped");
    }

    let repository =
        SqliteTaskRepository::open(&database_path).expect("file repository should reopen");
    let service = TaskService::new(repository, FixedIdGenerator::empty());

    assert_task_shape(
        service.list_tasks().expect("persisted tasks should list"),
        [
            ("task-1", "First", AreaId::Do, TaskStatus::Active, 0),
            (
                "task-2",
                "Second",
                AreaId::Skipped,
                TaskStatus::Skipped,
                0,
            ),
        ],
    );
}

#[test]
fn order_index_converts_between_sqlite_i64_and_domain_u32_boundaries() {
    let mut repository = SqliteTaskRepository::open_in_memory().expect("repository should open");
    repository
        .connection()
        .execute(
            "INSERT INTO tasks (id, title, area_id, status, order_index)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params!["task-max", "Max", "do", "active", i64::from(u32::MAX)],
        )
        .expect("max u32 order should be accepted");

    assert_eq!(
        repository
            .list_tasks()
            .expect("max order should list")
            .first()
            .expect("task should exist")
            .order_index,
        u32::MAX
    );

    repository
        .mutate_tasks_atomically(|_| {
            Ok((
                vec![Task {
                    id: "task-written".to_owned(),
                    title: "Written".to_owned(),
                    area_id: AreaId::Do,
                    status: TaskStatus::Active,
                    order_index: u32::MAX,
                }],
                (),
            ))
        })
        .expect("u32 max should write as SQLite integer");
    let stored_order: i64 = repository
        .connection()
        .query_row(
            "SELECT order_index FROM tasks WHERE id = 'task-written'",
            [],
            |row| row.get(0),
        )
        .expect("stored order should read");
    assert_eq!(stored_order, i64::from(u32::MAX));
}

#[test]
fn schema_constraints_reject_untrimmed_title_and_allow_duplicate_area_order() {
    let repository = SqliteTaskRepository::open_in_memory().expect("repository should open");

    repository
        .connection()
        .execute(
            "INSERT INTO tasks (id, title, area_id, status, order_index)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params!["task-1", "Title", "do", "active", 0_i64],
        )
        .expect("valid task should insert");
    repository
        .connection()
        .execute(
            "INSERT INTO tasks (id, title, area_id, status, order_index)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params!["task-2", "Also title", "do", "active", 0_i64],
        )
        .expect("duplicate area/order should not be unique-constrained in issue 59");

    let error = repository
        .connection()
        .execute(
            "INSERT INTO tasks (id, title, area_id, status, order_index)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params!["task-bad", "  Bad  ", "do", "active", 1_i64],
        )
        .expect_err("untrimmed title should violate schema check");

    assert!(
        error.to_string().contains("CHECK constraint failed"),
        "unexpected SQLite error: {error}"
    );
}

fn service_with_ids<const N: usize>(
    ids: [&'static str; N],
) -> TaskService<SqliteTaskRepository, FixedIdGenerator> {
    let repository = SqliteTaskRepository::open_in_memory().expect("repository should open");
    TaskService::new(repository, FixedIdGenerator::new(ids))
}

fn create_input(title: &str, area_id: AreaId) -> CreateTaskInput {
    CreateTaskInput {
        title: title.to_owned(),
        area_id,
    }
}

fn assert_task_shape<const N: usize>(
    tasks: Vec<Task>,
    expected: [(&str, &str, AreaId, TaskStatus, u32); N],
) {
    let actual = tasks
        .iter()
        .map(|task| {
            (
                task.id.as_str(),
                task.title.as_str(),
                task.area_id,
                task.status,
                task.order_index,
            )
        })
        .collect::<Vec<_>>();
    assert_eq!(actual, expected.to_vec());
}

fn assert_error_code<T>(
    result: SiftqResult<T>,
    expected_code: ErrorCode,
    expected_message: &str,
) {
    let error = match result {
        Ok(_) => panic!("operation should fail"),
        Err(error) => error,
    };
    assert_eq!(error.code(), expected_code);
    assert_eq!(error.message(), expected_message);
}

#[derive(Debug)]
struct FixedIdGenerator {
    ids: Vec<&'static str>,
}

impl FixedIdGenerator {
    fn empty() -> Self {
        Self { ids: Vec::new() }
    }

    fn new<const N: usize>(ids: [&'static str; N]) -> Self {
        let mut ids = ids.to_vec();
        ids.reverse();
        Self { ids }
    }
}

impl IdGenerator for FixedIdGenerator {
    fn generate_id(&mut self) -> String {
        self.ids
            .pop()
            .expect("test ID generator ran out of IDs")
            .to_owned()
    }
}
