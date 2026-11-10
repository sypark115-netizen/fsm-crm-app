import { AGENTS } from "../agents";
import { uid } from "../ids";
import { mockPlan } from "../orchestrator/mockPlanner";
import type { AgentRun, Message, RunStep, SpecialistId } from "../types";
import { claudeEnabled, planWithClaude, runSpecialist, synthesize } from "./claude";
import {
  broadcastMessageDraft,
  finalizeMessageText,
  getChannel,
  getUserById,
  insertMessage,
  recentMessages,
  saveRun,
} from "./repo";

// Server-side orchestration: Exi plans, specialists run one after another
// (each streaming into its own chat message), then Exi writes the wrap-up.

const MAX_CONCURRENT = Number(process.env.EXI_MAX_CONCURRENT_RUNS || 3);
const g = globalThis as unknown as { __exiActiveRuns?: number };
g.__exiActiveRuns ??= 0;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Throttle live updates so a fast stream doesn't flood every client. */
function draftUpdater(message: Message) {
  let last = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let pending = "";
  const flush = () => {
    timer = null;
    last = Date.now();
    broadcastMessageDraft({ ...message, text: pending });
  };
  return {
    update(text: string) {
      pending = text;
      if (timer) return;
      const wait = Math.max(0, 150 - (Date.now() - last));
      timer = setTimeout(flush, wait);
    },
    cancel() {
      if (timer) clearTimeout(timer);
    },
  };
}

/** Plays back canned text like a stream (demo mode). */
async function fakeStream(text: string, onText: (full: string) => void) {
  for (let i = 0; i < text.length; i += 18) {
    onText(text.slice(0, i + 18));
    await sleep(35);
  }
  return text;
}

export interface StartRunInput {
  channelId: string;
  command: string;
  requestedBy?: string;
  automationId?: string;
}

/** Starts a run in the background and returns it immediately. */
export function startRun(input: StartRunInput): AgentRun | null {
  if (g.__exiActiveRuns! >= MAX_CONCURRENT) {
    insertMessage({
      channelId: input.channelId,
      author: "exi",
      text: `⏳ The team is busy with ${MAX_CONCURRENT} requests right now — please try again in a minute.`,
    });
    return null;
  }
  const run: AgentRun = {
    id: uid("run"),
    channelId: input.channelId,
    command: input.command,
    status: "planning",
    source: claudeEnabled() ? "claude" : "mock",
    steps: [],
    startedAt: Date.now(),
    automationId: input.automationId,
    requestedBy: input.requestedBy,
  };
  saveRun(run);
  g.__exiActiveRuns!++;
  execute(run)
    .catch((err) => {
      const error = err instanceof Error ? err.message : String(err);
      console.error("[exi] run failed", run.id, err);
      saveRun({ ...run, status: "failed", error, finishedAt: Date.now() });
      insertMessage({ channelId: run.channelId, author: "exi", runId: run.id, text: `⚠️ Something went wrong: ${error}` });
    })
    .finally(() => {
      g.__exiActiveRuns!--;
    });
  return run;
}

async function execute(initial: AgentRun) {
  let run = initial;
  const update = (patch: Partial<AgentRun>) => {
    run = { ...run, ...patch };
    saveRun(run);
  };
  const patchStep = (id: string, patch: Partial<RunStep>) =>
    update({ steps: run.steps.map((s) => (s.id === id ? { ...s, ...patch } : s)) });

  const channel = getChannel(run.channelId);
  const history = recentMessages(run.channelId, 12)
    .filter((m) => m.text)
    .map((m) => ({
      author: AGENTS[m.author as keyof typeof AGENTS]?.name ?? getUserById(m.author)?.displayName ?? "Member",
      text: m.text.slice(0, 1500),
    }));

  // 1) Plan
  const useClaude = run.source === "claude";
  const mock = useClaude ? null : mockPlan(run.command);
  const plan = useClaude
    ? await planWithClaude({ command: run.command, channelName: channel?.name, history })
    : { summary: mock!.summary, steps: mock!.steps };

  const steps: RunStep[] = plan.steps.map((s) => ({
    id: uid("step"),
    agent: s.agent as SpecialistId,
    title: s.title,
    detail: s.detail,
    status: "queued",
  }));
  update({ status: "running", summary: plan.summary, steps });
  insertMessage({
    channelId: run.channelId,
    author: "exi",
    runId: run.id,
    automationId: run.automationId,
    text: `${plan.summary}\n\nDelegating: ${steps.map((s) => `**${AGENTS[s.agent].name}**`).join(" → ")}`,
  });

  // 2) Specialists, in order — each sees the earlier outputs.
  const outputs: { agent: string; title: string; output: string }[] = [];
  for (const [i, step] of steps.entries()) {
    const msg = insertMessage({ channelId: run.channelId, author: step.agent, runId: run.id, text: "" });
    broadcastMessageDraft(msg);
    patchStep(step.id, { status: "working", startedAt: Date.now(), messageId: msg.id });
    const draft = draftUpdater(msg);
    const header = `**${step.title}**\n\n`;
    try {
      const body = useClaude
        ? await runSpecialist(
            {
              agent: step.agent,
              title: step.title,
              detail: step.detail,
              command: run.command,
              planSummary: plan.summary,
              prior: outputs,
            },
            (full) => draft.update(header + full),
          )
        : await fakeStream(mock!.steps[i].output, (full) => draft.update(header + full));
      draft.cancel();
      finalizeMessageText(msg, header + (body || "_(no output)_"));
      outputs.push({ agent: AGENTS[step.agent].name, title: step.title, output: body });
      patchStep(step.id, { status: "done", finishedAt: Date.now() });
    } catch (err) {
      draft.cancel();
      const error = err instanceof Error ? err.message : String(err);
      finalizeMessageText(msg, `${header}⚠️ ${AGENTS[step.agent].name} couldn't finish: ${error}`);
      patchStep(step.id, { status: "failed", finishedAt: Date.now() });
      throw err;
    }
  }

  // 3) Exi wraps up.
  const final = insertMessage({
    channelId: run.channelId,
    author: "exi",
    runId: run.id,
    automationId: run.automationId,
    text: "",
  });
  broadcastMessageDraft(final);
  const draft = draftUpdater(final);
  const report = useClaude
    ? await synthesize({ command: run.command, outputs }, (full) => draft.update(full))
    : await fakeStream(mock!.finalReport, (full) => draft.update(full));
  draft.cancel();
  finalizeMessageText(final, report);
  update({ status: "done", finishedAt: Date.now() });
}
