"use client";

import { useEffect, useReducer, useRef, useState } from "react";
import { createSeedState } from "./seed";
import type {
  AgentRun,
  Automation,
  Channel,
  FeedbackItem,
  FeedbackLogEntry,
  Message,
  RunStep,
  WorkspaceState,
} from "./types";

const STORAGE_KEY = "exi.workspace.v1";
const MAX_MESSAGES = 1000;
const MAX_RUNS = 100;

export type Action =
  | { type: "hydrate"; state: WorkspaceState }
  | { type: "reset" }
  | { type: "setActiveChannel"; channelId: string }
  | { type: "addChannel"; channel: Channel }
  | { type: "addMessage"; message: Message }
  | { type: "upsertRun"; run: AgentRun }
  | { type: "patchRun"; runId: string; patch: Partial<AgentRun> }
  | { type: "patchStep"; runId: string; stepId: string; patch: Partial<RunStep> }
  | { type: "addAutomation"; automation: Automation }
  | { type: "patchAutomation"; id: string; patch: Partial<Automation> }
  | { type: "removeAutomation"; id: string }
  | { type: "addFeedback"; item: FeedbackItem }
  | { type: "appendFeedbackLog"; id: string; entry: FeedbackLogEntry; patch?: Partial<FeedbackItem> }
  | { type: "setVersion"; version: string };

export function reducer(state: WorkspaceState, action: Action): WorkspaceState {
  switch (action.type) {
    case "hydrate":
      return action.state;
    case "reset":
      return createSeedState();
    case "setActiveChannel":
      return { ...state, activeChannelId: action.channelId };
    case "addChannel":
      return { ...state, channels: [...state.channels, action.channel], activeChannelId: action.channel.id };
    case "addMessage":
      return { ...state, messages: [...state.messages, action.message].slice(-MAX_MESSAGES) };
    case "upsertRun": {
      const others = state.runs.filter((r) => r.id !== action.run.id);
      return { ...state, runs: [...others, action.run].slice(-MAX_RUNS) };
    }
    case "patchRun":
      return {
        ...state,
        runs: state.runs.map((r) => (r.id === action.runId ? { ...r, ...action.patch } : r)),
      };
    case "patchStep":
      return {
        ...state,
        runs: state.runs.map((r) =>
          r.id !== action.runId
            ? r
            : { ...r, steps: r.steps.map((s) => (s.id === action.stepId ? { ...s, ...action.patch } : s)) },
        ),
      };
    case "addAutomation":
      return { ...state, automations: [...state.automations, action.automation] };
    case "patchAutomation":
      return {
        ...state,
        automations: state.automations.map((a) => (a.id === action.id ? { ...a, ...action.patch } : a)),
      };
    case "removeAutomation":
      return { ...state, automations: state.automations.filter((a) => a.id !== action.id) };
    case "addFeedback":
      return { ...state, feedback: [action.item, ...state.feedback] };
    case "appendFeedbackLog":
      return {
        ...state,
        feedback: state.feedback.map((f) =>
          f.id === action.id ? { ...f, ...action.patch, log: [...f.log, action.entry] } : f,
        ),
      };
    case "setVersion":
      return { ...state, appVersion: action.version };
  }
}

function load(): WorkspaceState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WorkspaceState;
    if (!Array.isArray(parsed.channels) || !Array.isArray(parsed.messages)) return null;
    // Runs interrupted by a reload can't resume — mark them failed.
    parsed.runs = (parsed.runs ?? []).map((r) =>
      r.status === "planning" || r.status === "running"
        ? { ...r, status: "failed", error: "Interrupted by page reload" }
        : r,
    );
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Workspace state with localStorage persistence. The first render uses the seed
 * (so server and client markup match), then hydrates from storage after mount.
 */
export function useWorkspace() {
  const [state, dispatch] = useReducer(reducer, undefined, () => createSeedState(0));
  const [hydrated, setHydrated] = useState(false);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    dispatch({ type: "hydrate", state: load() ?? createSeedState() });
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const t = window.setTimeout(() => {
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch {
        /* storage full or blocked — the app keeps working in memory */
      }
    }, 250);
    return () => window.clearTimeout(t);
  }, [state, hydrated]);

  return { state, dispatch, stateRef, hydrated };
}

export type Dispatch = (action: Action) => void;
