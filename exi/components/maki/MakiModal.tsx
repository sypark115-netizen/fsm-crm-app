"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Play, Radio, Trash2, X, Zap } from "lucide-react";
import { uid } from "@/lib/ids";
import { describeCron, isValidCron, nextRun, naturalToCron } from "@/lib/maki/cron";
import type { Automation, Channel } from "@/lib/types";

const PRESETS = [
  { label: "Daily 9 AM", cron: "0 9 * * *" },
  { label: "Weekdays 8:30", cron: "30 8 * * 1-5" },
  { label: "Mondays 10 AM", cron: "0 10 * * 1" },
  { label: "Hourly", cron: "0 * * * *" },
  { label: "Every 5 min", cron: "*/5 * * * *" },
];

interface Props {
  channels: Channel[];
  automations: Automation[];
  defaultChannelId: string;
  onClose: () => void;
  onCreate: (a: Automation) => void;
  onToggle: (id: string, enabled: boolean) => void;
  onDelete: (id: string) => void;
  onRunNow: (a: Automation) => void;
}

export function MakiModal({ channels, automations, defaultChannelId, onClose, onCreate, onToggle, onDelete, onRunNow }: Props) {
  const [kind, setKind] = useState<"schedule" | "event">("schedule");
  const [quick, setQuick] = useState("");
  const [name, setName] = useState("");
  const [cron, setCron] = useState("0 9 * * *");
  const [keyword, setKeyword] = useState("");
  const [channelId, setChannelId] = useState(defaultChannelId);
  const [command, setCommand] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const cronOk = isValidCron(cron);
  const next = useMemo(() => (cronOk ? nextRun(cron) : null), [cron, cronOk]);
  const valid = name.trim() && command.trim() && (kind === "schedule" ? cronOk : keyword.trim());

  // "Run daily competitor analysis at 9 AM" → name, cron and command in one go.
  const applyQuick = () => {
    const c = naturalToCron(quick);
    if (c) setCron(c);
    setKind("schedule");
    const task = quick
      .replace(/\b(every|each)\s+(day|weekday|monday|tuesday|wednesday|thursday|friday|saturday|sunday|hour)s?\b/gi, "")
      .replace(/\b(daily|hourly|weekdays?)\b/gi, "")
      .replace(/\bat\s+\d{1,2}(:\d{2})?\s*(am|pm)?\b/gi, "")
      .replace(/\s+/g, " ")
      .trim();
    if (task) {
      setCommand(task);
      setName(task.replace(/^run\s+/i, "").replace(/^./, (s) => s.toUpperCase()).slice(0, 60));
    }
  };

  const create = () => {
    if (!valid) return;
    onCreate({
      id: uid("auto"),
      name: name.trim(),
      trigger:
        kind === "schedule"
          ? { type: "schedule", cron: cron.trim() }
          : { type: "event", event: "message_contains", keyword: keyword.trim(), channelId: undefined },
      channelId,
      command: command.trim(),
      enabled: true,
      createdAt: Date.now(),
      runCount: 0,
    });
    setName("");
    setCommand("");
    setKeyword("");
    setQuick("");
  };

  const channelName = (id: string) => channels.find((c) => c.id === id)?.name ?? "unknown";

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-label="Maki automations"
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-500 text-white">
            <Zap size={18} />
          </span>
          <div>
            <h2 className="font-bold">Maki · Automation Engine</h2>
            <p className="text-xs text-slate-500">Scheduled and event-driven tasks that Exi runs for you.</p>
          </div>
          <button className="ml-auto rounded p-1.5 hover:bg-slate-100" onClick={onClose} aria-label="Close automations">
            <X size={18} />
          </button>
        </div>

        <div className="grid flex-1 overflow-y-auto md:grid-cols-[1fr_1.1fr]">
          {/* Create */}
          <section className="space-y-3 border-b border-slate-200 p-5 md:border-r md:border-b-0">
            <label className="block text-xs font-semibold text-slate-600">Describe it in plain words</label>
            <div className="flex gap-2">
              <input
                value={quick}
                onChange={(e) => setQuick(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyQuick()}
                placeholder="Run daily competitor analysis at 9 AM"
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-violet-500"
              />
              <button onClick={applyQuick} className="rounded-md bg-slate-900 px-3 text-sm font-medium text-white">
                Fill
              </button>
            </div>

            <div className="flex rounded-lg bg-slate-100 p-1 text-sm">
              {(["schedule", "event"] as const).map((k) => (
                <button
                  key={k}
                  onClick={() => setKind(k)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 ${kind === k ? "bg-white font-semibold shadow-sm" : "text-slate-600"}`}
                >
                  {k === "schedule" ? <CalendarClock size={14} /> : <Radio size={14} />}
                  {k === "schedule" ? "Schedule" : "Event"}
                </button>
              ))}
            </div>

            <Field label="Name">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Daily competitor analysis" className="input" />
            </Field>

            {kind === "schedule" ? (
              <Field label="When (cron)">
                <div className="mb-2 flex flex-wrap gap-1.5">
                  {PRESETS.map((p) => (
                    <button
                      key={p.cron}
                      onClick={() => setCron(p.cron)}
                      className={`rounded-full border px-2.5 py-0.5 text-xs ${cron === p.cron ? "border-violet-500 bg-violet-50 text-violet-700" : "border-slate-200"}`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <input value={cron} onChange={(e) => setCron(e.target.value)} className="input font-mono" />
                <p className={`mt-1 text-xs ${cronOk ? "text-slate-500" : "text-red-600"}`}>
                  {describeCron(cron)}
                  {next && ` · next ${new Date(next).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}`}
                </p>
              </Field>
            ) : (
              <Field label="When a message contains">
                <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="outage" className="input" />
              </Field>
            )}

            <Field label="Post results in">
              <select value={channelId} onChange={(e) => setChannelId(e.target.value)} className="input">
                {channels.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.kind === "channel" ? `#${c.name}` : `@${c.name}`}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Task for Exi">
              <textarea
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                rows={3}
                placeholder="Analyze competitor moves in the AI agent market and summarize what changed"
                className="input resize-none"
              />
            </Field>

            <button
              disabled={!valid}
              onClick={create}
              className="w-full rounded-md bg-orange-500 py-2 text-sm font-semibold text-white disabled:bg-slate-200 disabled:text-slate-400"
            >
              Create automation
            </button>
          </section>

          {/* List */}
          <section className="p-5">
            <h3 className="mb-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">
              Rules ({automations.length})
            </h3>
            <ul className="space-y-2">
              {automations.map((a) => (
                <li key={a.id} className={`rounded-xl border p-3 ${a.enabled ? "border-slate-200" : "border-dashed border-slate-200 opacity-60"}`}>
                  <div className="flex items-start gap-2">
                    {a.trigger.type === "schedule" ? (
                      <CalendarClock size={16} className="mt-0.5 text-orange-500" />
                    ) : (
                      <Radio size={16} className="mt-0.5 text-sky-500" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-semibold">{a.name}</div>
                      <div className="text-xs text-slate-500">
                        {a.trigger.type === "schedule" ? describeCron(a.trigger.cron) : `On message containing “${a.trigger.keyword}”`}
                        {" → "}#{channelName(a.channelId)}
                      </div>
                      <div className="mt-1 line-clamp-2 text-xs text-slate-600">{a.command}</div>
                      <div className="mt-1 text-[11px] text-slate-400">
                        Ran {a.runCount}×{a.lastRunAt ? ` · last ${new Date(a.lastRunAt).toLocaleTimeString()}` : ""}
                      </div>
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        className="peer sr-only"
                        checked={a.enabled}
                        onChange={(e) => onToggle(a.id, e.target.checked)}
                        aria-label={`Enable ${a.name}`}
                      />
                      <span className="h-5 w-9 rounded-full bg-slate-300 transition peer-checked:bg-orange-500" />
                      <span className="absolute left-0.5 h-4 w-4 rounded-full bg-white transition peer-checked:translate-x-4" />
                    </label>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <button
                      onClick={() => onRunNow(a)}
                      className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
                    >
                      <Play size={12} /> Run now
                    </button>
                    <button
                      onClick={() => onDelete(a.id)}
                      className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                  </div>
                </li>
              ))}
              {automations.length === 0 && <li className="text-sm text-slate-500">No rules yet.</li>}
            </ul>
            <p className="mt-4 text-[11px] text-slate-400">
              Prototype note: schedules are evaluated in the browser every 15s while the app is open. Production would move
              this to a server-side worker (e.g. a cron job or queue).
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold text-slate-600">{label}</label>
      {children}
    </div>
  );
}
