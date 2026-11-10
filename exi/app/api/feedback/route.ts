import { handle, requireUser } from "@/lib/server/auth";
import { submitFeedback } from "@/lib/server/feedback";
import { FeedbackSchema, parseJson } from "@/lib/server/validation";

export const POST = handle(async (req: Request) => {
  const me = await requireUser(req);
  const { text } = await parseJson(req, FeedbackSchema);
  return Response.json({ item: submitFeedback(text, me) }, { status: 202 });
});
