import type { AgentId, AuthorId } from "./types";

export interface AgentProfile {
  id: AuthorId;
  name: string;
  role: string;
  /** Tailwind classes for the avatar chip. */
  color: string;
  initials: string;
}

export const AGENTS: Record<AuthorId, AgentProfile> = {
  user: { id: "user", name: "You", role: "Workspace member", color: "bg-slate-600", initials: "ME" },
  exi: { id: "exi", name: "Exi", role: "Coordinator · PM", color: "bg-violet-600", initials: "Ex" },
  planner: { id: "planner", name: "Planner", role: "Scopes work & milestones", color: "bg-sky-600", initials: "Pl" },
  researcher: { id: "researcher", name: "Researcher", role: "Market & competitor intel", color: "bg-amber-600", initials: "Rs" },
  coder: { id: "coder", name: "Coder", role: "Builds & ships code", color: "bg-emerald-600", initials: "Cd" },
  marketer: { id: "marketer", name: "Marketer", role: "Positioning & campaigns", color: "bg-pink-600", initials: "Mk" },
  analyst: { id: "analyst", name: "Analyst", role: "Metrics & insight", color: "bg-teal-600", initials: "An" },
  maki: { id: "maki", name: "Maki", role: "Automation engine", color: "bg-orange-500", initials: "Mi" },
};

/** Sub-agents Exi can delegate to. */
export const SPECIALISTS: AgentId[] = ["planner", "researcher", "coder", "marketer", "analyst"];
