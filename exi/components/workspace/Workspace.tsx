"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, Hash, Menu, RotateCcw, Zap } from "lucide-react";
import { AgentActivityPanel } from "@/components/agents/AgentActivityPanel";
import { Avatar } from "@/components/agents/Avatar";
import { Composer } from "@/components/chat/Composer";
import { MessageList } from "@/components/chat/MessageList";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { MakiModal } from "@/components/maki/MakiModal";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { AGENTS } from "@/lib/agents";
import { uid } from "@/lib/ids";
import { useOrchestrator } from "@/lib/orchestrator/useOrchestrator";
import { useWorkspace } from "@/lib/store";
import type { Attachment } from "@/lib/types";

export function Workspace() {
  const { state, dispatch, stateRef, hydrated } = useWorkspace();
  const { startRun, runAutomation, onUserMessage } = useOrchestrator(stateRef, dispatch, hydrated);

  const [panelOpen, setPanelOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [makiOpen, setMakiOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string>();

  // Show the activity panel by default on wide screens only (it's an overlay on mobile).
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px)").matches) setPanelOpen(true);
  }, []);

  const channel = state.channels.find((c) => c.id === state.activeChannelId) ?? state.channels[0];
  const messages = useMemo(
    () => state.messages.filter((m) => m.channelId === channel.id),
    [state.messages, channel.id],
  );
  const channelRuns = useMemo(() => state.runs.filter((r) => r.channelId === channel.id), [state.runs, channel.id]);
  const activeRun = [...channelRuns].reverse().find((r) => r.status === "planning" || r.status === "running");
  const busyChannels = useMemo(
    () => new Set(state.runs.filter((r) => r.status === "planning" || r.status === "running").map((r) => r.channelId)),
    [state.runs],
  );
  // Default the panel to the newest run in this channel.
  const shownRunId = selectedRunId && channelRuns.some((r) => r.id === selectedRunId)
    ? selectedRunId
    : channelRuns.at(-1)?.id;

  // Exi answers every message in channels and in its own DM; other DMs are with
  // a specialist, who still routes through Exi so the orchestration stays visible.
  const handleSend = (text: string, attachments: Attachment[]) => {
    dispatch({
      type: "addMessage",
      message: {
        id: uid("m"),
        channelId: channel.id,
        author: "user",
        text,
        createdAt: Date.now(),
        attachments: attachments.length ? attachments : undefined,
      },
    });
    if (onUserMessage(channel.id, text)) return; // a Maki rule already handed this to Exi
    const command = text || `Review the attached file(s): ${attachments.map((a) => a.name).join(", ")}`;
    const peerHint = channel.kind === "dm" && channel.peer && channel.peer !== "exi" ? ` (asked directly to ${AGENTS[channel.peer].name})` : "";
    void startRun(channel.id, command + peerHint);
    setPanelOpen((open) => open || window.innerWidth >= 1024);
  };

  const selectChannel = (id: string) => {
    dispatch({ type: "setActiveChannel", channelId: id });
    setSelectedRunId(undefined);
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-full">
      {/* Sidebar: static on md+, drawer on mobile */}
      <div className="hidden md:block">
        <Sidebar
          state={state}
          busyChannels={busyChannels}
          onSelect={selectChannel}
          onCreateChannel={(name) => dispatch({ type: "addChannel", channel: { id: uid("ch"), name, kind: "channel" } })}
          onOpenMaki={() => setMakiOpen(true)}
        />
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <Sidebar
            state={state}
            busyChannels={busyChannels}
            onSelect={selectChannel}
            onCreateChannel={(name) => dispatch({ type: "addChannel", channel: { id: uid("ch"), name, kind: "channel" } })}
            onOpenMaki={() => {
              setMakiOpen(true);
              setSidebarOpen(false);
            }}
            onClose={() => setSidebarOpen(false)}
          />
          <div className="flex-1 bg-black/40" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Chat */}
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-slate-200 px-4">
          <button className="md:hidden" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
            <Menu size={18} />
          </button>
          {channel.kind === "dm" && channel.peer ? <Avatar author={channel.peer} size="sm" /> : <Hash size={18} className="text-slate-500" />}
          <h1 className="font-bold">{channel.name}</h1>
          {channel.topic && <span className="hidden truncate text-sm text-slate-500 sm:inline">· {channel.topic}</span>}
          {channel.kind === "dm" && channel.peer && (
            <span className="hidden text-sm text-slate-500 sm:inline">· {AGENTS[channel.peer].role}</span>
          )}
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
            <button
              onClick={() => {
                if (window.confirm("Reset the workspace to demo data? This clears local messages and automations.")) {
                  dispatch({ type: "reset" });
                }
              }}
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
              title="Reset demo data"
              aria-label="Reset demo data"
            >
              <RotateCcw size={15} />
            </button>
          </div>
        </header>

        {hydrated ? (
          <MessageList
            messages={messages}
            activeRun={activeRun}
            onSelectRun={(id) => {
              setSelectedRunId(id);
              setPanelOpen(true);
            }}
          />
        ) : (
          <div className="flex-1" />
        )}

        <Composer
          disabled={!hydrated}
          placeholder={
            channel.kind === "dm" ? `Message ${channel.name}` : `Message #${channel.name} — Exi will coordinate the agents`
          }
          onSend={handleSend}
        />
      </main>

      {/* Agent activity: side panel on lg+, overlay below */}
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
          onCreate={(automation) => dispatch({ type: "addAutomation", automation })}
          onToggle={(id, enabled) => dispatch({ type: "patchAutomation", id, patch: { enabled } })}
          onDelete={(id) => dispatch({ type: "removeAutomation", id })}
          onRunNow={(a) => {
            runAutomation(a, "manual run");
            setMakiOpen(false);
            selectChannel(a.channelId);
          }}
        />
      )}

      <FeedbackWidget items={state.feedback} appVersion={state.appVersion} dispatch={dispatch} />
    </div>
  );
}
