"use client";

import { useCallback, useEffect, useReducer, useState } from "react";
import type {
  AgentRun,
  Automation,
  Bootstrap,
  Channel,
  FeedbackItem,
  Message,
  ServerStatus,
  User,
  WorkspaceEvent,
} from "../types";
import { ApiError, api } from "./api";

export interface WorkspaceState {
  me: User | null;
  users: Record<string, User>;
  channels: Channel[];
  messages: Message[];
  runs: AgentRun[];
  automations: Automation[];
  feedback: FeedbackItem[];
  status: ServerStatus | null;
  activeChannelId: string | null;
}

type Action = { type: "hydrate"; data: Bootstrap } | { type: "event"; event: WorkspaceEvent } | { type: "select"; channelId: string };

const ACTIVE_KEY = "exi.activeChannel";

const initial: WorkspaceState = {
  me: null,
  users: {},
  channels: [],
  messages: [],
  runs: [],
  automations: [],
  feedback: [],
  status: null,
  activeChannelId: null,
};

function upsert<T extends { id: string }>(list: T[], item: T, sortKey?: keyof T): T[] {
  const i = list.findIndex((x) => x.id === item.id);
  if (i === -1) {
    const next = [...list, item];
    return sortKey ? next.sort((a, b) => Number(a[sortKey]) - Number(b[sortKey])) : next;
  }
  const next = list.slice();
  next[i] = item;
  return next;
}

function reducer(state: WorkspaceState, action: Action): WorkspaceState {
  switch (action.type) {
    case "hydrate": {
      const d = action.data;
      let saved: string | null = null;
      try {
        saved = window.localStorage.getItem(ACTIVE_KEY);
      } catch {
        /* storage unavailable */
      }
      const keep = [state.activeChannelId, saved].find((id) => id && d.channels.some((c) => c.id === id));
      return {
        me: d.me,
        users: Object.fromEntries(d.users.map((u) => [u.id, u])),
        channels: d.channels,
        messages: d.messages,
        runs: d.runs,
        automations: d.automations,
        feedback: d.feedback,
        status: d.status,
        activeChannelId: keep ?? d.channels.find((c) => c.kind === "channel")?.id ?? d.channels[0]?.id ?? null,
      };
    }
    case "select":
      try {
        window.localStorage.setItem(ACTIVE_KEY, action.channelId);
      } catch {
        /* storage unavailable */
      }
      return { ...state, activeChannelId: action.channelId };
    case "event": {
      const e = action.event;
      switch (e.type) {
        case "message.upsert":
          return { ...state, messages: upsert(state.messages, e.message, "createdAt") };
        case "run.upsert":
          return { ...state, runs: upsert(state.runs, e.run, "startedAt") };
        case "channel.create":
          return { ...state, channels: upsert(state.channels, e.channel) };
        case "automation.upsert":
          return { ...state, automations: upsert(state.automations, e.automation, "createdAt") };
        case "automation.delete":
          return { ...state, automations: state.automations.filter((a) => a.id !== e.id) };
        case "feedback.upsert": {
          const exists = state.feedback.some((f) => f.id === e.item.id);
          return {
            ...state,
            feedback: exists ? state.feedback.map((f) => (f.id === e.item.id ? e.item : f)) : [e.item, ...state.feedback],
          };
        }
        case "user.join":
          return { ...state, users: { ...state.users, [e.user.id]: e.user } };
      }
    }
  }
  return state;
}

export type ConnectionState = "connecting" | "live" | "reconnecting";

/** Server-backed workspace state: bootstrap snapshot + live SSE events. */
export function useWorkspace() {
  const [state, dispatch] = useReducer(reducer, initial);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      dispatch({ type: "hydrate", data: await api<Bootstrap>("/api/bootstrap") });
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        window.location.href = "/login";
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load workspace");
    }
  }, []);

  useEffect(() => {
    let es: EventSource | null = null;
    let dropped = false;
    // Subscribe first, then snapshot, so nothing between the two is lost
    // (upserts are idempotent, so overlap is harmless).
    es = new EventSource("/api/stream");
    es.onopen = () => {
      setConnection("live");
      if (dropped) void load(); // resync whatever we missed while offline
      dropped = false;
    };
    es.onerror = () => {
      dropped = true;
      setConnection("reconnecting");
    };
    es.onmessage = (msg) => {
      try {
        dispatch({ type: "event", event: JSON.parse(msg.data) as WorkspaceEvent });
      } catch {
        /* ignore malformed frames */
      }
    };
    void load();
    return () => es?.close();
  }, [load]);

  const select = useCallback((channelId: string) => dispatch({ type: "select", channelId }), []);
  return { state, select, connection, error, reload: load };
}
