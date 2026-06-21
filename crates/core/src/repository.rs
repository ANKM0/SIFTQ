use crate::domain::Task;
use crate::error::SiftqResult;

pub trait TaskRepository {
    fn list_tasks(&self) -> SiftqResult<Vec<Task>>;

    fn mutate_tasks_atomically<T, F>(&mut self, operation: F) -> SiftqResult<T>
    where
        F: FnOnce(Vec<Task>) -> SiftqResult<(Vec<Task>, T)>;
}
