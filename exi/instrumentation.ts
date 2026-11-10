export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  // `next build` also loads this file; only start background work in a real server.
  if (process.env.NEXT_PHASE === "phase-production-build") return;
  const { failInterruptedRuns } = await import("./lib/server/repo");
  const { startScheduler } = await import("./lib/server/maki");
  failInterruptedRuns();
  startScheduler();
}
