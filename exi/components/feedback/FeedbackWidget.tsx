"use client";

import { useState } from "react";
import { ExternalLink, Lightbulb, Loader2, Rocket, X } from "lucide-react";
import { Avatar } from "@/components/agents/Avatar";
import { Markdown } from "@/components/chat/Markdown";
import { AGENTS } from "@/lib/agents";
import { api } from "@/lib/client/api";
import { formatTime } from "@/lib/ids";
import type { FeedbackItem, User } from "@/lib/types";

const BADGE: Record<FeedbackItem["status"], string> = {
  received: "bg-slate-100 text-slate-600",
  triaging: "bg-violet-100 text-violet-700",
  filed: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

export function FeedbackWidget({
  items,
  users,
  githubEnabled,
}: {
  items: FeedbackItem[];
  users: Record<string, User>;
  githubEnabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = items.some((i) => i.status === "received" || i.status === "triaging");

  const submit = async () => {
    const t = text.trim();
    if (t.length < 3 || sending) return;
    setSending(true);
    setError(null);
    try {
      await api("/api/feedback", { body: { text: t } });
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSending(false);
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
        <div className="fixed bottom-16 left-4 z-30 flex max-h-[75vh] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
            <Rocket size={16} className="text-violet-600" />
            <div>
              <div className="text-sm font-bold">Help Exi improve</div>
              <div className="text-[11px] text-slate-500">
                {githubEnabled ? "Agents triage it and file a GitHub issue for the dev team" : "Agents triage it into the team backlog"}
              </div>
            </div>
            <button className="ml-auto rounded p-1 hover:bg-slate-100" onClick={() => setOpen(false)} aria-label="Close feedback">
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
              onClick={() => void submit()}
              disabled={text.trim().length < 3 || sending}
              className="w-full rounded-md bg-violet-600 py-2 text-sm font-semibold text-white disabled:bg-slate-200 disabled:text-slate-400"
            >
              {sending ? "Sending…" : "Submit feedback"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto border-t border-slate-100 px-4 py-3">
            <div className="mb-2 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">Improvement log</div>
            {items.length === 0 && <p className="text-xs text-slate-500">No feedback yet — yours will show up here.</p>}
            <ul className="space-y-3">
              {items.map((f) => (
                <li key={f.id} className="rounded-lg bg-slate-50 p-2.5">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="min-w-0 flex-1 truncate font-semibold">{f.title ?? `“${f.text}”`}</span>
                    {f.priority && <span className="text-[10px] font-semibold text-slate-500">{f.priority}</span>}
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${BADGE[f.status]}`}>{f.status}</span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-400">
                    by {f.createdBy ? (users[f.createdBy]?.displayName ?? "member") : "member"}
                  </div>
                  {f.issueUrl && (
                    <a
                      href={f.issueUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-violet-700 hover:underline"
                    >
                      Open GitHub issue <ExternalLink size={11} />
                    </a>
                  )}
                  <ul className="mt-2 space-y-1.5">
                    {f.log.map((l, i) => (
                      <li key={i} className="flex gap-2 text-xs">
                        <Avatar author={l.agent} size="sm" />
                        <div className="min-w-0">
                          <span className="font-semibold">{AGENTS[l.agent].name}</span>{" "}
                          <span className="text-slate-400">{formatTime(l.at)}</span>
                          <div className="text-slate-600 [&_.prose-chat]:text-xs">
                            <Markdown text={l.text} />
                          </div>
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
