import crypto from "node:crypto";
import { cookies } from "next/headers";
import type { User } from "../types";
import { db } from "./db";
import { getUserById } from "./repo";

export const SESSION_COOKIE = "exi_session";
const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;

/* -------------------------------- passwords ------------------------------- */

export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(password, salt, 64);
  return `scrypt$${salt.toString("base64")}$${hash.toString("base64")}`;
}

export function verifyPassword(password: string, stored: string): boolean {
  const [scheme, saltB64, hashB64] = stored.split("$");
  if (scheme !== "scrypt" || !saltB64 || !hashB64) return false;
  const expected = Buffer.from(hashB64, "base64");
  const actual = crypto.scryptSync(password, Buffer.from(saltB64, "base64"), expected.length);
  return crypto.timingSafeEqual(actual, expected);
}

/* -------------------------------- sessions -------------------------------- */

const sha256 = (s: string) => crypto.createHash("sha256").update(s).digest("hex");

export function createSession(userId: string): { token: string; expiresAt: number } {
  const token = crypto.randomBytes(32).toString("base64url");
  const expiresAt = Date.now() + SESSION_TTL_MS;
  db.prepare("DELETE FROM sessions WHERE expires_at < ?").run(Date.now());
  db.prepare("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?,?,?)").run(sha256(token), userId, expiresAt);
  return { token, expiresAt };
}

export function deleteSession(token: string) {
  db.prepare("DELETE FROM sessions WHERE token_hash = ?").run(sha256(token));
}

export function userForToken(token: string | undefined): User | null {
  if (!token) return null;
  const row = db
    .prepare("SELECT user_id, expires_at FROM sessions WHERE token_hash = ?")
    .get(sha256(token)) as { user_id: string; expires_at: number } | undefined;
  if (!row || row.expires_at < Date.now()) return null;
  return getUserById(row.user_id);
}

/** Current user from the session cookie (Server Components and Route Handlers). */
export async function currentUser(): Promise<User | null> {
  const jar = await cookies();
  return userForToken(jar.get(SESSION_COOKIE)?.value);
}

export function isSecureRequest(req: Request): boolean {
  return new URL(req.url).protocol === "https:" || req.headers.get("x-forwarded-proto") === "https";
}

/* ------------------------------ request guards ---------------------------- */

export class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/**
 * For mutating requests: require a session and a same-origin request.
 * SameSite=Lax cookies plus this Origin check cover CSRF for a JSON API.
 */
export async function requireUser(req: Request): Promise<User> {
  if (req.method !== "GET" && req.method !== "HEAD") assertSameOrigin(req);
  const user = await currentUser();
  if (!user) throw new HttpError(401, "Please sign in");
  return user;
}

export function assertSameOrigin(req: Request) {
  const origin = req.headers.get("origin");
  if (!origin) return; // non-browser clients
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  if (!host || new URL(origin).host !== host) throw new HttpError(403, "Cross-origin request blocked");
}

/** Wrap a route handler so HttpErrors become JSON responses. */
export function handle<A extends unknown[]>(fn: (...args: A) => Promise<Response>) {
  return async (...args: A): Promise<Response> => {
    try {
      return await fn(...args);
    } catch (err) {
      if (err instanceof HttpError) return Response.json({ error: err.message }, { status: err.status });
      console.error("[exi] unhandled route error", err);
      return Response.json({ error: "Internal server error" }, { status: 500 });
    }
  };
}

/* ------------------------------ login throttle ---------------------------- */

const attempts = new Map<string, { n: number; until: number }>();

export function checkLoginThrottle(key: string) {
  const a = attempts.get(key);
  if (a && a.n >= 5 && a.until > Date.now()) throw new HttpError(429, "Too many attempts — try again in a minute");
}

export function recordLoginFailure(key: string) {
  const a = attempts.get(key);
  const fresh = !a || a.until < Date.now();
  attempts.set(key, { n: fresh ? 1 : a.n + 1, until: Date.now() + 60_000 });
}

export function clearLoginFailures(key: string) {
  attempts.delete(key);
}
