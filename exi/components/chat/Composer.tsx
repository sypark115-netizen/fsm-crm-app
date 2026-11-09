"use client";

import { useRef, useState } from "react";
import { AtSign, Bold, Code, Italic, Paperclip, SendHorizontal, X } from "lucide-react";
import { formatBytes, uid } from "@/lib/ids";
import type { Attachment } from "@/lib/types";

const INLINE_IMAGE_LIMIT = 200 * 1024;

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

export function Composer({
  placeholder,
  disabled,
  onSend,
}: {
  placeholder: string;
  disabled?: boolean;
  onSend: (text: string, attachments: Attachment[]) => void;
}) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<Attachment[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);
  const area = useRef<HTMLTextAreaElement>(null);

  const send = () => {
    const t = text.trim();
    if ((!t && files.length === 0) || disabled) return;
    onSend(t, files);
    setText("");
    setFiles([]);
    area.current?.focus();
  };

  const wrap = (before: string, after = before) => {
    const el = area.current;
    if (!el) return;
    const { selectionStart: s, selectionEnd: e } = el;
    const next = text.slice(0, s) + before + text.slice(s, e) + after + text.slice(e);
    setText(next);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(s + before.length, e + before.length);
    });
  };

  const addFiles = async (list: FileList | null) => {
    if (!list) return;
    const next: Attachment[] = [];
    for (const f of Array.from(list).slice(0, 5)) {
      const dataUrl = f.type.startsWith("image/") && f.size <= INLINE_IMAGE_LIMIT ? await readAsDataUrl(f) : undefined;
      next.push({ id: uid("file"), name: f.name, size: f.size, mime: f.type, dataUrl });
    }
    setFiles((cur) => [...cur, ...next]);
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
              <span key={f.id} className="flex items-center gap-1.5 rounded-md bg-slate-100 px-2 py-1 text-xs">
                {f.name} <span className="text-slate-500">{formatBytes(f.size)}</span>
                <button onClick={() => setFiles((cur) => cur.filter((x) => x.id !== f.id))} aria-label={`Remove ${f.name}`}>
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
              send();
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
              void addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <div className="flex items-center gap-3">
            <span className="hidden text-[11px] text-slate-400 sm:inline">Enter to send · Shift+Enter for newline</span>
            <button
              onClick={send}
              disabled={disabled || (!text.trim() && files.length === 0)}
              className="flex items-center gap-1 rounded-md bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white disabled:bg-slate-200 disabled:text-slate-400"
            >
              <SendHorizontal size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
