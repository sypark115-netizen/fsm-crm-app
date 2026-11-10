# Exi — Agent Organization Gateway

A self-hosted team chat where **Exi**, a coordinator agent, plans each request and delegates it to specialist Claude agents. **Maki** runs scheduled and event-driven automations, and a feedback widget turns suggestions into GitHub issues.

> This is a standalone Next.js 16 app inside the `fsm-crm-app` repo. It has its own `package.json`, and the parent app ignores it (via `tsconfig` and `eslint`).

## What actually happens

1. In a channel, someone writes `@Exi <request>` (or anything in their DM with Exi).
2. **Exi plans** the work with one Claude call that returns structured output: a summary and 2–5 steps, each assigned to Planner, Researcher, Coder, Marketer or Analyst.
3. **Each specialist is its own streamed Claude call** with a role prompt and every earlier teammate's output. The **Researcher uses live web search.** Answers stream token by token into the chat for everyone in the channel.
4. **Exi writes the wrap-up**: key takeaways and next actions with suggested owners.
5. The **Agent Activity** panel shows the plan, who is working, and step timings in real time.

Other features:
- **Maki:** cron schedules and "message contains X" rules run **on the server**, even when nobody has the app open. You can also DM Maki in plain words, e.g. `every weekday at 9am summarize AI agent market news`.
- **Feedback widget:** Claude triages each suggestion (type, priority, area, acceptance criteria) and files a **GitHub issue**.
- **Team accounts and real-time sync:** usernames and passwords, invite code, private DMs, live updates over SSE.
- **Storage:** SQLite (one file) plus uploaded files on disk. If a server restarts mid-run, that run is closed out cleanly.

Without `ANTHROPIC_API_KEY` the app still works in **demo mode**, with canned agent output and a banner saying so.

## Run it

### Docker (recommended for a server)

```bash
cd exi
cp .env.example .env        # set ANTHROPIC_API_KEY, EXI_INVITE_CODE, optionally GITHUB_*
docker compose up -d --build
# → http://<server>:3000
```

Data lives in the `exi-data` volume (`/data`: `exi.db` + `uploads/`). Back up that volume.

### Plain Node (local or VM)

```bash
cd exi
npm install
cp .env.example .env.local  # set ANTHROPIC_API_KEY
npm run dev                 # development, http://localhost:3000
# or production:
npm run build && npm start
```

Use Node 22+. Run **one** instance per data directory, because the scheduler and SQLite live in-process.

### First steps

1. Open the app. The **first account you create becomes the owner.**
2. Share the URL and `EXI_INVITE_CODE` with teammates. They choose "Join with invite". If the code is empty, sign-up is closed.
3. In `#general`, try: `@Exi analyze AI agent competitors and suggest our positioning`.

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Enables real agents. Without it the app runs in demo mode. |
| `EXI_MODEL` | `claude-opus-5-5` | Model used by every agent |
| `EXI_EFFORT` | `low` | `low` / `medium` / `high`. Higher is more thorough, slower and pricier. |
| `EXI_WEB_SEARCH` | `1` | Researcher web search (`0` turns it off) |
| `EXI_INVITE_CODE` | — | Code teammates need to sign up |
| `GITHUB_TOKEN`, `GITHUB_REPO` | — | Feedback → issues. Use a fine-grained token with *Issues: read & write*; `GITHUB_REPO` looks like `owner/name`. |
| `GITHUB_API_URL` | `https://api.github.com` | For GitHub Enterprise |
| `EXI_REPLY_ALL` | `0` | `1` = Exi answers every channel message, not only `@Exi` mentions |
| `EXI_MAX_CONCURRENT_RUNS` | `3` | Caps parallel agent runs (and cost) |
| `EXI_DATA_DIR` | `./data` | SQLite DB + uploads |
| `TZ` | system | Time zone for Maki schedules (compose sets it to `Asia/Seoul`) |

**Cost note:** a typical request makes about 4–7 Claude calls (plan, 2–5 specialists, wrap-up). Keep `EXI_EFFORT=low` and the `@Exi` mention rule until you know your usage.

## Architecture

```
app/
  page.tsx, login/             server-checked session → <Workspace/> or login
  api/auth/{signup,login,logout}
  api/bootstrap                initial snapshot for the signed-in user
  api/stream                   SSE: live workspace events
  api/messages                 post → event rules → Exi run (if addressed)
  api/files, files/[id]        uploads (auth-gated download)
  api/automations[/id[/run]]   Maki CRUD + manual run
  api/feedback                 Claude triage → GitHub issue
  api/health                   Docker health check
instrumentation.ts             starts the Maki scheduler and cleans up interrupted runs
lib/server/
  db.ts                        SQLite + migrations (lazy-opened)
  repo.ts                      data access; every write publishes an event
  bus.ts                       in-process pub/sub → SSE
  auth.ts                      scrypt passwords, hashed session tokens, same-origin check
  claude.ts                    planner / specialists / wrap-up / triage (Anthropic SDK)
  orchestrator.ts              run loop with streaming + concurrency cap
  maki.ts, makiDm.ts           scheduler, event rules, plain-language DMs
  feedback.ts, github.ts       improvement loop
lib/client/                    API helper + SSE-backed store
components/                    sidebar · chat · agents · maki · feedback · workspace
```

**Security choices:**
- Session cookies are `HttpOnly` and `SameSite=Lax`, plus `Secure` over HTTPS.
- Session tokens are stored hashed.
- Mutating requests require the same origin.
- Logins are rate-limited.
- Private DMs and their automations are filtered on the server, both in the snapshot and in live events.
- Uploads are limited to 15 MB. Only raster images and PDFs render inline; everything else downloads.
- Link previews are built from the URL alone (no server-side fetching, to avoid SSRF).

**Put it behind HTTPS** with a reverse proxy (Caddy, nginx, or Cloudflare Tunnel) before exposing it to the internet.

## Limits and next steps

- **One instance only.** To scale out, move to Postgres and Redis pub/sub, and move the scheduler to a separate worker.
- **Missed schedules are skipped.** Schedules that came due while the server was down don't run afterwards.
- **No agent memory beyond the thread.** Agents see the last 12 messages of a channel. Attached files are mentioned to the agents by name, not read.
- **Possible additions:** password reset/admin UI, Slack/Google connectors as agent tools, per-workspace usage and cost tracking.
