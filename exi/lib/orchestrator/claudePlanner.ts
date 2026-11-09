import Anthropic from "@anthropic-ai/sdk";
import { betaZodOutputFormat } from "@anthropic-ai/sdk/helpers/beta/zod";
import type { ExiPlan } from "../types";
import { PlanSchema, type PlanRequest } from "./schema";

const SYSTEM_PROMPT = `You are Exi, the coordinator agent of an enterprise collaboration workspace.
A teammate has posted a request in a chat channel. Act as a PM: decompose it into 2-5 sub-tasks
and delegate each to exactly one specialist, then write each specialist's deliverable as if they did the work.

Specialists:
- planner: scope, milestones, timelines, owners, risks
- researcher: market, competitor and background research
- coder: technical design, code, debugging, infrastructure
- marketer: positioning, messaging, campaigns, content
- analyst: metrics, KPIs, data interpretation, reporting

Rules:
- Order steps the way the work would actually flow.
- Keep every output skimmable Markdown, under ~150 words each.
- You have no live data access; label any figures as estimates.
- Reply in the same language the request is written in.
- finalReport is addressed to the requester: what was done, the key takeaways, and 2-3 next actions.`;

let client: Anthropic | null = null;
function getClient() {
  client ??= new Anthropic();
  return client;
}

export function claudeEnabled(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN);
}

export async function claudePlan(req: PlanRequest): Promise<ExiPlan> {
  const history = (req.history ?? []).map((m) => `${m.author}: ${m.text}`).join("\n");
  const userContent = [
    req.channelName ? `Channel: #${req.channelName}` : null,
    history ? `Recent conversation:\n${history}` : null,
    `Request:\n${req.command}`,
  ]
    .filter(Boolean)
    .join("\n\n");

  const response = await getClient().beta.messages.parse({
    model: process.env.EXI_MODEL || "claude-opus-5-5",
    max_tokens: 16000,
    betas: ["server-side-fallback-2026-07-01"],
    // On a safety decline the API re-runs the request on a fallback model in the same call.
    fallbacks: "default",
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userContent }],
    output_config: { effort: "low", format: betaZodOutputFormat(PlanSchema) },
  });

  if (response.stop_reason === "refusal") throw new Error("Claude declined this request");
  const parsed = response.parsed_output;
  if (!parsed) throw new Error(`Could not parse plan (stop_reason: ${response.stop_reason})`);
  if (parsed.steps.length === 0) throw new Error("Plan had no steps");
  return { ...parsed, steps: parsed.steps.slice(0, 5), source: "claude" };
}
