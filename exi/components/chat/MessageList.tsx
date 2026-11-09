"use client";

import { useEffect, useRef } from "react";
import { Zap } from "lucide-react";
import { Avatar } from "@/components/agents/Avatar";
import { AGENTS } from "@/lib/agents";
import { formatDay, formatTime } from "@/lib/ids";
import type { AgentRun, Message } from "@/lib/types";
import { Markdown } from "./Markdown";
import { AttachmentCard, LinkPreview, extractUrls } from "./Previews";

const GROUP_WINDOW_MS = 5 * 60 * 1000;

function TypingIndicator({ run }: { run: AgentRun }) {
  const working = run.steps.find((s) => s.status === "working");
  const who = working ? AGENTS[working.agent] : AGENTS.exi;
  const label = run.status === "planning" ? "Exi is planning" : `${who.name} is working on “${working?.title ?? "…"}”`;
  return (
    <div className="flex items-center gap-3 px-5 py-2 text-sm text-slate-500">
      <Avatar author={working?.agent ?? "exi"} size="sm" />
      <span>{label}</span>
      <span className="flex gap-0.5">
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
      </span>
    </div>
  );
}

export function MessageList({
  messages,
  activeRun,
  onSelectRun,
}: {
  messages: Message[];
  activeRun?: AgentRun;
  onSelectRun: (runId: string) => void;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, activeRun?.status, activeRun?.steps]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-center text-slate-500">
        <div>
          <p className="text-lg font-semibold text-slate-700">This is the very beginning of the conversation.</p>
          <p className="mt-1 text-sm">Type a request below — Exi will plan it and bring in the right agents.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto py-4">
      {messages.map((m, i) => {
        const prev = messages[i - 1];
        const newDay = !prev || new Date(prev.createdAt).toDateString() !== new Date(m.createdAt).toDateString();
        const grouped = !newDay && prev && prev.author === m.author && m.createdAt - prev.createdAt < GROUP_WINDOW_MS;
        const author = AGENTS[m.author];
        const urls = extractUrls(m.text);
        return (
          <div key={m.id}>
            {newDay && (
              <div className="relative my-3 flex items-center justify-center">
                <div className="absolute inset-x-0 top-1/2 border-t border-slate-200" />
                <span className="relative rounded-full border border-slate-200 bg-white px-3 py-0.5 text-xs font-semibold text-slate-600">
                  {formatDay(m.createdAt)}
                </span>
              </div>
            )}
            <div className={`group flex gap-3 px-5 hover:bg-slate-50 ${grouped ? "py-0.5" : "pt-2 pb-0.5"}`}>
              <div className="w-9 shrink-0">
                {grouped ? (
                  <span className="hidden pt-1 text-[10px] text-slate-400 group-hover:block">{formatTime(m.createdAt)}</span>
                ) : (
                  <Avatar author={m.author} />
                )}
              </div>
              <div className="min-w-0 flex-1">
                {!grouped && (
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-slate-900">{author.name}</span>
                    {m.author !== "user" && (
                      <span className="rounded bg-slate-100 px-1 text-[10px] font-semibold tracking-wide text-slate-500 uppercase">
                        Agent
                      </span>
                    )}
                    <span className="text-xs text-slate-500">{formatTime(m.createdAt)}</span>
                    {m.automationId && <Zap size={12} className="text-orange-500" aria-label="Automation" />}
                  </div>
                )}
                <Markdown text={m.text} />
                {m.attachments?.map((f) => <AttachmentCard key={f.id} file={f} />)}
                {urls.map((u) => <LinkPreview key={u} url={u} />)}
                {m.runId && m.author === "exi" && (
                  <button
                    onClick={() => onSelectRun(m.runId!)}
                    className="mt-1 text-xs font-medium text-violet-700 opacity-0 group-hover:opacity-100 hover:underline"
                  >
                    View agent activity →
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
      {activeRun && (activeRun.status === "planning" || activeRun.status === "running") && <TypingIndicator run={activeRun} />}
      <div ref={bottom} />
    </div>
  );
}
