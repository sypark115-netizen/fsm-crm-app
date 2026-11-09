import { z } from "zod";
import type { AgentId } from "@/lib/types";

export const runtime = "nodejs";

const Body = z.object({ text: z.string().min(3).max(2000), currentVersion: z.string().default("0.1.0") });

function bump(version: string, kind: "minor" | "patch"): string {
  const [maj, min, pat] = version.split(".").map((n) => Number(n) || 0);
  return kind === "minor" ? `${maj}.${min + 1}.0` : `${maj}.${min}.${pat + 1}`;
}

/**
 * POST /api/feedback — the self-improvement loop. An agent triages the feedback,
 * specs a change, "implements" it and cuts a release. Returned as a timed log the
 * client replays so it reads like a live iteration feed.
 */
export async function POST(request: Request) {
  const parsed = Body.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return Response.json({ error: "Feedback must be 3–2000 characters" }, { status: 400 });

  const { text, currentVersion } = parsed.data;
  const isBug = /bug|broken|error|crash|slow|doesn'?t work|오류|버그|느려/i.test(text);
  const kind = isBug ? "patch" : "minor";
  const version = bump(currentVersion, kind);
  const area =
    /sidebar|channel|dm/i.test(text) ? "Sidebar"
    : /maki|automation|schedule|cron/i.test(text) ? "Maki automations"
    : /agent|exi|panel/i.test(text) ? "Agent orchestration"
    : /chat|message|markdown|file/i.test(text) ? "Chat"
    : "General UX";

  const short = text.length > 60 ? `${text.slice(0, 57)}…` : text;
  const log: { delayMs: number; agent: AgentId; text: string }[] = [
    { delayMs: 300, agent: "exi", text: `Received feedback: “${short}”. Routing to Analyst for triage.` },
    { delayMs: 1200, agent: "analyst", text: `Classified as **${isBug ? "bug" : "enhancement"}** in _${area}_. Priority: ${isBug ? "P1" : "P2"}.` },
    { delayMs: 1300, agent: "planner", text: `Wrote spec: acceptance criteria + rollout behind \`ff_${area.toLowerCase().replace(/\s+/g, "_")}\`.` },
    { delayMs: 1600, agent: "coder", text: `Opened change set (3 files), tests green ✅.` },
    { delayMs: 1100, agent: "exi", text: `Shipped **v${version}** to the workspace (${kind} release). Thanks for making Exi better!` },
  ];

  return Response.json({ version, kind, area, log });
}
