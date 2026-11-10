// Domain model shared by server and client. Everything is JSON-serialisable.

export type AgentId = "exi" | "planner" | "researcher" | "coder" | "marketer" | "analyst" | "maki";
export type SpecialistId = Exclude<AgentId, "exi" | "maki">;

/** An agent id, or a user id ("usr_…"). */
export type AuthorId = string;

export interface User {
  id: string;
  username: string;
  displayName: string;
}

export interface Channel {
  id: string;
  name: string;
  kind: "channel" | "dm";
  topic?: string;
  /** DMs: the agent on the other side. */
  peer?: AgentId;
  /** DMs are private to their owner. */
  ownerId?: string;
}

export interface Attachment {
  id: string;
  name: string;
  size: number;
  mime: string;
  url: string;
}

export interface Message {
  id: string;
  channelId: string;
  author: AuthorId;
  text: string;
  createdAt: number;
  runId?: string;
  attachments?: Attachment[];
  automationId?: string;
  /** True while an agent is still streaming this message. */
  streaming?: boolean;
}

export type StepStatus = "queued" | "working" | "done" | "failed";

export interface RunStep {
  id: string;
  agent: SpecialistId;
  title: string;
  detail: string;
  status: StepStatus;
  startedAt?: number;
  finishedAt?: number;
  messageId?: string;
}

export type RunStatus = "planning" | "running" | "done" | "failed";

export interface AgentRun {
  id: string;
  channelId: string;
  command: string;
  status: RunStatus;
  source: "claude" | "mock";
  summary?: string;
  steps: RunStep[];
  startedAt: number;
  finishedAt?: number;
  error?: string;
  automationId?: string;
  requestedBy?: string;
}

export type AutomationTrigger =
  | { type: "schedule"; cron: string }
  | { type: "event"; event: "message_contains"; keyword: string; channelId?: string };

export interface Automation {
  id: string;
  name: string;
  trigger: AutomationTrigger;
  channelId: string;
  command: string;
  enabled: boolean;
  createdAt: number;
  createdBy?: string;
  lastRunAt?: number;
  runCount: number;
}

export interface FeedbackLogEntry {
  at: number;
  agent: AgentId;
  text: string;
}

export interface FeedbackItem {
  id: string;
  text: string;
  createdAt: number;
  createdBy?: string;
  status: "received" | "triaging" | "filed" | "failed";
  title?: string;
  kind?: "bug" | "enhancement";
  priority?: "P0" | "P1" | "P2" | "P3";
  issueUrl?: string;
  log: FeedbackLogEntry[];
}

export interface ServerStatus {
  planner: "claude" | "mock";
  github: boolean;
  model?: string;
}

/** Everything the client needs on load. */
export interface Bootstrap {
  me: User;
  users: User[];
  channels: Channel[];
  messages: Message[];
  runs: AgentRun[];
  automations: Automation[];
  feedback: FeedbackItem[];
  status: ServerStatus;
}

/** Real-time events pushed over SSE. */
export type WorkspaceEvent =
  | { type: "message.upsert"; message: Message }
  | { type: "run.upsert"; run: AgentRun }
  | { type: "channel.create"; channel: Channel }
  | { type: "automation.upsert"; automation: Automation }
  | { type: "automation.delete"; id: string }
  | { type: "feedback.upsert"; item: FeedbackItem }
  | { type: "user.join"; user: User };
