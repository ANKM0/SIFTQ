ALTER TABLE ideas ADD COLUMN id TEXT;
ALTER TABLE ideas ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local';
UPDATE ideas SET id = lower(hex(randomblob(16))) WHERE id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ideas_id_idx ON ideas (id);
