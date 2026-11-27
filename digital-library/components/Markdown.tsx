import { Fragment, type ReactNode } from "react";

// 의존성 없는 경량 마크다운 렌더러 (#, ##, ###, -, 1., >, ---, 표, **굵게**)
// HTML을 문자열로 주입하지 않고 React 요소로 만들기 때문에 XSS에 안전하다.
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  );
}

export default function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: ReactNode[] = [];
  let list: { type: "ul" | "ol"; items: string[] } | null = null;
  let para: string[] = [];

  const flushPara = () => {
    if (para.length) out.push(<p key={out.length}>{inline(para.join(" "))}</p>);
    para = [];
  };
  const flushList = () => {
    if (list) {
      const items = list.items.map((t, i) => <li key={i}>{inline(t)}</li>);
      out.push(list.type === "ul" ? <ul key={out.length}>{items}</ul> : <ol key={out.length}>{items}</ol>);
    }
    list = null;
  };

  const cells = (row: string) => row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();
    let m: RegExpMatchArray | null;
    if (!line.trim()) { flushPara(); flushList(); continue; }
    // 표: | a | b | 다음 줄이 |---|---|
    if (line.trim().startsWith("|") && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1] ?? "")) {
      flushPara(); flushList();
      const head = cells(line);
      const body: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) body.push(cells(lines[i++]));
      i--;
      out.push(
        <div key={out.length} className="overflow-x-auto my-4">
          <table className="w-full text-sm border-collapse">
            <thead><tr>{head.map((h, j) => <th key={j} className="border border-stone-200 bg-stone-50 px-3 py-2 text-left font-semibold">{inline(h)}</th>)}</tr></thead>
            <tbody>{body.map((r, k) => <tr key={k}>{r.map((c, j) => <td key={j} className="border border-stone-200 px-3 py-2 align-top">{inline(c)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    if ((m = line.match(/^(#{1,3})\s+(.*)$/))) {
      flushPara(); flushList();
      const Tag = (["h1", "h2", "h3"] as const)[m[1].length - 1];
      out.push(<Tag key={out.length}>{inline(m[2])}</Tag>);
    } else if (/^---+$/.test(line.trim())) {
      flushPara(); flushList(); out.push(<hr key={out.length} />);
    } else if ((m = line.match(/^>\s?(.*)$/))) {
      flushPara(); flushList(); out.push(<blockquote key={out.length}>{inline(m[1])}</blockquote>);
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      flushPara();
      if (list?.type !== "ul") { flushList(); list = { type: "ul", items: [] }; }
      list!.items.push(m[1]);
    } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      flushPara();
      if (list?.type !== "ol") { flushList(); list = { type: "ol", items: [] }; }
      list!.items.push(m[1]);
    } else {
      flushList(); para.push(line.trim());
    }
  }
  flushPara(); flushList();
  return <div className="prose-ko text-[15px] text-stone-800">{out}</div>;
}
