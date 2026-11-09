import type { ExiPlan } from "../types";

type Step = ExiPlan["steps"][number];
type Intent = "launch" | "research" | "engineering" | "marketing" | "analytics" | "general";

const INTENT_KEYWORDS: Record<Exclude<Intent, "general">, RegExp> = {
  research: /competitor|competition|market|benchmark|research|trend|경쟁사|시장|조사|리서치/i,
  engineering: /bug|fix|api|build|code|deploy|refactor|endpoint|timeout|outage|incident|개발|코드|버그|배포|장애/i,
  marketing: /campaign|marketing|seo|brand|content|social|ad\b|ads|copy|newsletter|마케팅|캠페인|광고|콘텐츠/i,
  analytics: /metric|kpi|dashboard|report|churn|retention|revenue|analy[sz]e|data|지표|분석|매출|리포트/i,
  launch: /launch|release|roadmap|plan|milestone|go-to-market|gtm|출시|런칭|기획|일정/i,
};

export function detectIntents(command: string): Intent[] {
  const hits = (Object.keys(INTENT_KEYWORDS) as Exclude<Intent, "general">[]).filter((k) =>
    INTENT_KEYWORDS[k].test(command),
  );
  return hits.length ? hits : ["general"];
}

function topic(command: string): string {
  const cleaned = command.replace(/^@?exi[,:]?\s*/i, "").trim();
  return cleaned.length > 80 ? `${cleaned.slice(0, 77)}…` : cleaned;
}

const S = {
  planner: (t: string): Step => ({
    agent: "planner",
    title: "Scope the request & set milestones",
    detail: `Break "${t}" into milestones with owners and a timeline.`,
    output: [
      `**Scope:** ${t}`,
      "",
      "| Milestone | Owner | ETA |",
      "|---|---|---|",
      "| Requirements & success metrics | Planner | Day 1 |",
      "| Discovery / research | Researcher | Day 2–3 |",
      "| Build & internal review | Coder | Day 4–8 |",
      "| Go-to-market assets | Marketer | Day 6–9 |",
      "| Launch readout | Analyst | Day 10 |",
      "",
      "Risks: unclear success metric, dependency on design sign-off.",
    ].join("\n"),
  }),
  researcher: (t: string): Step => ({
    agent: "researcher",
    title: "Gather market & competitor signals",
    detail: `Collect the latest market context relevant to "${t}".`,
    output: [
      "**Landscape snapshot** _(simulated data)_",
      "- **Competitor A** shipped a workflow builder last week — targeting mid-market ops teams.",
      "- **Competitor B** cut prices 20% on its team plan; signals a land-grab.",
      "- **Competitor C** is hiring heavily for enterprise sales in APAC.",
      "",
      "**White space:** none of them offer messenger-native multi-agent delegation — our core wedge.",
    ].join("\n"),
  }),
  coder: (t: string): Step => ({
    agent: "coder",
    title: "Draft the technical approach",
    detail: `Propose an implementation path for "${t}".`,
    output: [
      "**Approach**",
      "1. Reproduce & add a failing test.",
      "2. Isolate the change behind a feature flag.",
      "3. Ship to staging, then 10% → 100% rollout.",
      "",
      "```ts",
      "// sketch",
      "export async function handler(req: Request) {",
      "  const res = await withTimeout(fetchUpstream(req), 5_000);",
      "  return Response.json(res);",
      "}",
      "```",
    ].join("\n"),
  }),
  marketer: (t: string): Step => ({
    agent: "marketer",
    title: "Craft positioning & campaign",
    detail: `Write positioning and channel plan for "${t}".`,
    output: [
      "**Headline:** _Your team, plus a team of agents — right inside chat._",
      "",
      "- **Channels:** LinkedIn thought-leadership, product-hunt launch, partner newsletter",
      "- **Hook:** “Zero learning curve: if you can Slack, you can delegate to AI.”",
      "- **CTA:** Start a free 14-day workspace",
    ].join("\n"),
  }),
  analyst: (t: string): Step => ({
    agent: "analyst",
    title: "Define metrics & read out impact",
    detail: `Pick KPIs and estimate impact for "${t}".`,
    output: [
      "| KPI | Baseline | Target |",
      "|---|---|---|",
      "| Weekly active workspaces | 1,240 | 1,500 |",
      "| Tasks delegated / user / wk | 3.1 | 5.0 |",
      "| Time-to-first-agent-task | 9 min | < 3 min |",
      "",
      "_Figures are simulated for the prototype._",
    ].join("\n"),
  }),
};

const ROUTES: Record<Intent, (keyof typeof S)[]> = {
  launch: ["planner", "researcher", "marketer", "analyst"],
  research: ["researcher", "analyst"],
  engineering: ["planner", "coder"],
  marketing: ["researcher", "marketer"],
  analytics: ["analyst", "planner"],
  general: ["planner", "researcher"],
};

/** Deterministic, offline planner used when no ANTHROPIC_API_KEY is configured. */
export function mockPlan(command: string): ExiPlan {
  const t = topic(command);
  const intents = detectIntents(command);
  const order: (keyof typeof S)[] = [];
  for (const intent of intents) for (const a of ROUTES[intent]) if (!order.includes(a)) order.push(a);
  const agents = order.slice(0, 5);
  if (agents.length < 2) agents.push("planner");

  const steps = agents.map((a) => S[a](t));
  const names = agents.map((a) => a[0].toUpperCase() + a.slice(1));

  return {
    source: "mock",
    summary: `I'll route this to ${names.join(", ")} — ${intents.join(" + ")} request.`,
    steps,
    finalReport: [
      `### ✅ Done: ${t}`,
      "",
      ...steps.map((s) => `- **${s.agent[0].toUpperCase() + s.agent.slice(1)}** — ${s.title.toLowerCase()}`),
      "",
      "**Next actions**",
      "1. Confirm the owner and deadline in this thread.",
      "2. Say _\"schedule this weekly\"_ or open **Automations** to have Maki repeat it.",
    ].join("\n"),
  };
}
