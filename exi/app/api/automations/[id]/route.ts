import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { canAccess, deleteAutomation, getAutomation, getChannel, updateAutomation } from "@/lib/server/repo";
import { AutomationPatchSchema, parseJson } from "@/lib/server/validation";

export const PATCH = handle(async (req: Request, ctx: RouteContext<"/api/automations/[id]">) => {
  const me = await requireUser(req);
  const { id } = await ctx.params;
  const cur = getAutomation(id);
  if (!cur || !canAccess(me.id, getChannel(cur.channelId))) throw new HttpError(404, "Automation not found");
  const patch = await parseJson(req, AutomationPatchSchema);
  return Response.json({ automation: updateAutomation(id, patch) });
});

export const DELETE = handle(async (req: Request, ctx: RouteContext<"/api/automations/[id]">) => {
  const me = await requireUser(req);
  const { id } = await ctx.params;
  const cur = getAutomation(id);
  if (!cur || !canAccess(me.id, getChannel(cur.channelId))) throw new HttpError(404, "Automation not found");
  deleteAutomation(id);
  return Response.json({ ok: true });
});
