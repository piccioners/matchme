CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL,
  name TEXT NOT NULL,
  table_number TEXT NOT NULL,
  gender TEXT NOT NULL,
  like TEXT NOT NULL,
  interests_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_event ON users(event_id);
