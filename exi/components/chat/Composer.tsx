"use client";

import { useRef, useState } from "react";
import { AtSign, Bold, Code, Italic, Loader2, Paperclip, SendHorizontal, X } from "lucide-react";
import { formatBytes } from "@/lib/ids";
import type { Attachment } from "@/lib/types";

interface Pending {
  key: string;
  name: string;
  size: number;
  file?: Attachment;
  error?: string;
}

async function upload(file: File): Promise<Attachment> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/files", { method: "POST", body: form, credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? `Upload failed (${res.status})`);
  return data.file as Attachment;
}

export function Composer({
  placeholder,
  disabled,
  onSend,
}: {
  placeholder: string;
  disabled?: boolean;
  onSend: (text: string, attachmentIds: string[]) => Promise<void>;
}) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<Pending[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const area = useRef<HTMLTextAreaElement>(null);

  const uploading = files.some((f) => !f.file && !f.error);
  const ready = files.filter((f) => f.file).map((f) => f.file!.id);
  const canSend = !disabled && !sending && !uploading && (text.trim().length > 0 || ready.length > 0);

  const send = async () => {
    if (!canSend) return;
    setSending(true);
    setError(null);
    try {
      await onSend(text.trim(), ready);
      setText("");
      setFiles([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't send");
    } finally {
      setSending(false);
      area.current?.focus();
    }
  };

  const wrap = (before: string, after = before) => {
    const el = area.current;
    if (!el) return;
    const { selectionStart: s, selectionEnd: e } = el;
    setText(text.slice(0, s) + before + text.slice(s, e) + after + text.slice(e));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(s + before.length, e + before.length);
    });
  };

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    for (const f of Array.from(list).slice(0, 5 - files.length)) {
      const key = `${f.name}-${f.size}-${Math.random()}`;
      setFiles((cur) => [...cur, { key, name: f.name, size: f.size }]);
      upload(f)
        .then((file) => setFiles((cur) => cur.map((p) => (p.key === key ? { ...p, file } : p))))
        .catch((err: Error) => setFiles((cur) => cur.map((p) => (p.key === key ? { ...p, error: err.message } : p))));
    }
  };

  return (
    <div className="px-5 pb-5">
      <div className="rounded-xl border border-slate-300 bg-white shadow-sm focus-within:border-slate-400">
        <div className="flex items-center gap-1 border-b border-slate-100 px-2 py-1 text-slate-500">
          <button className="rounded p-1.5 hover:bg-slate-100" onClick={() => wrap("**")} aria-label="Bold"><Bold size={15} /></button>
          <button className="rounded p-1.5 hover:bg-slate-100" onClick={() => wrap("_")} aria-label="Italic"><Italic size={15} /></button>
          <button className="rounded p-1.5 hover:bg-slate-100" onClick={() => wrap("`")} aria-label="Code"><Code size={15} /></button>
          <button className="rounded p-1.5 hover:bg-slate-100" onClick={() => wrap("@Exi ", "")} aria-label="Mention Exi"><AtSign size={15} /></button>
        </div>
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 px-3 pt-2">
            {files.map((f) => (
              <span
                key={f.key}
                className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs ${f.error ? "bg-red-50 text-red-700" : "bg-slate-100"}`}
                title={f.error}
              >
                {!f.file && !f.error && <Loader2 size={12} className="animate-spin" />}
                {f.name} <span className="text-slate-500">{f.error ? "failed" : formatBytes(f.size)}</span>
                <button onClick={() => setFiles((cur) => cur.filter((x) => x.key !== f.key))} aria-label={`Remove ${f.name}`}>
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <textarea
          ref={area}
          rows={2}
          value={text}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              void send();
            }
          }}
          className="block max-h-48 min-h-[3rem] w-full resize-none bg-transparent px-3 py-2 text-[15px] outline-none"
        />
        <div className="flex items-center justify-between px-2 pb-2">
          <button
            className="rounded p-1.5 text-slate-500 hover:bg-slate-100"
            onClick={() => fileInput.current?.click()}
            aria-label="Attach files"
          >
            <Paperclip size={16} />
          </button>
          <input
            ref={fileInput}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <div className="flex items-center gap-3">
            {error ? (
              <span className="text-xs text-red-600">{error}</span>
            ) : (
              <span className="hidden text-[11px] text-slate-400 sm:inline">Enter to send · Shift+Enter for newline</span>
            )}
            <button
              onClick={() => void send()}
              disabled={!canSend}
              aria-label="Send"
              className="flex items-center gap-1 rounded-md bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white disabled:bg-slate-200 disabled:text-slate-400"
            >
              {sending ? <Loader2 size={15} className="animate-spin" /> : <SendHorizontal size={15} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
