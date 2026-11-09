"use client";

import { useState } from "react";
import { Lightbulb, Loader2, Rocket, X } from "lucide-react";
import { Avatar } from "@/components/agents/Avatar";
import { AGENTS } from "@/lib/agents";
import { formatTime, uid } from "@/lib/ids";
import type { Dispatch } from "@/lib/store";
import type { AgentId, FeedbackItem } from "@/lib/types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const STATUS_FOR: Record<number, FeedbackItem["status"]> = { 1: "triaging", 2: "building", 3: "building", 4: "shipped" };

export function FeedbackWidget({ items, appVersion, dispatch }: { items: FeedbackItem[]; appVersion: string; dispatch: Dispatch }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = items.some((i) => i.status !== "shipped");

  const submit = async () => {
    const t = text.trim();
    if (t.length < 3 || sending) return;
    setSending(true);
    setError(null);
    const id = uid("fb");
    dispatch({ type: "addFeedback", item: { id, text: t, createdAt: Date.now(), status: "received", log: [] } });
    setText("");
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: t, currentVersion: appVersion }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.error ?? `HTTP ${res.status}`);
      const data: { version: string; log: { delayMs: number; agent: AgentId; text: string }[] } = await res.json();
      setSending(false);
      // Replay the iteration log so it reads like a live feed.
      for (const [i, entry] of data.log.entries()) {
        await sleep(entry.delayMs);
        const last = i === data.log.length - 1;
        dispatch({
          type: "appendFeedbackLog",
          id,
          entry: { at: Date.now(), agent: entry.agent, text: entry.text },
          patch: { status: STATUS_FOR[i] ?? "received", ...(last ? { version: data.version } : {}) },
        });
        if (last) dispatch({ type: "setVersion", version: data.version });
      }
    } catch (err) {
      setSending(false);
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-4 left-4 z-30 flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg hover:brightness-110"
        aria-expanded={open}
      >
        {inFlight ? <Loader2 size={16} className="animate-spin" /> : <Lightbulb size={16} />}
        Feedback / Improve
      </button>

      {open && (
        <div className="fixed bottom-16 left-4 z-30 flex max-h-[70vh] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
            <Rocket size={16} className="text-violet-600" />
            <div>
              <div className="text-sm font-bold">Help Exi improve itself</div>
              <div className="text-[11px] text-slate-500">Agents triage, build and ship your suggestion · now v{appVersion}</div>
            </div>
            <button className="ml-auto rounded p-1 hover:bg-slate-100" onClick={() => setOpen(false)} aria-label="Close">
              <X size={16} />
            </button>
          </div>

          <div className="space-y-2 p-4">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              placeholder="e.g. Let me pin important agent reports in a channel"
              className="input resize-none"
            />
            {error && <p className="text-xs text-red-600">{error}</p>}
            <button
              onClick={submit}
              disabled={text.trim().length < 3 || sending}
              className="w-full rounded-md bg-violet-600 py-2 text-sm font-semibold text-white disabled:bg-slate-200 disabled:text-slate-400"
            >
              {sending ? "Sending…" : "Submit feedback"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto border-t border-slate-100 px-4 py-3">
            <div className="mb-2 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">Iteration log</div>
            {items.length === 0 && <p className="text-xs text-slate-500">No feedback yet — yours will show up here.</p>}
            <ul className="space-y-3">
              {items.map((f) => (
                <li key={f.id} className="rounded-lg bg-slate-50 p-2.5">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="min-w-0 flex-1 truncate font-semibold">“{f.text}”</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                        f.status === "shipped" ? "bg-emerald-100 text-emerald-700" : "bg-violet-100 text-violet-700"
                      }`}
                    >
                      {f.status === "shipped" ? `v${f.version}` : f.status}
                    </span>
                  </div>
                  <ul className="mt-2 space-y-1.5">
                    {f.log.map((l, i) => (
                      <li key={i} className="flex gap-2 text-xs">
                        <Avatar author={l.agent} size="sm" />
                        <div className="min-w-0">
                          <span className="font-semibold">{AGENTS[l.agent].name}</span>{" "}
                          <span className="text-slate-400">{formatTime(l.at)}</span>
                          <div className="text-slate-600" dangerouslySetInnerHTML={{ __html: inlineMd(l.text) }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </>
  );
}

/** Tiny, escape-first inline markdown (bold, italic, code) for log lines. */
function inlineMd(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="font-mono text-[11px]">$1</code>');
}
