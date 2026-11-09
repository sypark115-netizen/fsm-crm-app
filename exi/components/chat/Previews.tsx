import { FileText, Globe, ImageIcon } from "lucide-react";
import { formatBytes } from "@/lib/ids";
import type { Attachment } from "@/lib/types";

const URL_RE = /https?:\/\/[^\s<>()]+[^\s<>().,!?;:'"]/g;

export function extractUrls(text: string): string[] {
  return Array.from(new Set(text.match(URL_RE) ?? [])).slice(0, 3);
}

const KNOWN: Record<string, { name: string; tint: string }> = {
  "figma.com": { name: "Figma", tint: "bg-fuchsia-500" },
  "github.com": { name: "GitHub", tint: "bg-slate-800" },
  "notion.so": { name: "Notion", tint: "bg-neutral-700" },
  "docs.google.com": { name: "Google Docs", tint: "bg-blue-500" },
  "youtube.com": { name: "YouTube", tint: "bg-red-600" },
  "linear.app": { name: "Linear", tint: "bg-indigo-600" },
};

/** Client-side unfurl. A production build would fetch OpenGraph tags server-side. */
export function LinkPreview({ url }: { url: string }) {
  let host = url;
  let path = "";
  try {
    const u = new URL(url);
    host = u.hostname.replace(/^www\./, "");
    path = decodeURIComponent(u.pathname).replace(/[/_-]+/g, " ").trim();
  } catch {
    /* keep raw */
  }
  const known = Object.entries(KNOWN).find(([d]) => host.endsWith(d))?.[1];
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer noopener"
      className="mt-2 flex max-w-md gap-3 rounded-lg border border-l-4 border-slate-200 border-l-violet-400 bg-white p-3 hover:bg-slate-50"
    >
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-white ${known?.tint ?? "bg-slate-400"}`}>
        <Globe size={18} />
      </span>
      <span className="min-w-0">
        <span className="block text-xs font-semibold text-slate-500">{known?.name ?? host}</span>
        <span className="block truncate text-sm font-medium text-[#1264a3] capitalize">{path || host}</span>
        <span className="block truncate text-xs text-slate-500">{url}</span>
      </span>
    </a>
  );
}

export function AttachmentCard({ file }: { file: Attachment }) {
  if (file.dataUrl && file.mime.startsWith("image/")) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- local data URL preview
      <img src={file.dataUrl} alt={file.name} className="mt-2 max-h-60 max-w-xs rounded-lg border border-slate-200 object-cover" />
    );
  }
  const Icon = file.mime.startsWith("image/") ? ImageIcon : FileText;
  return (
    <div className="mt-2 flex w-72 items-center gap-3 rounded-lg border border-slate-200 bg-white p-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-violet-100 text-violet-700">
        <Icon size={18} />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium">{file.name}</span>
        <span className="block text-xs text-slate-500">
          {formatBytes(file.size)} · {file.mime || "file"}
        </span>
      </span>
    </div>
  );
}
