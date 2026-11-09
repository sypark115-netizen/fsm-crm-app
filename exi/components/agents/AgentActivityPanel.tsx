"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, CircleDashed, Loader2, X, XCircle, Zap } from "lucide-react";
import { AGENTS, SPECIALISTS } from "@/lib/agents";
import { formatTime } from "@/lib/ids";
import type { AgentRun, RunStep } from "@/lib/types";
import { Avatar } from "./Avatar";

function StepIcon({ status }: { status: RunStep["status"] }) {
  if (status === "done") return <CheckCircle2 size={16} className="text-emerald-600" />;
  if (status === "working") return <Loader2 size={16} className="animate-spin text-violet-600" />;
  return <CircleDashed size={16} className="text-slate-300" />;
}

function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, [active]);
  return now;
}

function RunCard({ run, selected, onSelect }: { run: AgentRun; selected: boolean; onSelect: () => void }) {
  const live = run.status === "planning" || run.status === "running";
  const now = useNow(live);
  const done = run.steps.filter((s) => s.status === "done").length;
  const pct = run.steps.length ? Math.round((done / run.steps.length) * 100) : run.status === "done" ? 100 : 8;
  const elapsed = (((run.finishedAt ?? now) - run.startedAt) / 1000).toFixed(1);

  return (
    <div
      className={`rounded-xl border bg-white p-3 transition ${selected ? "border-violet-400 shadow-md" : "border-slate-200 hover:border-slate-300"}`}
    >
      <button className="w-full text-left" onClick={onSelect}>
        <div className="flex items-center gap-2">
          <Avatar author="exi" size="sm" pulse={live} />
          <span className="min-w-0 flex-1 truncate text-sm font-semibold">{run.command}</span>
          {run.automationId && <Zap size={13} className="shrink-0 text-orange-500" />}
        </div>
        <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-500">
          <span
            className={`rounded px-1.5 py-0.5 font-semibold uppercase ${
              run.status === "done"
                ? "bg-emerald-50 text-emerald-700"
                : run.status === "failed"
                  ? "bg-red-50 text-red-700"
                  : "bg-violet-50 text-violet-700"
            }`}
          >
            {run.status}
          </span>
          {run.source && <span>{run.source === "claude" ? "Claude" : "mock planner"}</span>}
          <span className="ml-auto tabular-nums">{elapsed}s</span>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full transition-all duration-500 ${run.status === "failed" ? "bg-red-400" : "bg-violet-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </button>

      {selected && (
        <ol className="mt-3 space-y-0">
          <li className="flex gap-2.5 pb-3">
            <div className="flex flex-col items-center">
              {run.status === "planning" ? (
                <Loader2 size={16} className="animate-spin text-violet-600" />
              ) : run.status === "failed" && run.steps.length === 0 ? (
                <XCircle size={16} className="text-red-500" />
              ) : (
                <CheckCircle2 size={16} className="text-emerald-600" />
              )}
              <div className="mt-1 w-px flex-1 bg-slate-200" />
            </div>
            <div className="min-w-0 text-xs">
              <div className="font-semibold text-slate-800">Exi · Plan & delegate</div>
              <div className="text-slate-500">{run.summary ?? run.error ?? "Reading the request…"}</div>
            </div>
          </li>
          {run.steps.map((s, i) => (
            <li key={s.id} className="flex gap-2.5 pb-3">
              <div className="flex flex-col items-center">
                <StepIcon status={s.status} />
                {i < run.steps.length - 1 && <div className="mt-1 w-px flex-1 bg-slate-200" />}
              </div>
              <div className="min-w-0 text-xs">
                <div className="flex items-center gap-1.5">
                  <Avatar author={s.agent} size="sm" />
                  <span className="font-semibold text-slate-800">{AGENTS[s.agent].name}</span>
                  {s.finishedAt && s.startedAt && (
                    <span className="text-slate-400 tabular-nums">{((s.finishedAt - s.startedAt) / 1000).toFixed(1)}s</span>
                  )}
                </div>
                <div className="mt-0.5 font-medium text-slate-700">{s.title}</div>
                <div className="text-slate-500">{s.detail}</div>
              </div>
            </li>
          ))}
          {run.status === "failed" && run.error && <li className="text-xs text-red-600">{run.error}</li>}
        </ol>
      )}
    </div>
  );
}

export function AgentActivityPanel({
  runs,
  selectedRunId,
  onSelectRun,
  onClose,
}: {
  runs: AgentRun[];
  selectedRunId?: string;
  onSelectRun: (id: string) => void;
  onClose: () => void;
}) {
  const ordered = [...runs].sort((a, b) => b.startedAt - a.startedAt);
  const busy = new Set(
    runs.flatMap((r) => r.steps.filter((s) => s.status === "working").map((s) => s.agent as string)),
  );
  if (runs.some((r) => r.status === "planning")) busy.add("exi");

  return (
    <aside className="flex h-full w-full flex-col border-l border-slate-200 bg-slate-50 lg:w-96">
      <div className="flex h-12 items-center gap-2 border-b border-slate-200 bg-white px-4">
        <Activity size={16} className="text-violet-600" />
        <span className="font-semibold">Agent Activity</span>
        <button className="ml-auto rounded p-1 hover:bg-slate-100" onClick={onClose} aria-label="Close panel">
          <X size={16} />
        </button>
      </div>

      <div className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="mb-2 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">Agent roster</div>
        <div className="grid grid-cols-2 gap-1.5">
          {(["exi", ...SPECIALISTS] as const).map((id) => (
            <div key={id} className="flex items-center gap-2 rounded-md px-1.5 py-1 text-xs">
              <Avatar author={id} size="sm" />
              <div className="min-w-0">
                <div className="font-semibold">{AGENTS[id].name}</div>
                <div className={`truncate ${busy.has(id) ? "text-violet-700" : "text-slate-400"}`}>
                  {busy.has(id) ? "working…" : "idle"}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {ordered.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">
            No runs in this channel yet. Send a request and watch Exi coordinate the team here.
          </p>
        ) : (
          ordered.map((r) => (
            <RunCard key={r.id} run={r} selected={r.id === selectedRunId} onSelect={() => onSelectRun(r.id)} />
          ))
        )}
        {ordered.length > 0 && (
          <p className="pt-1 text-center text-[11px] text-slate-400">Last run {formatTime(ordered[0].startedAt)}</p>
        )}
      </div>
    </aside>
  );
}
