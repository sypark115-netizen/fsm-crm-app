import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { createChannel, listChannelsFor } from "@/lib/server/repo";
import { ChannelSchema, parseJson } from "@/lib/server/validation";

export const POST = handle(async (req: Request) => {
  const me = await requireUser(req);
  const { name, topic } = await parseJson(req, ChannelSchema);
  if (listChannelsFor(me.id).some((c) => c.kind === "channel" && c.name === name)) {
    throw new HttpError(409, `#${name} already exists`);
  }
  return Response.json({ channel: createChannel(name, topic) }, { status: 201 });
});
