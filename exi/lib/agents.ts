import type { AgentId, SpecialistId, User } from "./types";

export interface Profile {
  id: string;
  name: string;
  role: string;
  /** Tailwind classes for the avatar chip. */
  color: string;
  initials: string;
  isAgent: boolean;
}

export const AGENTS: Record<AgentId, Profile> = {
  exi: { id: "exi", name: "Exi", role: "Coordinator · PM", color: "bg-violet-600", initials: "Ex", isAgent: true },
  planner: { id: "planner", name: "Planner", role: "Scopes work & milestones", color: "bg-sky-600", initials: "Pl", isAgent: true },
  researcher: { id: "researcher", name: "Researcher", role: "Market & competitor intel (web search)", color: "bg-amber-600", initials: "Rs", isAgent: true },
  coder: { id: "coder", name: "Coder", role: "Technical design & code", color: "bg-emerald-600", initials: "Cd", isAgent: true },
  marketer: { id: "marketer", name: "Marketer", role: "Positioning & campaigns", color: "bg-pink-600", initials: "Mk", isAgent: true },
  analyst: { id: "analyst", name: "Analyst", role: "Metrics & insight", color: "bg-teal-600", initials: "An", isAgent: true },
  maki: { id: "maki", name: "Maki", role: "Automation engine", color: "bg-orange-500", initials: "Mi", isAgent: true },
};

export const SPECIALISTS: SpecialistId[] = ["planner", "researcher", "coder", "marketer", "analyst"];

const USER_COLORS = ["bg-slate-600", "bg-indigo-500", "bg-rose-500", "bg-cyan-600", "bg-lime-600", "bg-purple-500", "bg-yellow-600"];

export function isAgent(id: string): id is AgentId {
  return id in AGENTS;
}

export function profileOf(id: string, users: Record<string, User>): Profile {
  if (isAgent(id)) return AGENTS[id];
  const u = users[id];
  const name = u?.displayName ?? "Former member";
  const hash = [...id].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
  const initials = name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return { id, name, role: u ? `@${u.username}` : "", color: USER_COLORS[hash % USER_COLORS.length], initials, isAgent: false };
}
