import { z } from "zod";

export const PlanStepSchema = z.object({
  agent: z.enum(["planner", "researcher", "coder", "marketer", "analyst"]),
  title: z.string().describe("Short imperative task title, max ~8 words"),
  detail: z.string().describe("One sentence on what the agent is asked to do"),
  output: z.string().describe("The agent's deliverable in concise Markdown (bullets, tables or code)"),
});

export const PlanSchema = z.object({
  summary: z.string().describe("One or two sentences: how Exi will tackle the request"),
  steps: z.array(PlanStepSchema).describe("2-5 delegated steps in execution order"),
  finalReport: z.string().describe("Exi's consolidated Markdown report to the requester, with next actions"),
});

export const PlanRequestSchema = z.object({
  command: z.string().min(1).max(4000),
  channelName: z.string().max(80).optional(),
  history: z
    .array(z.object({ author: z.string(), text: z.string().max(2000) }))
    .max(20)
    .optional(),
});

export type PlanRequest = z.infer<typeof PlanRequestSchema>;
