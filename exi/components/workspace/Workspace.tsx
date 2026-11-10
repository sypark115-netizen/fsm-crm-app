"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, Hash, Loader2, Menu, Zap } from "lucide-react";
import { AgentActivityPanel } from "@/components/agents/AgentActivityPanel";
import { Avatar } from "@/components/agents/Avatar";
import { Composer } from "@/components/chat/Composer";
import { MessageList } from "@/components/chat/MessageList";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { MakiModal, type NewAutomation } from "@/components/maki/MakiModal";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { AGENTS } from "@/lib/agents";
import { api } from "@/lib/client/api";
import { useWorkspace } from "@/lib/client/useWorkspace";
import type { Automation } from "@/lib/types";

export function Workspace() {
  const { state, select, connection, error, reload } = useWorkspace();
  const [panelOpen, setPanelOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [makiOpen, setMakiOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string>();
  const [actionError, setActionError] = useState<string | null>(null);

  // Activity panel open by default on wide screens only (it's an overlay on mobile).
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px)").matches) setPanelOpen(true);
  }, []);

  const channel = state.channels.find((c) => c.id === state.activeChannelId) ?? null;
  const messages = useMemo(
    () => (channel ? state.messages.filter((m) => m.channelId === channel.id) : []),
    [state.messages, channel],
  );
  const channelRuns = useMemo(
    () => (channel ? state.runs.filter((r) => r.channelId === channel.id) : []),
    [state.runs, channel],
  );
  const busyChannels = useMemo(
    () => new Set(state.runs.filter((r) => r.status === "planning" || r.status === "running").map((r) => r.channelId)),
    [state.runs],
  );
  const planningRun = channelRuns.findLast((r) => r.status === "planning");
  const shownRunId =
    selectedRunId && channelRuns.some((r) => r.id === selectedRunId) ? selectedRunId : channelRuns.at(-1)?.id;

  const run = async (fn: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  if (!state.me || !channel) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        {error ? (
          <div className="text-center">
            <p className="text-red-600">{error}</p>
            <button onClick={() => void reload()} className="mt-2 rounded-md border px-3 py-1 text-sm">
              Retry
            </button>
          </div>
        ) : (
          <Loader2 className="animate-spin" />
        )}
      </div>
    );
  }

  const selectChannel = (id: string) => {
    select(id);
    setSelectedRunId(undefined);
    setSidebarOpen(false);
  };

  const sidebarProps = {
    me: state.me,
    users: state.users,
    channels: state.channels,
    activeChannelId: state.activeChannelId,
    activeAutomations: state.automations.filter((a) => a.enabled).length,
    status: state.status,
    connection,
    busyChannels,
    onSelect: selectChannel,
    onCreateChannel: async (name: string) => {
      const { channel: created } = await api<{ channel: { id: string } }>("/api/channels", { body: { name } });
      selectChannel(created.id);
    },
    onOpenMaki: () => {
      setMakiOpen(true);
      setSidebarOpen(false);
    },
    onLogout: () =>
      void run(async () => {
        await api("/api/auth/logout", { body: {} });
        window.location.href = "/login";
      }),
  };

  const isMakiDm = channel.kind === "dm" && channel.peer === "maki";
  const placeholder = isMakiDm
    ? "Tell Maki what to run and when — e.g. every weekday at 9am summarize AI agent news"
    : channel.kind === "dm"
      ? `Message ${channel.name}`
      : `Message #${channel.name} — mention @Exi to delegate to the agents`;

  return (
    <div className="flex h-full">
      <div className="hidden md:block">
        <Sidebar {...sidebarProps} />
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <Sidebar {...sidebarProps} onClose={() => setSidebarOpen(false)} />
          <div className="flex-1 bg-black/40" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-slate-200 px-4">
          <button className="md:hidden" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
            <Menu size={18} />
          </button>
          {channel.kind === "dm" && channel.peer ? <Avatar author={channel.peer} size="sm" /> : <Hash size={18} className="text-slate-500" />}
          <h1 className="font-bold">{channel.name}</h1>
          <span className="hidden truncate text-sm text-slate-500 sm:inline">
            {channel.topic ? `· ${channel.topic}` : channel.peer ? `· ${AGENTS[channel.peer].role}` : ""}
          </span>
          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={() => setMakiOpen(true)}
              className="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-slate-700 hover:bg-slate-100"
            >
              <Zap size={15} className="text-orange-500" /> <span className="hidden sm:inline">Automations</span>
            </button>
            <button
              onClick={() => setPanelOpen((o) => !o)}
              className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-sm hover:bg-slate-100 ${panelOpen ? "text-violet-700" : "text-slate-700"}`}
              aria-pressed={panelOpen}
            >
              <Activity size={15} /> <span className="hidden sm:inline">Activity</span>
            </button>
          </div>
        </header>

        {state.status?.planner === "mock" && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-xs text-amber-800">
            Demo mode — agents return canned output. Set <code>ANTHROPIC_API_KEY</code> on the server for real work.
          </div>
        )}
        {actionError && (
          <div className="border-b border-red-200 bg-red-50 px-4 py-1.5 text-xs text-red-700">{actionError}</div>
        )}

        <MessageList
          messages={messages}
          users={state.users}
          planningRun={planningRun}
          onSelectRun={(id) => {
            setSelectedRunId(id);
            setPanelOpen(true);
          }}
        />

        <Composer
          placeholder={placeholder}
          disabled={connection === "connecting"}
          onSend={async (text, attachmentIds) => {
            await api("/api/messages", { body: { channelId: channel.id, text, attachmentIds } });
          }}
        />
      </main>

      {panelOpen && (
        <div className="fixed inset-0 z-30 bg-white lg:static lg:z-auto">
          <AgentActivityPanel
            runs={channelRuns}
            selectedRunId={shownRunId}
            onSelectRun={setSelectedRunId}
            onClose={() => setPanelOpen(false)}
          />
        </div>
      )}

      {makiOpen && (
        <MakiModal
          channels={state.channels}
          automations={state.automations}
          defaultChannelId={channel.id}
          onClose={() => setMakiOpen(false)}
          onCreate={async (a: NewAutomation) => {
            await api("/api/automations", { body: a });
          }}
          onToggle={(id, enabled) => void run(() => api(`/api/automations/${id}`, { method: "PATCH", body: { enabled } }))}
          onDelete={(id) => void run(() => api(`/api/automations/${id}`, { method: "DELETE" }))}
          onRunNow={(a: Automation) =>
            void run(async () => {
              await api(`/api/automations/${a.id}/run`, { body: {} });
              setMakiOpen(false);
              selectChannel(a.channelId);
            })
          }
        />
      )}

      <FeedbackWidget items={state.feedback} users={state.users} githubEnabled={!!state.status?.github} />
    </div>
  );
}
