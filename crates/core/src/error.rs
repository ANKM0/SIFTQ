use std::error::Error;
use std::fmt::{self, Display};

pub type SiftqResult<T> = Result<T, SiftqError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorCode {
    Validation,
    NotFound,
    Storage,
    Migration,
    Internal,
}

impl ErrorCode {
    pub fn as_str(self) -> &'static str {
        match self {
            ErrorCode::Validation => "VALIDATION",
            ErrorCode::NotFound => "NOT_FOUND",
            ErrorCode::Storage => "STORAGE",
            ErrorCode::Migration => "MIGRATION",
            ErrorCode::Internal => "INTERNAL",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SiftqError {
    code: ErrorCode,
    message: String,
}

impl SiftqError {
    pub fn validation(message: impl Into<String>) -> Self {
        Self::new(ErrorCode::Validation, message)
    }

    pub fn not_found(message: impl Into<String>) -> Self {
        Self::new(ErrorCode::NotFound, message)
    }

    pub fn storage(message: impl Into<String>) -> Self {
        Self::new(ErrorCode::Storage, message)
    }

    pub fn migration(message: impl Into<String>) -> Self {
        Self::new(ErrorCode::Migration, message)
    }

    pub fn internal(message: impl Into<String>) -> Self {
        Self::new(ErrorCode::Internal, message)
    }

    pub fn code(&self) -> ErrorCode {
        self.code
    }

    pub fn message(&self) -> &str {
        &self.message
    }

    fn new(code: ErrorCode, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }
}

impl Display for SiftqError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code.as_str(), self.message)
    }
}

impl Error for SiftqError {}
