import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { canAccess, createAutomation, getChannel } from "@/lib/server/repo";
import { AutomationCreateSchema, parseJson } from "@/lib/server/validation";

export const POST = handle(async (req: Request) => {
  const me = await requireUser(req);
  const body = await parseJson(req, AutomationCreateSchema);
  if (!canAccess(me.id, getChannel(body.channelId))) throw new HttpError(404, "Channel not found");
  const automation = createAutomation({ ...body, enabled: true, createdBy: me.id });
  return Response.json({ automation }, { status: 201 });
});
