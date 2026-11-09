import type { WorkspaceState } from "./types";

const HOUR = 60 * 60 * 1000;

export function createSeedState(now = Date.now()): WorkspaceState {
  return {
    appVersion: "0.1.0",
    activeChannelId: "ch_general",
    channels: [
      { id: "ch_general", name: "general", kind: "channel", topic: "Company-wide announcements — ask @Exi anything" },
      { id: "ch_launch", name: "product-launch", kind: "channel", topic: "Q4 launch of the Exi mobile app" },
      { id: "ch_growth", name: "growth-marketing", kind: "channel", topic: "Campaigns, SEO, competitor watch" },
      { id: "ch_eng", name: "engineering", kind: "channel", topic: "Builds, incidents, code review" },
      { id: "dm_exi", name: "Exi", kind: "dm", peer: "exi" },
      { id: "dm_maki", name: "Maki", kind: "dm", peer: "maki" },
      { id: "dm_planner", name: "Planner", kind: "dm", peer: "planner" },
    ],
    messages: [
      {
        id: "m_seed_1",
        channelId: "ch_general",
        author: "exi",
        createdAt: now - 3 * HOUR,
        text:
          "👋 Hi, I'm **Exi** — your coordinator agent.\n\nType any request in a channel and I'll break it down, delegate to the specialists " +
          "(**Planner**, **Researcher**, **Coder**, **Marketer**, **Analyst**) and report back.\n\n" +
          "Try:\n- `Plan the launch of our mobile app in 3 weeks`\n- `Analyze competitors in the AI agent market`\n- `Fix the login API timeout bug`",
      },
      {
        id: "m_seed_2",
        channelId: "ch_general",
        author: "maki",
        createdAt: now - 2 * HOUR,
        text:
          "⚡ **Maki** here. I run scheduled and event-driven automations. Open **Automations** in the header to add rules like " +
          "_\"Run daily competitor analysis at 9 AM\"_.",
      },
      {
        id: "m_seed_3",
        channelId: "ch_growth",
        author: "user",
        createdAt: now - HOUR,
        text: "Reference deck from last quarter: https://www.figma.com/file/q3-campaign-review",
      },
      {
        id: "m_seed_4",
        channelId: "dm_exi",
        author: "exi",
        createdAt: now - HOUR,
        text: "This is our private thread. Anything you send here goes straight to me.",
      },
    ],
    runs: [],
    automations: [
      {
        id: "auto_seed_competitor",
        name: "Daily competitor analysis",
        trigger: { type: "schedule", cron: "0 9 * * *" },
        channelId: "ch_growth",
        command: "Run the daily competitor analysis for the AI agent market and flag notable moves",
        enabled: true,
        createdAt: now - 24 * HOUR,
        runCount: 0,
      },
      {
        id: "auto_seed_incident",
        name: "Incident triage",
        trigger: { type: "event", event: "message_contains", keyword: "outage" },
        channelId: "ch_eng",
        command: "Triage the reported outage: likely root cause, blast radius and a fix plan",
        enabled: true,
        createdAt: now - 24 * HOUR,
        runCount: 0,
      },
    ],
    feedback: [],
  };
}
