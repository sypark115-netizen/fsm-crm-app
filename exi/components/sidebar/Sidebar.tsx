"use client";

import { useState } from "react";
import { ChevronDown, Hash, LogOut, Plus, Sparkles, X, Zap } from "lucide-react";
import { Avatar } from "@/components/agents/Avatar";
import type { ConnectionState } from "@/lib/client/useWorkspace";
import type { Channel, ServerStatus, User } from "@/lib/types";

interface Props {
  me: User;
  users: Record<string, User>;
  channels: Channel[];
  activeChannelId: string | null;
  activeAutomations: number;
  status: ServerStatus | null;
  connection: ConnectionState;
  busyChannels: Set<string>;
  onSelect: (channelId: string) => void;
  onCreateChannel: (name: string) => Promise<void>;
  onOpenMaki: () => void;
  onLogout: () => void;
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

export function Sidebar(props: Props) {
  const { me, users, channels, activeChannelId, busyChannels, onSelect, onOpenMaki, onClose } = props;
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const item = (c: Channel) => {
    const active = c.id === activeChannelId;
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
          {busyChannels.has(c.id) && <span className="ml-auto h-2 w-2 animate-pulse rounded-full bg-amber-400" title="Agents working" />}
        </button>
      </li>
    );
  };

  const submit = async () => {
    const name = draft.trim().toLowerCase().replace(/\s+/g, "-");
    if (!name) {
      setCreating(false);
      return;
    }
    try {
      await props.onCreateChannel(name);
      setDraft("");
      setCreating(false);
      setCreateError(null);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Couldn't create channel");
    }
  };

  const mode = props.status?.planner === "claude" ? "Claude" : "Demo mode";

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col bg-rail text-rail-text">
      <div className="flex h-12 items-center gap-2 border-b border-white/10 px-4">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white">
          <Sparkles size={16} />
        </span>
        <div className="leading-tight">
          <div className="font-bold text-white">Exi Workspace</div>
          <div className="flex items-center gap-1 text-[11px] text-rail-text/70">
            <span
              className={`h-1.5 w-1.5 rounded-full ${props.connection === "live" ? "bg-emerald-400" : "bg-amber-400"}`}
              title={props.connection}
            />
            {props.connection === "live" ? mode : "Reconnecting…"}
          </div>
        </div>
        {onClose && (
          <button className="ml-auto md:hidden" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto pb-6">
        <button
          onClick={onOpenMaki}
          className="mx-2 mt-3 flex w-[calc(100%-1rem)] items-center gap-2 rounded-md px-2 py-1.5 text-[15px] hover:bg-rail-hover"
        >
          <Zap size={16} className="text-orange-400" />
          Automations
          <span className="ml-auto rounded bg-white/10 px-1.5 text-xs">{props.activeAutomations}</span>
        </button>

        <Section
          title="Channels"
          action={
            <button className="opacity-0 group-hover:opacity-100 hover:text-white" onClick={() => setCreating(true)} aria-label="New channel">
              <Plus size={15} />
            </button>
          }
        >
          {channels.filter((c) => c.kind === "channel").map(item)}
          {creating ? (
            <li className="mx-2 px-2 py-1">
              <input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void submit();
                  if (e.key === "Escape") setCreating(false);
                }}
                placeholder="new-channel"
                className="w-full rounded bg-white/10 px-2 py-1 text-sm text-white outline-none placeholder:text-rail-text/50"
              />
              {createError && <p className="mt-1 text-[11px] text-red-300">{createError}</p>}
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

        <Section title="Direct messages">{channels.filter((c) => c.kind === "dm").map(item)}</Section>
      </nav>

      <div className="flex items-center gap-2 border-t border-white/10 px-3 py-2 pb-16">
        <Avatar author={me.id} users={users} size="sm" />
        <div className="min-w-0 flex-1 leading-tight">
          <div className="truncate text-sm font-semibold text-white">{me.displayName}</div>
          <div className="truncate text-[11px] text-rail-text/70">@{me.username}</div>
        </div>
        <button onClick={props.onLogout} className="rounded p-1.5 hover:bg-rail-hover" title="Sign out" aria-label="Sign out">
          <LogOut size={15} />
        </button>
      </div>
    </aside>
  );
}
