import { claudeEnabled, claudePlan } from "@/lib/orchestrator/claudePlanner";
import { mockPlan } from "@/lib/orchestrator/mockPlanner";
import { PlanRequestSchema } from "@/lib/orchestrator/schema";

export const runtime = "nodejs";

/**
 * POST /api/exi — Exi turns a channel command into a delegation plan.
 * Uses Claude when ANTHROPIC_API_KEY is set, otherwise the offline mock planner.
 * The client animates the returned steps so users see agents collaborate.
 */
export async function POST(request: Request) {
  const body = PlanRequestSchema.safeParse(await request.json().catch(() => null));
  if (!body.success) {
    return Response.json({ error: "Invalid request", issues: body.error.issues }, { status: 400 });
  }

  if (claudeEnabled()) {
    try {
      return Response.json(await claudePlan(body.data));
    } catch (err) {
      console.error("[exi] Claude planner failed, falling back to mock:", err);
      const plan = mockPlan(body.data.command);
      return Response.json({ ...plan, warning: "Claude unavailable — used mock planner" });
    }
  }

  return Response.json(mockPlan(body.data.command));
}

export async function GET() {
  return Response.json({ planner: claudeEnabled() ? "claude" : "mock" });
}
