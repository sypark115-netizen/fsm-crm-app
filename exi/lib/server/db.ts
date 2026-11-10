import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";

// One SQLite file for the whole workspace. Fine for a single self-hosted node;
// swap for Postgres when you need several app servers.

const DATA_DIR = path.resolve(/*turbopackIgnore: true*/ process.cwd(), process.env.EXI_DATA_DIR || "data");

const MIGRATIONS: string[] = [
  `
  CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );
  CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
  );
  CREATE TABLE channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('channel','dm')),
    topic TEXT,
    peer TEXT,
    owner_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL
  );
  CREATE UNIQUE INDEX channels_public_name ON channels(name) WHERE kind = 'channel';
  CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    run_id TEXT,
    automation_id TEXT,
    attachments TEXT
  );
  CREATE INDEX messages_channel_time ON messages(channel_id, created_at);
  CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    started_at INTEGER NOT NULL
  );
  CREATE INDEX runs_channel_time ON runs(channel_id, started_at);
  CREATE TABLE automations (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
  );
  CREATE TABLE feedback (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );
  CREATE TABLE files (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mime TEXT NOT NULL,
    size INTEGER NOT NULL,
    uploaded_by TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );
  `,
];

function open(): Database.Database {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const db = new Database(path.join(DATA_DIR, "exi.db"));
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.pragma("busy_timeout = 5000");

  const current = db.pragma("user_version", { simple: true }) as number;
  for (let v = current; v < MIGRATIONS.length; v++) {
    db.transaction(() => {
      db.exec(MIGRATIONS[v]);
      db.pragma(`user_version = ${v + 1}`);
    })();
  }
  return db;
}

// Opened lazily on first use (never at build time), and cached on globalThis
// so dev-server hot reloads don't open a second handle.
const g = globalThis as unknown as { __exiDb?: Database.Database };
const getDb = () => (g.__exiDb ??= open());

export const db = new Proxy({} as Database.Database, {
  get(_target, prop) {
    const real = getDb();
    const value = Reflect.get(real, prop, real);
    return typeof value === "function" ? value.bind(real) : value;
  },
});

export const UPLOAD_DIR = path.join(DATA_DIR, "uploads");
