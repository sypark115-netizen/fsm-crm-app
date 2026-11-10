import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { triggerAutomation } from "@/lib/server/maki";
import { canAccess, getAutomation, getChannel } from "@/lib/server/repo";

export const POST = handle(async (req: Request, ctx: RouteContext<"/api/automations/[id]/run">) => {
  const me = await requireUser(req);
  const { id } = await ctx.params;
  const a = getAutomation(id);
  if (!a || !canAccess(me.id, getChannel(a.channelId))) throw new HttpError(404, "Automation not found");
  triggerAutomation(a, `run by ${me.displayName}`, me.id);
  return Response.json({ ok: true });
});
