import { z } from "zod";
import { isValidCron } from "../maki/cron";
import { HttpError } from "./auth";

export async function parseJson<T extends z.ZodType>(req: Request, schema: T): Promise<z.infer<T>> {
  if (!(req.headers.get("content-type") ?? "").includes("application/json")) {
    throw new HttpError(415, "Expected application/json");
  }
  const parsed = schema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) {
    const first = parsed.error.issues[0];
    throw new HttpError(400, first ? `${first.path.join(".") || "body"}: ${first.message}` : "Invalid request");
  }
  return parsed.data;
}

export const SignupSchema = z.object({
  username: z
    .string()
    .trim()
    .min(3)
    .max(32)
    .regex(/^[a-zA-Z0-9_.-]+$/, "letters, numbers, . _ - only"),
  displayName: z.string().trim().min(1).max(40),
  password: z.string().min(8).max(200),
  inviteCode: z.string().max(200).optional(),
});

export const LoginSchema = z.object({
  username: z.string().trim().min(1).max(32),
  password: z.string().min(1).max(200),
});

export const ChannelSchema = z.object({
  name: z
    .string()
    .trim()
    .toLowerCase()
    .min(1)
    .max(40)
    .regex(/^[a-z0-9가-힣_-]+$/, "use lowercase letters, numbers, - or _"),
  topic: z.string().trim().max(200).optional(),
});

export const MessageSchema = z.object({
  channelId: z.string().min(1).max(64),
  text: z.string().max(8000),
  attachmentIds: z.array(z.string().max(64)).max(5).optional(),
});

const TriggerSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("schedule"),
    cron: z.string().trim().refine(isValidCron, "invalid cron expression"),
  }),
  z.object({
    type: z.literal("event"),
    event: z.literal("message_contains"),
    keyword: z.string().trim().min(2).max(60),
    channelId: z.string().max(64).optional(),
  }),
]);

export const AutomationCreateSchema = z.object({
  name: z.string().trim().min(1).max(80),
  trigger: TriggerSchema,
  channelId: z.string().min(1).max(64),
  command: z.string().trim().min(3).max(2000),
});

export const AutomationPatchSchema = z
  .object({
    name: z.string().trim().min(1).max(80),
    enabled: z.boolean(),
    command: z.string().trim().min(3).max(2000),
    trigger: TriggerSchema,
  })
  .partial();

export const FeedbackSchema = z.object({ text: z.string().trim().min(3).max(4000) });
