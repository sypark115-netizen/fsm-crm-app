import { uid } from "../ids";
import type {
  AgentId,
  AgentRun,
  Attachment,
  Automation,
  Channel,
  FeedbackItem,
  Message,
  User,
} from "../types";
import { publish } from "./bus";
import { db } from "./db";

// Data access + change notification. Every write that other users should see
// publishes a WorkspaceEvent; DM-scoped writes are published only to the owner.

/* ---------------------------------- users --------------------------------- */

interface UserRow {
  id: string;
  username: string;
  display_name: string;
  password_hash: string;
}

const toUser = (r: UserRow): User => ({ id: r.id, username: r.username, displayName: r.display_name });

export function countUsers(): number {
  return (db.prepare("SELECT COUNT(*) AS n FROM users").get() as { n: number }).n;
}

export function listUsers(): User[] {
  return (db.prepare("SELECT * FROM users ORDER BY created_at").all() as UserRow[]).map(toUser);
}

export function getUserById(id: string): User | null {
  const r = db.prepare("SELECT * FROM users WHERE id = ?").get(id) as UserRow | undefined;
  return r ? toUser(r) : null;
}

export function getUserWithHash(username: string): (User & { passwordHash: string }) | null {
  const r = db.prepare("SELECT * FROM users WHERE username = ?").get(username) as UserRow | undefined;
  return r ? { ...toUser(r), passwordHash: r.password_hash } : null;
}

export function createUser(username: string, displayName: string, passwordHash: string): User {
  const id = uid("usr");
  const now = Date.now();
  db.transaction(() => {
    db.prepare("INSERT INTO users (id, username, display_name, password_hash, created_at) VALUES (?,?,?,?,?)").run(
      id,
      username,
      displayName,
      passwordHash,
      now,
    );
    // Every member gets private DMs with Exi and Maki.
    const dm = db.prepare(
      "INSERT INTO channels (id, name, kind, peer, owner_id, created_at) VALUES (?,?,?,?,?,?)",
    );
    dm.run(uid("dm"), "Exi", "dm", "exi", id, now);
    dm.run(uid("dm"), "Maki", "dm", "maki", id, now);
  })();
  const user = { id, username, displayName };
  publish({ type: "user.join", user });
  return user;
}

/* -------------------------------- channels -------------------------------- */

interface ChannelRow {
  id: string;
  name: string;
  kind: "channel" | "dm";
  topic: string | null;
  peer: string | null;
  owner_id: string | null;
}

const toChannel = (r: ChannelRow): Channel => ({
  id: r.id,
  name: r.name,
  kind: r.kind,
  topic: r.topic ?? undefined,
  peer: (r.peer as AgentId) ?? undefined,
  ownerId: r.owner_id ?? undefined,
});

export function listChannelsFor(userId: string): Channel[] {
  return (
    db
      .prepare("SELECT * FROM channels WHERE kind = 'channel' OR owner_id = ? ORDER BY kind, created_at")
      .all(userId) as ChannelRow[]
  ).map(toChannel);
}

export function getChannel(id: string): Channel | null {
  const r = db.prepare("SELECT * FROM channels WHERE id = ?").get(id) as ChannelRow | undefined;
  return r ? toChannel(r) : null;
}

export function canAccess(userId: string, channel: Channel | null): channel is Channel {
  return !!channel && (channel.kind === "channel" || channel.ownerId === userId);
}

export function createChannel(name: string, topic?: string): Channel {
  const channel: Channel = { id: uid("ch"), name, kind: "channel", topic };
  db.prepare("INSERT INTO channels (id, name, kind, topic, created_at) VALUES (?,?,?,?,?)").run(
    channel.id,
    name,
    "channel",
    topic ?? null,
    Date.now(),
  );
  publish({ type: "channel.create", channel });
  return channel;
}

export function ensureDefaultChannels() {
  const n = (db.prepare("SELECT COUNT(*) AS n FROM channels WHERE kind = 'channel'").get() as { n: number }).n;
  if (n > 0) return;
  const general = createChannel("general", "Company-wide — ask Exi anything");
  createChannel("growth-marketing", "Campaigns, SEO, competitor watch");
  const eng = createChannel("engineering", "Builds, incidents, code review");
  insertMessage({
    channelId: general.id,
    author: "exi",
    text:
      "👋 Hi, I'm **Exi** — your coordinator agent.\n\nPost a request in any channel and I'll plan it, delegate to the specialists " +
      "(**Planner**, **Researcher**, **Coder**, **Marketer**, **Analyst**) and report back here.\n\n" +
      "Try: `Analyze competitors in the AI agent market and suggest our positioning`",
  });
  createAutomation({
    name: "Incident triage",
    trigger: { type: "event", event: "message_contains", keyword: "outage" },
    channelId: eng.id,
    command: "Triage the reported outage: likely root cause, blast radius and a fix plan",
    enabled: true,
  });
}

/** Who should receive events about this channel: everyone, or the DM owner. */
export function audienceOf(channelId: string): string | undefined {
  const c = getChannel(channelId);
  return c?.kind === "dm" ? c.ownerId : undefined;
}

/* -------------------------------- messages -------------------------------- */

interface MessageRow {
  id: string;
  channel_id: string;
  author: string;
  text: string;
  created_at: number;
  run_id: string | null;
  automation_id: string | null;
  attachments: string | null;
}

const toMessage = (r: MessageRow): Message => ({
  id: r.id,
  channelId: r.channel_id,
  author: r.author,
  text: r.text,
  createdAt: r.created_at,
  runId: r.run_id ?? undefined,
  automationId: r.automation_id ?? undefined,
  attachments: r.attachments ? (JSON.parse(r.attachments) as Attachment[]) : undefined,
});

/** Latest `perChannel` messages of each channel the user can see. */
export function listMessagesFor(userId: string, perChannel = 200): Message[] {
  const rows = db
    .prepare(
      `SELECT * FROM (
         SELECT m.*, ROW_NUMBER() OVER (PARTITION BY m.channel_id ORDER BY m.created_at DESC) AS rn
         FROM messages m JOIN channels c ON c.id = m.channel_id
         WHERE c.kind = 'channel' OR c.owner_id = ?
       ) WHERE rn <= ? ORDER BY created_at`,
    )
    .all(userId, perChannel) as MessageRow[];
  return rows.map(toMessage);
}

export function recentMessages(channelId: string, limit = 12): Message[] {
  return (
    db
      .prepare("SELECT * FROM messages WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?")
      .all(channelId, limit) as MessageRow[]
  )
    .map(toMessage)
    .reverse();
}

export function insertMessage(m: Omit<Message, "id" | "createdAt"> & { id?: string }): Message {
  const message: Message = { ...m, id: m.id ?? uid("m"), createdAt: Date.now() };
  db.prepare(
    "INSERT INTO messages (id, channel_id, author, text, created_at, run_id, automation_id, attachments) VALUES (?,?,?,?,?,?,?,?)",
  ).run(
    message.id,
    message.channelId,
    message.author,
    message.text,
    message.createdAt,
    message.runId ?? null,
    message.automationId ?? null,
    message.attachments?.length ? JSON.stringify(message.attachments) : null,
  );
  publish({ type: "message.upsert", message }, audienceOf(message.channelId));
  return message;
}

/** Live update while streaming: broadcast only. */
export function broadcastMessageDraft(message: Message) {
  publish({ type: "message.upsert", message: { ...message, streaming: true } }, audienceOf(message.channelId));
}

export function finalizeMessageText(message: Message, text: string): Message {
  db.prepare("UPDATE messages SET text = ? WHERE id = ?").run(text, message.id);
  const done = { ...message, text, streaming: false };
  publish({ type: "message.upsert", message: done }, audienceOf(message.channelId));
  return done;
}

/* ---------------------------------- runs ---------------------------------- */

export function listRunsFor(userId: string, limit = 200): AgentRun[] {
  return (
    db
      .prepare(
        `SELECT r.data FROM runs r JOIN channels c ON c.id = r.channel_id
         WHERE c.kind = 'channel' OR c.owner_id = ?
         ORDER BY r.started_at DESC LIMIT ?`,
      )
      .all(userId, limit) as { data: string }[]
  )
    .map((r) => JSON.parse(r.data) as AgentRun)
    .reverse();
}

export function saveRun(run: AgentRun) {
  db.prepare(
    "INSERT INTO runs (id, channel_id, data, started_at) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
  ).run(run.id, run.channelId, JSON.stringify(run), run.startedAt);
  publish({ type: "run.upsert", run }, audienceOf(run.channelId));
}

/** Runs left mid-flight by a crash/restart can't resume — close them out. */
export function failInterruptedRuns() {
  const rows = db.prepare("SELECT data FROM runs").all() as { data: string }[];
  for (const { data } of rows) {
    const run = JSON.parse(data) as AgentRun;
    if (run.status === "planning" || run.status === "running") {
      saveRun({ ...run, status: "failed", error: "Interrupted by server restart", finishedAt: Date.now() });
    }
  }
}

/* ------------------------------- automations ------------------------------ */

export function listAutomations(): Automation[] {
  return (db.prepare("SELECT data FROM automations").all() as { data: string }[])
    .map((r) => JSON.parse(r.data) as Automation)
    .sort((a, b) => a.createdAt - b.createdAt);
}

export function getAutomation(id: string): Automation | null {
  const r = db.prepare("SELECT data FROM automations WHERE id = ?").get(id) as { data: string } | undefined;
  return r ? (JSON.parse(r.data) as Automation) : null;
}

export function createAutomation(
  a: Omit<Automation, "id" | "createdAt" | "runCount">,
): Automation {
  const automation: Automation = { ...a, id: uid("auto"), createdAt: Date.now(), runCount: 0 };
  db.prepare("INSERT INTO automations (id, data) VALUES (?, ?)").run(automation.id, JSON.stringify(automation));
  publish({ type: "automation.upsert", automation }, audienceOf(automation.channelId));
  return automation;
}

export function updateAutomation(id: string, patch: Partial<Automation>): Automation | null {
  const cur = getAutomation(id);
  if (!cur) return null;
  const next = { ...cur, ...patch, id };
  db.prepare("UPDATE automations SET data = ? WHERE id = ?").run(JSON.stringify(next), id);
  publish({ type: "automation.upsert", automation: next }, audienceOf(next.channelId));
  return next;
}

export function deleteAutomation(id: string) {
  const cur = getAutomation(id);
  db.prepare("DELETE FROM automations WHERE id = ?").run(id);
  publish({ type: "automation.delete", id }, cur ? audienceOf(cur.channelId) : undefined);
}

/** Automations whose target channel the user can see (DM rules stay private). */
export function listAutomationsFor(userId: string): Automation[] {
  return listAutomations().filter((a) => canAccess(userId, getChannel(a.channelId)));
}

/* -------------------------------- feedback -------------------------------- */

export function listFeedback(limit = 50): FeedbackItem[] {
  return (
    db.prepare("SELECT data FROM feedback ORDER BY created_at DESC LIMIT ?").all(limit) as { data: string }[]
  ).map((r) => JSON.parse(r.data) as FeedbackItem);
}

export function saveFeedback(item: FeedbackItem) {
  db.prepare(
    "INSERT INTO feedback (id, data, created_at) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
  ).run(item.id, JSON.stringify(item), item.createdAt);
  publish({ type: "feedback.upsert", item });
}

/* ---------------------------------- files --------------------------------- */

export function insertFile(f: { id: string; name: string; mime: string; size: number; uploadedBy: string }) {
  db.prepare("INSERT INTO files (id, name, mime, size, uploaded_by, created_at) VALUES (?,?,?,?,?,?)").run(
    f.id,
    f.name,
    f.mime,
    f.size,
    f.uploadedBy,
    Date.now(),
  );
}

export function getFile(id: string): { id: string; name: string; mime: string; size: number } | null {
  return (
    (db.prepare("SELECT id, name, mime, size FROM files WHERE id = ?").get(id) as
      | { id: string; name: string; mime: string; size: number }
      | undefined) ?? null
  );
}
