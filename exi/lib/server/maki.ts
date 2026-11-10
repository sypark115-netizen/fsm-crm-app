import { firedBetween } from "../maki/cron";
import type { Automation } from "../types";
import { startRun } from "./orchestrator";
import { insertMessage, listAutomations, updateAutomation } from "./repo";

// Maki — the automation engine. Runs inside the Next.js server process
// (started from instrumentation.ts), so it works on any long-running Node host.

const TICK_MS = 30_000;

export function triggerAutomation(a: Automation, reason: string, requestedBy?: string) {
  updateAutomation(a.id, { lastRunAt: Date.now(), runCount: a.runCount + 1 });
  insertMessage({
    channelId: a.channelId,
    author: "maki",
    automationId: a.id,
    text: `⚡ **${a.name}** triggered (${reason}). Handing off to Exi: _${a.command}_`,
  });
  startRun({ channelId: a.channelId, command: a.command, automationId: a.id, requestedBy });
}

/** Event rules. Returns true if a rule fired *in this channel* (caller skips its own run). */
export function onUserMessage(channelId: string, text: string, userId: string): boolean {
  const lower = text.toLowerCase();
  let handledHere = false;
  for (const a of listAutomations()) {
    if (!a.enabled || a.trigger.type !== "event") continue;
    const t = a.trigger;
    if (t.channelId && t.channelId !== channelId) continue;
    if (!t.keyword || !lower.includes(t.keyword.toLowerCase())) continue;
    triggerAutomation(a, `keyword “${t.keyword}”`, userId);
    if (a.channelId === channelId) handledHere = true;
  }
  return handledHere;
}

function tick(since: number, now: number) {
  for (const a of listAutomations()) {
    if (!a.enabled || a.trigger.type !== "schedule") continue;
    const from = Math.max(since, a.lastRunAt ?? 0, a.createdAt);
    if (firedBetween(a.trigger.cron, from, now)) triggerAutomation(a, "schedule");
  }
}

const g = globalThis as unknown as { __exiScheduler?: ReturnType<typeof setInterval> };

/** Idempotent: safe to call on every hot reload. Missed slots while the server was down are skipped. */
export function startScheduler() {
  if (g.__exiScheduler) return;
  let last = Date.now();
  g.__exiScheduler = setInterval(() => {
    const now = Date.now();
    try {
      tick(last, now);
    } catch (err) {
      console.error("[maki] scheduler tick failed", err);
    }
    last = now;
  }, TICK_MS);
  g.__exiScheduler.unref?.();
  console.log(`[maki] scheduler started (tick ${TICK_MS / 1000}s, TZ=${Intl.DateTimeFormat().resolvedOptions().timeZone})`);
}
