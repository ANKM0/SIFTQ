use crate::domain::{
    normalize_orders, normalize_task_title, status_for_area, AreaId, Task, TaskId, TaskStatus,
};
use crate::error::{SiftqError, SiftqResult};
use crate::id::IdGenerator;
use crate::repository::TaskRepository;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CreateTaskInput {
    pub title: String,
    pub area_id: AreaId,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MoveTaskInput {
    pub task_id: TaskId,
    pub to_area_id: AreaId,
    pub insert_at: Option<i64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReorderTaskInput {
    pub task_id: TaskId,
    pub to_index: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateTaskTitleInput {
    pub task_id: TaskId,
    pub title: String,
}

#[derive(Debug)]
pub struct TaskService<R, G> {
    repository: R,
    id_generator: G,
}

impl<R, G> TaskService<R, G>
where
    R: TaskRepository,
    G: IdGenerator,
{
    pub fn new(repository: R, id_generator: G) -> Self {
        Self {
            repository,
            id_generator,
        }
    }

    pub fn create_task(&mut self, input: CreateTaskInput) -> SiftqResult<Task> {
        if !input.area_id.is_matrix() {
            return Err(SiftqError::validation(
                "Tasks can only be created in matrix areas.",
            ));
        }

        let title = normalize_task_title(&input.title)?;
        let task_id = self.id_generator.generate_id();

        self.repository.mutate_tasks_atomically(|tasks| {
            let order_index = tasks
                .iter()
                .filter(|task| task.area_id == input.area_id)
                .count() as u32;
            let task = Task {
                id: task_id,
                title,
                area_id: input.area_id,
                status: status_for_area(input.area_id),
                order_index,
            };

            let mut next_tasks = tasks;
            next_tasks.push(task.clone());
            let normalized_tasks = normalize_orders(next_tasks);
            let created_task = find_task_in(&normalized_tasks, &task.id)?.clone();

            Ok((normalized_tasks, created_task))
        })
    }

    pub fn list_tasks(&self) -> SiftqResult<Vec<Task>> {
        self.repository.list_tasks()
    }

    pub fn move_task(&mut self, input: MoveTaskInput) -> SiftqResult<Task> {
        self.repository.mutate_tasks_atomically(|tasks| {
            let task = find_task_in(&tasks, &input.task_id)?.clone();

            if task.status != TaskStatus::Active && input.to_area_id.is_matrix() {
                return Err(SiftqError::validation(
                    "Terminal tasks cannot be restored to matrix areas.",
                ));
            }

            let moved_task = Task {
                area_id: input.to_area_id,
                status: status_for_area(input.to_area_id),
                ..task
            };
            let remaining_tasks = tasks
                .into_iter()
                .filter(|candidate| candidate.id != input.task_id)
                .collect::<Vec<_>>();
            let normalized_tasks = insert_task_at(
                remaining_tasks,
                moved_task,
                input.to_area_id,
                input.insert_at,
            );
            let moved_task = find_task_in(&normalized_tasks, &input.task_id)?.clone();

            Ok((normalized_tasks, moved_task))
        })
    }

    pub fn reorder_task(&mut self, input: ReorderTaskInput) -> SiftqResult<Task> {
        self.repository.mutate_tasks_atomically(|tasks| {
            let task = find_task_in(&tasks, &input.task_id)?.clone();

            if !task.area_id.is_matrix() {
                return Err(SiftqError::validation(
                    "Only matrix tasks can be reordered.",
                ));
            }

            let area_id = task.area_id;
            let remaining_tasks = tasks
                .into_iter()
                .filter(|candidate| candidate.id != input.task_id)
                .collect::<Vec<_>>();
            let normalized_tasks =
                insert_task_at(remaining_tasks, task, area_id, Some(input.to_index));
            let reordered_task = find_task_in(&normalized_tasks, &input.task_id)?.clone();

            Ok((normalized_tasks, reordered_task))
        })
    }

    pub fn update_task_title(&mut self, input: UpdateTaskTitleInput) -> SiftqResult<Task> {
        let title = normalize_task_title(&input.title)?;

        self.repository.mutate_tasks_atomically(|tasks| {
            let mut updated_task = None;
            let next_tasks = tasks
                .into_iter()
                .map(|task| {
                    if task.id == input.task_id {
                        let task = Task {
                            title: title.clone(),
                            ..task
                        };
                        updated_task = Some(task.clone());
                        task
                    } else {
                        task
                    }
                })
                .collect::<Vec<_>>();

            let missing_task_message = format!("Unknown task: {}", input.task_id);
            let updated_task =
                updated_task.ok_or_else(|| SiftqError::not_found(missing_task_message))?;

            Ok((normalize_orders(next_tasks), updated_task))
        })
    }
}

fn insert_task_at(
    tasks: Vec<Task>,
    mut task: Task,
    area_id: AreaId,
    insert_at: Option<i64>,
) -> Vec<Task> {
    let ordered_tasks = normalize_orders(tasks);
    let mut tasks_by_area: [Vec<Task>; 6] = std::array::from_fn(|_| Vec::new());

    for task in ordered_tasks {
        tasks_by_area[task.area_id.sort_index()].push(task);
    }

    task.area_id = area_id;
    let target_tasks = &mut tasks_by_area[area_id.sort_index()];
    let clamped_index = clamp_index(insert_at, target_tasks.len());
    target_tasks.insert(clamped_index, task);

    let mut result = Vec::with_capacity(tasks_by_area.iter().map(Vec::len).sum());
    for area_tasks in tasks_by_area {
        for (order_index, mut task) in area_tasks.into_iter().enumerate() {
            task.order_index = order_index as u32;
            result.push(task);
        }
    }

    result
}

fn clamp_index(index: Option<i64>, len: usize) -> usize {
    match index {
        Some(value) if value <= 0 => 0,
        Some(value) => usize::try_from(value).map_or(len, |index| index.min(len)),
        None => len,
    }
}

fn find_task_in<'a>(tasks: &'a [Task], task_id: &str) -> SiftqResult<&'a Task> {
    tasks
        .iter()
        .find(|task| task.id == task_id)
        .ok_or_else(|| SiftqError::not_found(format!("Unknown task: {task_id}")))
}
