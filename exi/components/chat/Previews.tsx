import { Download, FileText, Globe } from "lucide-react";
import { formatBytes } from "@/lib/ids";
import type { Attachment } from "@/lib/types";

const URL_RE = /https?:\/\/[^\s<>()\[\]]+[^\s<>()\[\].,!?;:'"]/g;

export function extractUrls(text: string): string[] {
  return Array.from(new Set(text.match(URL_RE) ?? [])).slice(0, 2);
}

const KNOWN: Record<string, { name: string; tint: string }> = {
  "figma.com": { name: "Figma", tint: "bg-fuchsia-500" },
  "github.com": { name: "GitHub", tint: "bg-slate-800" },
  "notion.so": { name: "Notion", tint: "bg-neutral-700" },
  "docs.google.com": { name: "Google Docs", tint: "bg-blue-500" },
  "youtube.com": { name: "YouTube", tint: "bg-red-600" },
  "linear.app": { name: "Linear", tint: "bg-indigo-600" },
};

/**
 * Link card built from the URL itself. We deliberately don't fetch remote pages
 * server-side (SSRF risk); add an allow-listed unfurler if you need OG data.
 */
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
  if (/^image\/(png|jpeg|gif|webp)$/.test(file.mime)) {
    return (
      <a href={file.url} target="_blank" rel="noreferrer" className="mt-2 block w-fit">
        {/* eslint-disable-next-line @next/next/no-img-element -- authenticated upload, not optimisable */}
        <img src={file.url} alt={file.name} className="max-h-64 max-w-xs rounded-lg border border-slate-200 object-cover" />
      </a>
    );
  }
  return (
    <a
      href={file.url}
      className="mt-2 flex w-72 items-center gap-3 rounded-lg border border-slate-200 bg-white p-2.5 hover:bg-slate-50"
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-violet-100 text-violet-700">
        <FileText size={18} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{file.name}</span>
        <span className="block text-xs text-slate-500">
          {formatBytes(file.size)} · {file.mime || "file"}
        </span>
      </span>
      <Download size={16} className="text-slate-400" />
    </a>
  );
}
