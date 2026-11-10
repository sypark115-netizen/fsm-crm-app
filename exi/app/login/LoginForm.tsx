"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/client/api";

export function LoginForm({ firstUser, signupOpen }: { firstUser: boolean; signupOpen: boolean }) {
  const [mode, setMode] = useState<"login" | "signup">(firstUser ? "signup" : "login");
  const [form, setForm] = useState({ username: "", displayName: "", password: "", inviteCode: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await api("/api/auth/login", { body: { username: form.username, password: form.password } });
      } else {
        await api("/api/auth/signup", {
          body: {
            username: form.username,
            displayName: form.displayName || form.username,
            password: form.password,
            inviteCode: form.inviteCode || undefined,
          },
        });
      }
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center bg-rail p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white">
            <Sparkles size={20} />
          </span>
          <div>
            <h1 className="text-lg font-bold">Exi Workspace</h1>
            <p className="text-xs text-slate-500">Your team, plus a team of AI agents</p>
          </div>
        </div>

        {firstUser && (
          <p className="rounded-md bg-violet-50 p-2 text-xs text-violet-800">
            No accounts yet — create the first one. You&apos;ll be the workspace owner.
          </p>
        )}

        {!firstUser && (
          <div className="flex rounded-lg bg-slate-100 p-1 text-sm">
            {(["login", "signup"] as const).map((m) => (
              <button
                type="button"
                key={m}
                onClick={() => setMode(m)}
                disabled={m === "signup" && !signupOpen}
                className={`flex-1 rounded-md py-1.5 disabled:opacity-40 ${mode === m ? "bg-white font-semibold shadow-sm" : "text-slate-600"}`}
              >
                {m === "login" ? "Sign in" : "Join with invite"}
              </button>
            ))}
          </div>
        )}

        <label className="block">
          <span className="mb-1 block text-xs font-semibold text-slate-600">Username</span>
          <input className="input" autoComplete="username" required value={form.username} onChange={set("username")} />
        </label>
        {mode === "signup" && (
          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-slate-600">Display name</span>
            <input className="input" autoComplete="name" value={form.displayName} onChange={set("displayName")} placeholder="Shown to your team" />
          </label>
        )}
        <label className="block">
          <span className="mb-1 block text-xs font-semibold text-slate-600">Password</span>
          <input
            className="input"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "signup" ? 8 : 1}
            value={form.password}
            onChange={set("password")}
          />
        </label>
        {mode === "signup" && !firstUser && (
          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-slate-600">Invite code</span>
            <input className="input" required value={form.inviteCode} onChange={set("inviteCode")} />
          </label>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-violet-600 py-2 font-semibold text-white disabled:opacity-60"
        >
          {busy && <Loader2 size={16} className="animate-spin" />}
          {mode === "login" ? "Sign in" : firstUser ? "Create workspace" : "Join workspace"}
        </button>
      </form>
    </div>
  );
}
