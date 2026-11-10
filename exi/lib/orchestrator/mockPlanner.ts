import type { SpecialistId } from "../types";

// Offline planner used when no ANTHROPIC_API_KEY is configured, so the app is
// fully usable (and demoable) without a key. Output is clearly labelled.

export interface MockPlan {
  summary: string;
  steps: { agent: SpecialistId; title: string; detail: string; output: string }[];
  finalReport: string;
}

type Intent = "launch" | "research" | "engineering" | "marketing" | "analytics" | "general";

const INTENT_KEYWORDS: Record<Exclude<Intent, "general">, RegExp> = {
  research: /competitor|competition|market|benchmark|research|trend|경쟁사|시장|조사|리서치/i,
  engineering: /bug|fix|api|build|code|deploy|refactor|endpoint|timeout|outage|incident|개발|코드|버그|배포|장애/i,
  marketing: /campaign|marketing|seo|brand|content|social|\bads?\b|copy|newsletter|마케팅|캠페인|광고|콘텐츠/i,
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

type Step = MockPlan["steps"][number];
const NOTE = "\n\n_Demo output — set `ANTHROPIC_API_KEY` for real agent work._";

const S: Record<SpecialistId, (t: string) => Step> = {
  planner: (t) => ({
    agent: "planner",
    title: "Scope the request & set milestones",
    detail: `Break "${t}" into milestones with owners and a timeline.`,
    output:
      [
        `**Scope:** ${t}`,
        "",
        "| Milestone | Owner | ETA |",
        "|---|---|---|",
        "| Requirements & success metrics | Planner | Day 1 |",
        "| Discovery / research | Researcher | Day 2–3 |",
        "| Build & internal review | Coder | Day 4–8 |",
        "| Go-to-market assets | Marketer | Day 6–9 |",
        "| Launch readout | Analyst | Day 10 |",
      ].join("\n") + NOTE,
  }),
  researcher: (t) => ({
    agent: "researcher",
    title: "Gather market & competitor signals",
    detail: `Collect the latest market context relevant to "${t}".`,
    output:
      [
        "**Landscape snapshot**",
        "- Competitor A — workflow builder aimed at mid-market ops teams.",
        "- Competitor B — aggressive pricing on team plans.",
        "- Competitor C — enterprise sales push in APAC.",
        "",
        "**White space:** messenger-native multi-agent delegation.",
      ].join("\n") + NOTE,
  }),
  coder: (t) => ({
    agent: "coder",
    title: "Draft the technical approach",
    detail: `Propose an implementation path for "${t}".`,
    output:
      [
        "1. Reproduce & add a failing test.",
        "2. Isolate the change behind a feature flag.",
        "3. Ship to staging, then 10% → 100% rollout.",
        "",
        "```ts",
        "const res = await withTimeout(fetchUpstream(req), 5_000);",
        "```",
      ].join("\n") + NOTE,
  }),
  marketer: (t) => ({
    agent: "marketer",
    title: "Craft positioning & campaign",
    detail: `Write positioning and channel plan for "${t}".`,
    output:
      [
        "**Headline:** _Your team, plus a team of agents — right inside chat._",
        "- Channels: LinkedIn, Product Hunt, partner newsletter",
        "- CTA: Start a free 14-day workspace",
      ].join("\n") + NOTE,
  }),
  analyst: (t) => ({
    agent: "analyst",
    title: "Define metrics & read out impact",
    detail: `Pick KPIs and estimate impact for "${t}".`,
    output:
      [
        "| KPI | Target |",
        "|---|---|",
        "| Weekly active workspaces | +20% |",
        "| Tasks delegated / user / wk | 5 |",
        "| Time-to-first-agent-task | < 3 min |",
      ].join("\n") + NOTE,
  }),
};

const ROUTES: Record<Intent, SpecialistId[]> = {
  launch: ["planner", "researcher", "marketer", "analyst"],
  research: ["researcher", "analyst"],
  engineering: ["planner", "coder"],
  marketing: ["researcher", "marketer"],
  analytics: ["analyst", "planner"],
  general: ["planner", "researcher"],
};

export function mockPlan(command: string): MockPlan {
  const t = topic(command);
  const intents = detectIntents(command);
  const order: SpecialistId[] = [];
  for (const intent of intents) for (const a of ROUTES[intent]) if (!order.includes(a)) order.push(a);
  const agents = order.slice(0, 5);
  const steps = agents.map((a) => S[a](t));
  const names = agents.map((a) => a[0].toUpperCase() + a.slice(1));
  return {
    summary: `I'll route this to ${names.join(", ")} (${intents.join(" + ")}).`,
    steps,
    finalReport: [
      `### ✅ Done: ${t}`,
      "",
      ...steps.map((s) => `- **${s.agent[0].toUpperCase() + s.agent.slice(1)}** — ${s.title.toLowerCase()}`),
      "",
      "_Running in demo mode. Add `ANTHROPIC_API_KEY` to get real research, plans and code._",
    ].join("\n"),
  };
}
