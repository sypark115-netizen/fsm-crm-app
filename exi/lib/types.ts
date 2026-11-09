// Domain model for the Exi workspace. Everything here is serialisable so the
// whole workspace can be persisted to localStorage (or swapped for a DB later).

export type AgentId =
  | "exi"
  | "planner"
  | "researcher"
  | "coder"
  | "marketer"
  | "analyst"
  | "maki";

export type AuthorId = AgentId | "user";

export interface Channel {
  id: string;
  name: string;
  kind: "channel" | "dm";
  topic?: string;
  /** For DMs: who the conversation is with. */
  peer?: AgentId;
}

export interface Attachment {
  id: string;
  name: string;
  size: number;
  mime: string;
  /** Small images only — larger files keep metadata alone. */
  dataUrl?: string;
}

export interface Message {
  id: string;
  channelId: string;
  author: AuthorId;
  text: string;
  createdAt: number;
  runId?: string;
  attachments?: Attachment[];
  /** Messages posted by automation carry the rule that fired them. */
  automationId?: string;
}

export type StepStatus = "queued" | "working" | "done";

export interface RunStep {
  id: string;
  agent: AgentId;
  title: string;
  detail: string;
  output: string;
  status: StepStatus;
  startedAt?: number;
  finishedAt?: number;
}

export type RunStatus = "planning" | "running" | "done" | "failed";

export interface AgentRun {
  id: string;
  channelId: string;
  command: string;
  status: RunStatus;
  source?: "claude" | "mock";
  summary?: string;
  steps: RunStep[];
  startedAt: number;
  finishedAt?: number;
  error?: string;
  automationId?: string;
}

/** What a planner (mock or Claude) returns: the plan plus each step's result. */
export interface ExiPlan {
  summary: string;
  steps: { agent: Exclude<AgentId, "exi" | "maki">; title: string; detail: string; output: string }[];
  finalReport: string;
  source: "claude" | "mock";
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
  status: "received" | "triaging" | "building" | "shipped";
  version?: string;
  log: FeedbackLogEntry[];
}

export interface WorkspaceState {
  channels: Channel[];
  messages: Message[];
  runs: AgentRun[];
  automations: Automation[];
  feedback: FeedbackItem[];
  activeChannelId: string;
  appVersion: string;
}
