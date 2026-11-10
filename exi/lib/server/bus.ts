import { EventEmitter } from "node:events";
import type { WorkspaceEvent } from "../types";

/**
 * In-process pub/sub that fans workspace events out to every open SSE stream.
 * `audience` restricts an event to one user (their private DMs).
 * Multi-instance deployments would swap this for Redis pub/sub.
 */
export interface Envelope {
  event: WorkspaceEvent;
  audience?: string;
}

const g = globalThis as unknown as { __exiBus?: EventEmitter };
const bus = g.__exiBus ?? (g.__exiBus = new EventEmitter().setMaxListeners(0));

export function publish(event: WorkspaceEvent, audience?: string) {
  bus.emit("event", { event, audience } satisfies Envelope);
}

export function subscribe(fn: (e: Envelope) => void): () => void {
  bus.on("event", fn);
  return () => bus.off("event", fn);
}
