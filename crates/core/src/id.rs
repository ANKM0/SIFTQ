use uuid::Uuid;

use crate::domain::TaskId;

pub trait IdGenerator {
    fn generate_id(&mut self) -> TaskId;
}

#[derive(Debug, Default, Clone, Copy)]
pub struct UuidGenerator;

impl IdGenerator for UuidGenerator {
    fn generate_id(&mut self) -> TaskId {
        Uuid::new_v4().to_string()
    }
}
