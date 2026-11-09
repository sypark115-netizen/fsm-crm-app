// Minimal 5-field cron ("min hour day-of-month month day-of-week") evaluator.
// Supports "*", numbers, lists (1,2), ranges (1-5) and steps (*/15, 1-10/2).

const FIELDS = [
  { min: 0, max: 59 },
  { min: 0, max: 23 },
  { min: 1, max: 31 },
  { min: 1, max: 12 },
  { min: 0, max: 6 },
] as const;

type ParsedCron = Set<number>[];

function parseField(expr: string, min: number, max: number): Set<number> {
  const out = new Set<number>();
  for (const part of expr.split(",")) {
    const [rangePart, stepPart] = part.split("/");
    const step = stepPart ? Number(stepPart) : 1;
    if (!Number.isInteger(step) || step < 1) throw new Error(`Bad step "${part}"`);
    let lo = min;
    let hi = max;
    if (rangePart !== "*") {
      const [a, b] = rangePart.split("-").map(Number);
      if (!Number.isInteger(a)) throw new Error(`Bad value "${part}"`);
      lo = a;
      hi = b === undefined ? (stepPart ? max : a) : b;
    }
    if (lo < min || hi > max || lo > hi) throw new Error(`Out of range "${part}"`);
    for (let v = lo; v <= hi; v += step) out.add(v);
  }
  return out;
}

export function parseCron(cron: string): ParsedCron {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) throw new Error("Cron needs 5 fields: min hour day month weekday");
  return parts.map((p, i) => parseField(p, FIELDS[i].min, FIELDS[i].max));
}

export function isValidCron(cron: string): boolean {
  try {
    parseCron(cron);
    return true;
  } catch {
    return false;
  }
}

function matches(p: ParsedCron, d: Date): boolean {
  return (
    p[0].has(d.getMinutes()) &&
    p[1].has(d.getHours()) &&
    p[2].has(d.getDate()) &&
    p[3].has(d.getMonth() + 1) &&
    p[4].has(d.getDay())
  );
}

/** Next fire time strictly after `from` (searches up to ~1 year). */
export function nextRun(cron: string, from = Date.now()): number | null {
  let p: ParsedCron;
  try {
    p = parseCron(cron);
  } catch {
    return null;
  }
  const d = new Date(from);
  d.setSeconds(0, 0);
  d.setMinutes(d.getMinutes() + 1);
  for (let i = 0; i < 366 * 24 * 60; i++) {
    if (matches(p, d)) return d.getTime();
    d.setMinutes(d.getMinutes() + 1);
  }
  return null;
}

/** True if the cron fired in the window (since, now]. */
export function firedBetween(cron: string, since: number, now: number): boolean {
  const n = nextRun(cron, since);
  return n !== null && n <= now;
}

const DOW = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function hhmm(h: number, m: number) {
  const suffix = h >= 12 ? "PM" : "AM";
  const hr = h % 12 === 0 ? 12 : h % 12;
  return `${hr}:${String(m).padStart(2, "0")} ${suffix}`;
}

/** Human-readable description for the common shapes; falls back to the raw expression. */
export function describeCron(cron: string): string {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5 || !isValidCron(cron)) return "Invalid schedule";
  const [m, h, dom, mon, dow] = parts;
  const fixedTime = /^\d+$/.test(m) && /^\d+$/.test(h);
  if (m.startsWith("*/") && h === "*" && dom === "*" && mon === "*" && dow === "*") return `Every ${m.slice(2)} minutes`;
  if (/^\d+$/.test(m) && h === "*" && dom === "*" && mon === "*" && dow === "*") return `Hourly at :${m.padStart(2, "0")}`;
  if (fixedTime && dom === "*" && mon === "*") {
    const t = hhmm(Number(h), Number(m));
    if (dow === "*") return `Every day at ${t}`;
    if (dow === "1-5") return `Weekdays at ${t}`;
    if (/^\d$/.test(dow)) return `Every ${DOW[Number(dow)]} at ${t}`;
  }
  if (fixedTime && /^\d+$/.test(dom) && mon === "*" && dow === "*") return `Monthly on day ${dom} at ${hhmm(Number(h), Number(m))}`;
  return `cron: ${cron}`;
}

/**
 * Turns phrases like "daily at 9 AM", "every monday at 14:30", "weekdays 8am",
 * "every 15 minutes", "hourly" into cron. Returns null when nothing matches.
 */
export function naturalToCron(text: string): string | null {
  const t = text.toLowerCase();
  const every = t.match(/every\s+(\d+)\s*(?:min|minutes?)/);
  if (every) return `*/${every[1]} * * * *`;
  if (/\bhourly\b|every hour/.test(t)) return "0 * * * *";

  const time = t.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/);
  let hour = 9;
  let minute = 0;
  if (time) {
    hour = Number(time[1]);
    minute = time[2] ? Number(time[2]) : 0;
    if (time[3] === "pm" && hour < 12) hour += 12;
    if (time[3] === "am" && hour === 12) hour = 0;
    if (hour > 23 || minute > 59) return null;
  }
  const dowIdx = DOW.findIndex((d) => t.includes(d.toLowerCase()));
  if (dowIdx >= 0) return `${minute} ${hour} * * ${dowIdx}`;
  if (/weekday/.test(t)) return `${minute} ${hour} * * 1-5`;
  if (/daily|every day|each day|매일/.test(t) || time) return `${minute} ${hour} * * *`;
  return null;
}
