"use client";

import { useState } from "react";
import { ChevronDown, Hash, Plus, Sparkles, Zap, X } from "lucide-react";
import { Avatar } from "@/components/agents/Avatar";
import type { Channel, WorkspaceState } from "@/lib/types";

interface Props {
  state: WorkspaceState;
  busyChannels: Set<string>;
  onSelect: (channelId: string) => void;
  onCreateChannel: (name: string) => void;
  onOpenMaki: () => void;
  onClose?: () => void;
}

function Section({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="mt-4">
      <div className="group flex items-center justify-between px-3 text-[13px] text-rail-text/80">
        <button className="flex items-center gap-1 hover:text-white" onClick={() => setOpen((o) => !o)}>
          <ChevronDown size={14} className={`transition-transform ${open ? "" : "-rotate-90"}`} />
          {title}
        </button>
        {action}
      </div>
      {open && <ul className="mt-1 space-y-px">{children}</ul>}
    </div>
  );
}

export function Sidebar({ state, busyChannels, onSelect, onCreateChannel, onOpenMaki, onClose }: Props) {
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState("");
  const channels = state.channels.filter((c) => c.kind === "channel");
  const dms = state.channels.filter((c) => c.kind === "dm");
  const activeAutomations = state.automations.filter((a) => a.enabled).length;

  const item = (c: Channel) => {
    const active = c.id === state.activeChannelId;
    const busy = busyChannels.has(c.id);
    return (
      <li key={c.id}>
        <button
          onClick={() => onSelect(c.id)}
          className={`mx-2 flex w-[calc(100%-1rem)] items-center gap-2 rounded-md px-2 py-1 text-left text-[15px] ${
            active ? "bg-rail-active text-white" : "text-rail-text hover:bg-rail-hover"
          }`}
        >
          {c.kind === "dm" && c.peer ? <Avatar author={c.peer} size="sm" pulse /> : <Hash size={16} className="opacity-70" />}
          <span className="truncate">{c.name}</span>
          {busy && <span className="ml-auto h-2 w-2 animate-pulse rounded-full bg-amber-400" title="Agents working" />}
        </button>
      </li>
    );
  };

  const submit = () => {
    const name = draft.trim().toLowerCase().replace(/[^a-z0-9가-힣-_]+/g, "-").replace(/^-+|-+$/g, "");
    if (name) onCreateChannel(name);
    setDraft("");
    setCreating(false);
  };

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col bg-rail text-rail-text">
      <div className="flex h-12 items-center gap-2 border-b border-white/10 px-4">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white">
          <Sparkles size={16} />
        </span>
        <div className="leading-tight">
          <div className="font-bold text-white">Exi Workspace</div>
          <div className="text-[11px] text-rail-text/70">v{state.appVersion} · Agent Organization</div>
        </div>
        {onClose && (
          <button className="ml-auto md:hidden" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto pb-24">
        <button
          onClick={onOpenMaki}
          className="mx-2 mt-3 flex w-[calc(100%-1rem)] items-center gap-2 rounded-md px-2 py-1.5 text-[15px] hover:bg-rail-hover"
        >
          <Zap size={16} className="text-orange-400" />
          Automations
          <span className="ml-auto rounded bg-white/10 px-1.5 text-xs">{activeAutomations}</span>
        </button>

        <Section
          title="Channels"
          action={
            <button className="opacity-0 group-hover:opacity-100 hover:text-white" onClick={() => setCreating(true)} aria-label="New channel">
              <Plus size={15} />
            </button>
          }
        >
          {channels.map(item)}
          {creating ? (
            <li className="mx-2 px-2 py-1">
              <input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submit();
                  if (e.key === "Escape") setCreating(false);
                }}
                onBlur={submit}
                placeholder="new-channel"
                className="w-full rounded bg-white/10 px-2 py-1 text-sm text-white outline-none placeholder:text-rail-text/50"
              />
            </li>
          ) : (
            <li>
              <button
                onClick={() => setCreating(true)}
                className="mx-2 flex w-[calc(100%-1rem)] items-center gap-2 rounded-md px-2 py-1 text-[15px] hover:bg-rail-hover"
              >
                <Plus size={16} className="opacity-70" /> Add channel
              </button>
            </li>
          )}
        </Section>

        <Section title="Direct messages">{dms.map(item)}</Section>
      </nav>
    </aside>
  );
}
