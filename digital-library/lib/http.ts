export function bad(message: string, status = 400) {
  return Response.json({ error: message }, { status });
}

export async function readJson<T = Record<string, unknown>>(req: Request): Promise<T | null> {
  try {
    return (await req.json()) as T;
  } catch {
    return null;
  }
}

export const str = (v: unknown, max = 20000) =>
  typeof v === "string" ? v.trim().slice(0, max) : "";
