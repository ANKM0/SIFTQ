use std::cmp::Ordering;
use std::str::FromStr;

use crate::error::{SiftqError, SiftqResult};

pub const TASK_TITLE_MAX_CHARS: usize = 256;

pub type TaskId = String;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AreaId {
    Do,
    Schedule,
    Delegate,
    Eliminate,
    Skipped,
    Done,
}

impl AreaId {
    pub const ALL_IN_DISPLAY_ORDER: [AreaId; 6] = [
        AreaId::Do,
        AreaId::Schedule,
        AreaId::Delegate,
        AreaId::Eliminate,
        AreaId::Skipped,
        AreaId::Done,
    ];

    pub fn as_str(self) -> &'static str {
        match self {
            AreaId::Do => "do",
            AreaId::Schedule => "schedule",
            AreaId::Delegate => "delegate",
            AreaId::Eliminate => "eliminate",
            AreaId::Skipped => "skipped",
            AreaId::Done => "done",
        }
    }

    pub fn is_matrix(self) -> bool {
        matches!(
            self,
            AreaId::Do | AreaId::Schedule | AreaId::Delegate | AreaId::Eliminate
        )
    }

    pub fn sort_index(self) -> usize {
        Self::ALL_IN_DISPLAY_ORDER
            .iter()
            .position(|area| *area == self)
            .expect("area display order must contain every area")
    }
}

impl FromStr for AreaId {
    type Err = SiftqError;

    fn from_str(value: &str) -> SiftqResult<Self> {
        match value {
            "do" => Ok(AreaId::Do),
            "schedule" => Ok(AreaId::Schedule),
            "delegate" => Ok(AreaId::Delegate),
            "eliminate" => Ok(AreaId::Eliminate),
            "skipped" => Ok(AreaId::Skipped),
            "done" => Ok(AreaId::Done),
            _ => Err(SiftqError::storage(format!(
                "Unknown task area in storage: {value}"
            ))),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TaskStatus {
    Active,
    Done,
    Skipped,
}

impl TaskStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            TaskStatus::Active => "active",
            TaskStatus::Done => "done",
            TaskStatus::Skipped => "skipped",
        }
    }
}

impl FromStr for TaskStatus {
    type Err = SiftqError;

    fn from_str(value: &str) -> SiftqResult<Self> {
        match value {
            "active" => Ok(TaskStatus::Active),
            "done" => Ok(TaskStatus::Done),
            "skipped" => Ok(TaskStatus::Skipped),
            _ => Err(SiftqError::storage(format!(
                "Unknown task status in storage: {value}"
            ))),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Task {
    pub id: TaskId,
    pub title: String,
    pub area_id: AreaId,
    pub status: TaskStatus,
    pub order_index: u32,
}

pub fn normalize_task_title(raw_title: &str) -> SiftqResult<String> {
    let title = raw_title.trim();

    if title.is_empty() {
        return Err(SiftqError::validation("Task title must not be empty."));
    }

    if title.chars().count() > TASK_TITLE_MAX_CHARS {
        return Err(SiftqError::validation(format!(
            "Task title must be {TASK_TITLE_MAX_CHARS} characters or less."
        )));
    }

    Ok(title.to_owned())
}

pub fn status_for_area(area_id: AreaId) -> TaskStatus {
    match area_id {
        AreaId::Done => TaskStatus::Done,
        AreaId::Skipped => TaskStatus::Skipped,
        AreaId::Do | AreaId::Schedule | AreaId::Delegate | AreaId::Eliminate => TaskStatus::Active,
    }
}

pub(crate) fn compare_tasks(left: &Task, right: &Task) -> Ordering {
    left.area_id
        .sort_index()
        .cmp(&right.area_id.sort_index())
        .then_with(|| left.order_index.cmp(&right.order_index))
        .then_with(|| left.id.cmp(&right.id))
}

pub(crate) fn normalize_orders(mut tasks: Vec<Task>) -> Vec<Task> {
    tasks.sort_by(compare_tasks);

    let mut next_order_by_area = [0_u32; 6];
    for task in &mut tasks {
        let area_index = task.area_id.sort_index();
        task.order_index = next_order_by_area[area_index];
        next_order_by_area[area_index] += 1;
    }

    tasks
}
