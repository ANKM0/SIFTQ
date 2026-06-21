use std::path::Path;
use std::str::FromStr;

use rusqlite::{params, Connection, Transaction};

use crate::domain::{compare_tasks, AreaId, Task, TaskStatus, TASK_TITLE_MAX_CHARS};
use crate::error::{SiftqError, SiftqResult};
use crate::repository::TaskRepository;

const CURRENT_SCHEMA_VERSION: i64 = 1;

#[derive(Debug)]
pub struct SqliteTaskRepository {
    connection: Connection,
}

impl SqliteTaskRepository {
    pub fn open(path: impl AsRef<Path>) -> SiftqResult<Self> {
        let connection = Connection::open(path).map_err(|error| {
            SiftqError::storage(format!("Failed to open SQLite database: {error}"))
        })?;
        Self::from_connection(connection)
    }

    pub fn open_in_memory() -> SiftqResult<Self> {
        let connection = Connection::open_in_memory().map_err(|error| {
            SiftqError::storage(format!("Failed to open in-memory SQLite database: {error}"))
        })?;
        Self::from_connection(connection)
    }

    pub fn from_connection(connection: Connection) -> SiftqResult<Self> {
        let repository = Self { connection };
        repository.migrate()?;
        Ok(repository)
    }

    pub fn user_version(&self) -> SiftqResult<i64> {
        user_version(&self.connection)
    }

    pub fn connection(&self) -> &Connection {
        &self.connection
    }

    fn migrate(&self) -> SiftqResult<()> {
        match self.user_version()? {
            0 => {
                self.connection
                    .execute_batch(INITIAL_SCHEMA_SQL)
                    .map_err(|error| {
                        SiftqError::migration(format!(
                            "Failed to apply initial SQLite schema migration: {error}"
                        ))
                    })?;
                Ok(())
            }
            CURRENT_SCHEMA_VERSION => Ok(()),
            version => Err(SiftqError::migration(format!(
                "Unsupported SQLite schema version: {version}"
            ))),
        }
    }
}

impl TaskRepository for SqliteTaskRepository {
    fn list_tasks(&self) -> SiftqResult<Vec<Task>> {
        read_tasks(&self.connection)
    }

    fn mutate_tasks_atomically<T, F>(&mut self, operation: F) -> SiftqResult<T>
    where
        F: FnOnce(Vec<Task>) -> SiftqResult<(Vec<Task>, T)>,
    {
        let transaction = self
            .connection
            .transaction()
            .map_err(|error| {
                SiftqError::storage(format!("Failed to start transaction: {error}"))
            })?;
        let tasks = read_tasks(&transaction)?;
        let (mut next_tasks, output) = operation(tasks)?;

        next_tasks.sort_by(compare_tasks);
        replace_tasks(&transaction, &next_tasks)?;
        transaction
            .commit()
            .map_err(|error| {
                SiftqError::storage(format!("Failed to commit transaction: {error}"))
            })?;

        Ok(output)
    }
}

fn user_version(connection: &Connection) -> SiftqResult<i64> {
    connection
        .query_row("PRAGMA user_version", [], |row| row.get(0))
        .map_err(|error| {
            SiftqError::migration(format!("Failed to read schema version: {error}"))
        })
}

fn read_tasks(connection: &Connection) -> SiftqResult<Vec<Task>> {
    let mut statement = connection
        .prepare(
            "SELECT id, title, area_id, status, order_index
             FROM tasks
             ORDER BY
               CASE area_id
                 WHEN 'do' THEN 0
                 WHEN 'schedule' THEN 1
                 WHEN 'delegate' THEN 2
                 WHEN 'eliminate' THEN 3
                 WHEN 'skipped' THEN 4
                 WHEN 'done' THEN 5
                 ELSE 99
               END,
               order_index ASC,
               id ASC",
        )
        .map_err(|error| SiftqError::storage(format!("Failed to prepare task query: {error}")))?;
    let rows = statement
        .query_map([], |row| {
            let id: String = row.get(0)?;
            let title: String = row.get(1)?;
            let area_id: String = row.get(2)?;
            let status: String = row.get(3)?;
            let order_index: i64 = row.get(4)?;

            Ok((id, title, area_id, status, order_index))
        })
        .map_err(|error| SiftqError::storage(format!("Failed to query tasks: {error}")))?;

    let mut tasks = Vec::new();
    for row in rows {
        let (id, title, area_id, status, order_index) = row
            .map_err(|error| SiftqError::storage(format!("Failed to read task row: {error}")))?;
        tasks.push(Task {
            id,
            title,
            area_id: AreaId::from_str(&area_id)?,
            status: TaskStatus::from_str(&status)?,
            order_index: u32::try_from(order_index).map_err(|_| {
                SiftqError::storage(format!(
                    "Stored task order_index is outside u32 range: {order_index}"
                ))
            })?,
        });
    }

    Ok(tasks)
}

fn replace_tasks(transaction: &Transaction<'_>, tasks: &[Task]) -> SiftqResult<()> {
    transaction
        .execute("DELETE FROM tasks", [])
        .map_err(|error| SiftqError::storage(format!("Failed to clear tasks: {error}")))?;

    let mut statement = transaction
        .prepare(
            "INSERT INTO tasks (id, title, area_id, status, order_index)
             VALUES (?1, ?2, ?3, ?4, ?5)",
        )
        .map_err(|error| SiftqError::storage(format!("Failed to prepare task write: {error}")))?;

    for task in tasks {
        statement
            .execute(params![
                &task.id,
                &task.title,
                task.area_id.as_str(),
                task.status.as_str(),
                i64::from(task.order_index),
            ])
            .map_err(|error| SiftqError::storage(format!("Failed to write task: {error}")))?;
    }

    Ok(())
}

const INITIAL_SCHEMA_SQL: &str = r#"
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
  title TEXT NOT NULL CHECK (
    length(trim(title)) > 0
    AND length(title) <= 256
    AND title = trim(title)
  ),
  area_id TEXT NOT NULL CHECK (
    area_id IN ('do', 'schedule', 'delegate', 'eliminate', 'done', 'skipped')
  ),
  status TEXT NOT NULL CHECK (status IN ('active', 'done', 'skipped')),
  order_index INTEGER NOT NULL CHECK (
    order_index >= 0
    AND order_index <= 4294967295
  )
);

PRAGMA user_version = 1;
"#;

const _: () = assert!(TASK_TITLE_MAX_CHARS == 256);
