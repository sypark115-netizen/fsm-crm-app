import { handle, requireUser } from "@/lib/server/auth";
import { claudeEnabled, claudeModel } from "@/lib/server/claude";
import { githubEnabled } from "@/lib/server/github";
import {
  ensureDefaultChannels,
  listAutomationsFor,
  listChannelsFor,
  listFeedback,
  listMessagesFor,
  listRunsFor,
  listUsers,
} from "@/lib/server/repo";
import type { Bootstrap } from "@/lib/types";

export const GET = handle(async (req: Request) => {
  const me = await requireUser(req);
  ensureDefaultChannels();
  const body: Bootstrap = {
    me,
    users: listUsers(),
    channels: listChannelsFor(me.id),
    messages: listMessagesFor(me.id),
    runs: listRunsFor(me.id),
    automations: listAutomationsFor(me.id),
    feedback: listFeedback(),
    status: {
      planner: claudeEnabled() ? "claude" : "mock",
      github: githubEnabled(),
      model: claudeEnabled() ? claudeModel() : undefined,
    },
  };
  return Response.json(body);
});
