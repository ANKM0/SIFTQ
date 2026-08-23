CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('do', 'done', 'skip')),
  area INTEGER NOT NULL CHECK (area IN (1, 2, 3, 4)),
  "order" INTEGER NOT NULL,
  version INTEGER NOT NULL
);
