"use client";

import { useCallback, useEffect, useRef, type RefObject } from "react";
import { AGENTS } from "../agents";
import { uid } from "../ids";
import { firedBetween } from "../maki/cron";
import type { Dispatch } from "../store";
import type { AgentRun, Automation, ExiPlan, Message, WorkspaceState } from "../types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const jitter = (base: number) => base + Math.round(Math.random() * base * 0.6);
const SCHEDULER_TICK_MS = 15_000;

interface StartOptions {
  automationId?: string;
}

/**
 * Drives the multi-agent simulation: Exi plans, sub-agents work through their
 * steps one by one (visible in the Activity panel), then Exi reports back.
 * Also owns Maki — the schedule ticker and event-rule matching.
 */
export function useOrchestrator(stateRef: RefObject<WorkspaceState>, dispatch: Dispatch, enabled: boolean) {
  const post = useCallback(
    (m: Omit<Message, "id" | "createdAt">) =>
      dispatch({ type: "addMessage", message: { ...m, id: uid("m"), createdAt: Date.now() } }),
    [dispatch],
  );

  const startRun = useCallback(
    async (channelId: string, command: string, opts: StartOptions = {}) => {
      const runId = uid("run");
      const run: AgentRun = {
        id: runId,
        channelId,
        command,
        status: "planning",
        steps: [],
        startedAt: Date.now(),
        automationId: opts.automationId,
      };
      dispatch({ type: "upsertRun", run });

      const state = stateRef.current;
      const channel = state.channels.find((c) => c.id === channelId);
      const history = state.messages
        .filter((m) => m.channelId === channelId)
        .slice(-10)
        .map((m) => ({ author: AGENTS[m.author].name, text: m.text.slice(0, 2000) }));

      let plan: ExiPlan & { warning?: string };
      try {
        const res = await fetch("/api/exi", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command, channelName: channel?.name, history }),
        });
        if (!res.ok) throw new Error(`Planner returned ${res.status}`);
        plan = await res.json();
      } catch (err) {
        const error = err instanceof Error ? err.message : String(err);
        dispatch({ type: "patchRun", runId, patch: { status: "failed", error, finishedAt: Date.now() } });
        post({ channelId, author: "exi", runId, text: `⚠️ I couldn't plan that: ${error}` });
        return;
      }

      await sleep(jitter(500));
      const steps = plan.steps.map((s) => ({ ...s, id: uid("step"), status: "queued" as const }));
      dispatch({
        type: "patchRun",
        runId,
        patch: { status: "running", source: plan.source, summary: plan.summary, steps },
      });
      const delegated = steps.map((s) => `**${AGENTS[s.agent].name}**`).join(" → ");
      post({
        channelId,
        author: "exi",
        runId,
        automationId: opts.automationId,
        text: `${plan.summary}\n\nDelegating: ${delegated}${plan.warning ? `\n\n_${plan.warning}_` : ""}`,
      });

      for (const step of steps) {
        dispatch({ type: "patchStep", runId, stepId: step.id, patch: { status: "working", startedAt: Date.now() } });
        await sleep(jitter(1400));
        dispatch({ type: "patchStep", runId, stepId: step.id, patch: { status: "done", finishedAt: Date.now() } });
        post({ channelId, author: step.agent, runId, text: `**${step.title}**\n\n${step.output}` });
        await sleep(300);
      }

      await sleep(jitter(600));
      post({ channelId, author: "exi", runId, automationId: opts.automationId, text: plan.finalReport });
      dispatch({ type: "patchRun", runId, patch: { status: "done", finishedAt: Date.now() } });
    },
    [dispatch, post, stateRef],
  );

  const runAutomation = useCallback(
    (a: Automation, reason: string) => {
      dispatch({
        type: "patchAutomation",
        id: a.id,
        patch: { lastRunAt: Date.now(), runCount: a.runCount + 1 },
      });
      post({
        channelId: a.channelId,
        author: "maki",
        automationId: a.id,
        text: `⚡ **${a.name}** triggered (${reason}). Handing off to Exi: _${a.command}_`,
      });
      void startRun(a.channelId, a.command, { automationId: a.id });
    },
    [dispatch, post, startRun],
  );

  /**
   * Called after every user message so event-driven rules can react.
   * Returns true if a rule fired in this channel (so the caller can skip a duplicate run).
   */
  const onUserMessage = useCallback(
    (channelId: string, text: string): boolean => {
      const lower = text.toLowerCase();
      let handledHere = false;
      for (const a of stateRef.current.automations) {
        if (!a.enabled || a.trigger.type !== "event") continue;
        const t = a.trigger;
        if (t.channelId && t.channelId !== channelId) continue;
        if (t.keyword && lower.includes(t.keyword.toLowerCase())) {
          runAutomation(a, `keyword “${t.keyword}”`);
          if (a.channelId === channelId) handledHere = true;
        }
      }
      return handledHere;
    },
    [runAutomation, stateRef],
  );

  // Maki scheduler: fire schedule rules whose cron matched since the last tick.
  const lastTick = useRef<number>(0);
  useEffect(() => {
    if (!enabled) return;
    lastTick.current = Date.now();
    const id = window.setInterval(() => {
      const now = Date.now();
      const since = lastTick.current;
      lastTick.current = now;
      for (const a of stateRef.current.automations) {
        if (!a.enabled || a.trigger.type !== "schedule") continue;
        if (firedBetween(a.trigger.cron, Math.max(since, a.lastRunAt ?? 0), now)) runAutomation(a, "schedule");
      }
    }, SCHEDULER_TICK_MS);
    return () => window.clearInterval(id);
  }, [enabled, runAutomation, stateRef]);

  return { startRun, runAutomation, onUserMessage, post };
}
