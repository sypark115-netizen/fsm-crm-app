import { describeCron, naturalToCron } from "../maki/cron";
import type { Channel } from "../types";
import { createAutomation, insertMessage } from "./repo";

/**
 * Talk to Maki in plain words: "every weekday at 9am summarize competitor news".
 * Maki turns it into a schedule rule that posts back into this DM.
 */
export function handleMakiDm(channel: Channel, text: string, userId: string) {
  const cron = naturalToCron(text);
  const task = text
    .replace(/\b(every|each)\s+(\d+\s*min(ute)?s?|day|weekday|monday|tuesday|wednesday|thursday|friday|saturday|sunday|hour)s?\b/gi, "")
    .replace(/\b(daily|hourly|weekdays?)\b|매일/gi, "")
    .replace(/\b(at\s+)?\d{1,2}(:\d{2})?\s*(am|pm)\b|\bat\s+\d{1,2}(:\d{2})?\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();

  if (!cron || task.length < 3) {
    insertMessage({
      channelId: channel.id,
      author: "maki",
      text:
        "Tell me **what** to run and **when**, e.g.\n- `every weekday at 9am summarize AI agent market news`\n- `every monday at 10am review last week's pipeline`\n\nOr open **Automations** for keyword-triggered rules.",
    });
    return;
  }
  const a = createAutomation({
    name: task.slice(0, 60),
    trigger: { type: "schedule", cron },
    channelId: channel.id,
    command: task,
    enabled: true,
    createdBy: userId,
  });
  insertMessage({
    channelId: channel.id,
    author: "maki",
    automationId: a.id,
    text: `✅ Scheduled **${a.name}** — ${describeCron(cron)} (\`${cron}\`). Results will be posted here. Manage it under **Automations**.`,
  });
}
