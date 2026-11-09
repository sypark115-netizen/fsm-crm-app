# Exi — Agent Organization Gateway (prototype)

A messenger-style workspace where **Exi**, a coordinator agent, breaks each request into sub-tasks and hands them to specialist agents. **Maki** runs scheduled and event-driven automations, and a **feedback loop** shows the product improving itself.

> This is a standalone Next.js app inside the `fsm-crm-app` repo. It has its own `package.json`, and the parent app ignores it (via `tsconfig` and `eslint`).

## Run locally

```bash
cd exi
npm install
npm run dev            # http://localhost:3000
```

Production build: `npm run build && npm start`.

### Optional: real Claude planning

Without a key, Exi uses a **deterministic mock planner** that routes requests by keyword, in English and Korean. To have Claude plan and write each agent's deliverable:

```bash
cp .env.example .env.local
# set ANTHROPIC_API_KEY=...   (optional: EXI_MODEL, default claude-opus-5-5)
```

`GET /api/exi` reports which planner is active. If Claude fails, the route falls back to the mock planner and flags it in the chat.

## What's in the prototype

| Feature | Where |
|---|---|
| Slack-like layout: sidebar (channels + DMs), chat, Agent Activity panel | `components/workspace/Workspace.tsx` |
| Markdown (GFM tables, code), link unfurls, file/image attachments | `components/chat/*` |
| Exi plans → sub-agents run step by step → Exi reports | `lib/orchestrator/useOrchestrator.ts` |
| Planners: Claude (structured output) or mock | `lib/orchestrator/claudePlanner.ts`, `mockPlanner.ts`, `app/api/exi/route.ts` |
| Maki: cron schedules + "message contains" rules, plain-language → cron | `components/maki/MakiModal.tsx`, `lib/maki/cron.ts` |
| Feedback widget (bottom-left) → triage/spec/build/ship log + version bump | `components/feedback/FeedbackWidget.tsx`, `app/api/feedback/route.ts` |
| State + localStorage persistence (reset button in header) | `lib/store.ts`, `lib/seed.ts`, `lib/types.ts` |

### Try it

- In `#general`: `Plan the launch of our mobile app in 3 weeks and draft the marketing campaign`
- In `#engineering`: `We have an outage on the login API`. This fires the seeded **Incident triage** rule.
- Under **Automations**, type `Run weekly pipeline review every monday at 10 am`, then click **Fill** and **Create**.
- Click **Feedback / Improve** and submit an idea. Watch the agents ship a new version.

## Architecture notes and next steps

```
app/
  page.tsx                 → <Workspace/> (client)
  api/exi/route.ts         → POST: command → plan {summary, steps[], finalReport}
  api/feedback/route.ts    → POST: feedback → iteration log + next version
components/{sidebar,chat,agents,maki,feedback,workspace}
lib/
  types.ts                 domain model (serialisable → DB-ready)
  store.ts                 reducer + localStorage
  orchestrator/            planners + client-side run loop
  maki/cron.ts             5-field cron parser, next-run, NL → cron
```

- **Prototype shortcuts:** sub-agent outputs come from a single planner call, and the client replays them with delays so you can watch the hand-offs. Maki evaluates schedules in the browser every 15 s, and only while the tab is open.
- **Toward production:**
  - Move runs and schedules to a server worker or queue, and persist them in a DB (`lib/types.ts` maps 1:1 to tables).
  - Stream real per-agent tool-use runs over SSE.
  - Add auth and multi-user realtime (e.g. WebSockets).
  - Unfurl links from OpenGraph data on the server.
