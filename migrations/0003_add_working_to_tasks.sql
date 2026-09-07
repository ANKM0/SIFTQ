-- Migration number: 0003
ALTER TABLE tasks ADD COLUMN working INTEGER NOT NULL DEFAULT 0 CHECK (working IN (0, 1));
