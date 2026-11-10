import Anthropic from "@anthropic-ai/sdk";
import { betaZodOutputFormat } from "@anthropic-ai/sdk/helpers/beta/zod";
import { z } from "zod";
import type { SpecialistId } from "../types";

// All Claude calls live here. Each specialist is a separate, streamed call with
// its own role prompt; the Researcher can search the web (server-side tool).

const MODEL = process.env.EXI_MODEL || "claude-opus-5-5";
type Effort = "low" | "medium" | "high" | "xhigh" | "max";
const EFFORT = (process.env.EXI_EFFORT as Effort) || "low";
const WEB_SEARCH = process.env.EXI_WEB_SEARCH !== "0";
// On a safety decline the API re-runs the request on a fallback model in the same call.
const FALLBACK = { betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" as const };

export function claudeEnabled(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN);
}
export const claudeModel = () => MODEL;

let client: Anthropic | null = null;
const getClient = () => (client ??= new Anthropic({ maxRetries: 2, timeout: 5 * 60 * 1000 }));

/* --------------------------------- planner -------------------------------- */

const PlanSchema = z.object({
  summary: z.string().describe("One or two sentences to the requester: how the team will tackle it"),
  steps: z
    .array(
      z.object({
        agent: z.enum(["planner", "researcher", "coder", "marketer", "analyst"]),
        title: z.string().describe("Short imperative task title, max ~8 words"),
        detail: z.string().describe("Precise instructions for that specialist, 1-3 sentences"),
      }),
    )
    .describe("2-5 delegated steps in execution order; later steps can build on earlier ones"),
});
export type Plan = z.infer<typeof PlanSchema>;

const PLANNER_SYSTEM = `You are Exi, the coordinator (PM) agent of a team workspace that looks like a chat app.
A teammate posted a request in a channel. Decompose it into 2-5 sub-tasks and assign each to exactly one specialist:
- planner: scope, milestones, timelines, owners, risks
- researcher: market, competitor and background research (has live web search)
- coder: technical design, code, debugging, architecture
- marketer: positioning, messaging, campaigns, copy
- analyst: metrics, KPIs, data interpretation, business cases
Order the steps the way the work should flow. Only include specialists that add real value.
For a trivial question, use the minimum of 2 steps. Write in the language of the request.`;

export async function planWithClaude(input: {
  command: string;
  channelName?: string;
  history: { author: string; text: string }[];
}): Promise<Plan> {
  const context = input.history.map((m) => `${m.author}: ${m.text}`).join("\n");
  const res = await getClient().beta.messages.parse({
    model: MODEL,
    max_tokens: 8000,
    ...FALLBACK,
    system: PLANNER_SYSTEM,
    output_config: { effort: EFFORT, format: betaZodOutputFormat(PlanSchema) },
    messages: [
      {
        role: "user",
        content: [
          input.channelName ? `Channel: #${input.channelName}` : "",
          context ? `Recent conversation:\n${context}` : "",
          `Request:\n${input.command}`,
        ]
          .filter(Boolean)
          .join("\n\n"),
      },
    ],
  });
  if (res.stop_reason === "refusal") throw new Error("Claude declined to plan this request");
  const plan = res.parsed_output;
  if (!plan || plan.steps.length === 0) throw new Error(`Planner returned no steps (stop_reason: ${res.stop_reason})`);
  return { ...plan, steps: plan.steps.slice(0, 5) };
}

/* ------------------------------- specialists ------------------------------ */

const ROLE_PROMPTS: Record<SpecialistId, string> = {
  planner:
    "You are Planner, a pragmatic project planner. Produce scope, milestones (table: milestone, owner, ETA), dependencies and top risks with mitigations.",
  researcher:
    "You are Researcher, a market and competitive-intelligence analyst. Use web search for current facts and cite sources as Markdown links. Separate facts from your inferences.",
  coder:
    "You are Coder, a senior software engineer. Give a concrete technical approach: architecture, key decisions with trade-offs, and focused code snippets where they help.",
  marketer:
    "You are Marketer, a B2B product marketer. Produce positioning, key messages, channel plan and ready-to-use copy.",
  analyst:
    "You are Analyst, a business/data analyst. Define KPIs with baselines and targets, explain the logic, and state assumptions explicitly. Never invent precise internal figures — mark estimates as estimates.",
};

const SHARED_RULES = `You are one member of an AI team coordinated by Exi, posting your deliverable into a team chat.
- Output skimmable Markdown (headings, bullets, tables). Aim for 120-350 words.
- Do the work; don't describe what you would do. No preamble, no sign-off.
- Build on teammates' earlier outputs instead of repeating them.
- Write in the language of the original request.`;

async function streamText(
  params: {
    system: string;
    content: string;
    tools?: Anthropic.Beta.BetaToolUnion[];
    maxTokens?: number;
  },
  onText: (full: string) => void,
): Promise<string> {
  const messages: Anthropic.Beta.BetaMessageParam[] = [{ role: "user", content: params.content }];
  let full = "";
  // pause_turn: a long server-tool turn (web search) can pause; resend to continue.
  for (let turn = 0; turn < 4; turn++) {
    const stream = getClient().beta.messages.stream({
      model: MODEL,
      max_tokens: params.maxTokens ?? 16000,
      ...FALLBACK,
      system: params.system,
      output_config: { effort: EFFORT },
      messages,
      ...(params.tools ? { tools: params.tools } : {}),
    });
    stream.on("text", (delta) => {
      full += delta;
      onText(full);
    });
    const msg = await stream.finalMessage();
    if (msg.stop_reason === "refusal") throw new Error("Claude declined this step");
    if (msg.stop_reason !== "pause_turn") break;
    messages.push({ role: "assistant", content: msg.content });
  }
  return full.trim();
}

export async function runSpecialist(
  input: {
    agent: SpecialistId;
    title: string;
    detail: string;
    command: string;
    planSummary: string;
    prior: { agent: string; title: string; output: string }[];
  },
  onText: (full: string) => void,
): Promise<string> {
  const priorText = input.prior.length
    ? input.prior.map((p) => `### ${p.agent} — ${p.title}\n${p.output}`).join("\n\n")
    : "(you are first)";
  const content = `Original request:\n${input.command}\n\nExi's plan: ${input.planSummary}\n\nTeammates' outputs so far:\n${priorText}\n\nYour task — ${input.title}:\n${input.detail}`;
  const system = `${ROLE_PROMPTS[input.agent]}\n\n${SHARED_RULES}`;

  if (input.agent === "researcher" && WEB_SEARCH) {
    try {
      return await streamText(
        { system, content, tools: [{ type: "web_search_20260209", name: "web_search", max_uses: 5 }] },
        onText,
      );
    } catch (err) {
      // Web search may be disabled for the organization — retry without it.
      if (!(err instanceof Anthropic.BadRequestError)) throw err;
      console.warn("[exi] web search unavailable, retrying without it:", err.message);
      onText("");
    }
  }
  return streamText({ system, content }, onText);
}

export async function synthesize(
  input: { command: string; outputs: { agent: string; title: string; output: string }[] },
  onText: (full: string) => void,
): Promise<string> {
  return streamText(
    {
      system: `You are Exi, the coordinator. Your team has finished. Write the final reply to the requester in the chat:
a short headline, the 3-6 most important takeaways across the team's work, and 2-4 concrete next actions with suggested owners.
Don't repeat the full outputs — they are already in the thread above. Markdown, under 250 words, in the language of the request.`,
      content: `Request:\n${input.command}\n\nTeam outputs:\n${input.outputs
        .map((o) => `### ${o.agent} — ${o.title}\n${o.output}`)
        .join("\n\n")}`,
      maxTokens: 8000,
    },
    onText,
  );
}

/* --------------------------------- feedback ------------------------------- */

const TriageSchema = z.object({
  title: z.string().describe("Concise GitHub issue title, imperative, max ~70 chars"),
  kind: z.enum(["bug", "enhancement"]),
  priority: z.enum(["P0", "P1", "P2", "P3"]),
  area: z.string().describe("Product area, e.g. Chat, Sidebar, Agents, Automations, Auth"),
  body: z
    .string()
    .describe("Issue body in Markdown: Problem / Proposal, Acceptance criteria (checklist), Notes"),
});
export type Triage = z.infer<typeof TriageSchema>;

export async function triageWithClaude(feedback: string): Promise<Triage> {
  const res = await getClient().beta.messages.parse({
    model: MODEL,
    max_tokens: 4000,
    ...FALLBACK,
    system:
      "You triage product feedback for Exi, a chat workspace where AI agents (Exi, Planner, Researcher, Coder, Marketer, Analyst, Maki automations) collaborate. Turn the feedback into a well-formed GitHub issue. Keep the user's intent; don't invent requirements. Write in the feedback's language.",
    output_config: { effort: "low", format: betaZodOutputFormat(TriageSchema) },
    messages: [{ role: "user", content: feedback }],
  });
  if (!res.parsed_output) throw new Error(`Triage failed (stop_reason: ${res.stop_reason})`);
  return res.parsed_output;
}
