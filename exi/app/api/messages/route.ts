import { HttpError, handle, requireUser } from "@/lib/server/auth";
import { handleMakiDm } from "@/lib/server/makiDm";
import { onUserMessage } from "@/lib/server/maki";
import { startRun } from "@/lib/server/orchestrator";
import { canAccess, getChannel, getFile, insertMessage } from "@/lib/server/repo";
import { MessageSchema, parseJson } from "@/lib/server/validation";
import type { Attachment } from "@/lib/types";

const MENTION = /(^|\s)[@/]exi\b[,:]?/i;
const REPLY_ALL = process.env.EXI_REPLY_ALL === "1";

/**
 * Post a message. Exi picks it up when:
 *  - it's in your DM with Exi, or
 *  - it mentions @Exi (or /exi) in a channel (or EXI_REPLY_ALL=1).
 * Event automations are checked on every message.
 */
export const POST = handle(async (req: Request) => {
  const me = await requireUser(req);
  const body = await parseJson(req, MessageSchema);
  const channel = getChannel(body.channelId);
  if (!canAccess(me.id, channel)) throw new HttpError(404, "Channel not found");

  const attachments: Attachment[] = (body.attachmentIds ?? []).flatMap((id) => {
    const f = getFile(id);
    return f ? [{ id: f.id, name: f.name, size: f.size, mime: f.mime, url: `/api/files/${f.id}` }] : [];
  });
  const text = body.text.trim();
  if (!text && attachments.length === 0) throw new HttpError(400, "Message is empty");

  const message = insertMessage({ channelId: channel.id, author: me.id, text, attachments });

  if (channel.kind === "dm" && channel.peer === "maki") {
    handleMakiDm(channel, text, me.id);
    return Response.json({ message }, { status: 201 });
  }

  const handledByRule = onUserMessage(channel.id, text, me.id);
  const addressed = channel.kind === "dm" ? channel.peer === "exi" : REPLY_ALL || MENTION.test(text);
  if (addressed && !handledByRule) {
    const files = attachments.length ? `\n\nAttached files: ${attachments.map((a) => a.name).join(", ")}` : "";
    const command = text.replace(MENTION, " ").trim() || "Review the attached files";
    startRun({ channelId: channel.id, command: command + files, requestedBy: me.id });
  }
  return Response.json({ message }, { status: 201 });
});
