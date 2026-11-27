"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import BookCover from "./BookCover";
import Markdown from "./Markdown";
import { dueDate, todayStr } from "@/lib/review";
import type { ActionItem, Book, BookDetail, LibraryData, NoteKind } from "@/lib/types";
import { REVIEW_STAGES } from "@/lib/types";

type Tab = "summary" | "actions" | "notes";
const TABS: { id: Tab; label: string }[] = [
  { id: "summary", label: "① 핵심 요약" },
  { id: "actions", label: "② 실전 실행 인사이트" },
  { id: "notes", label: "③ 북마크 & 메모" },
];

export default function BookDetailView({ id }: { id: string }) {
  const router = useRouter();
  const [book, setBook] = useState<BookDetail | null>(null);
  const [lib, setLib] = useState<LibraryData | null>(null);
  const [missing, setMissing] = useState(false);
  const [tab, setTab] = useState<Tab>("summary");

  const load = useCallback(async () => {
    try {
      const [b, l] = await Promise.all([api.get<BookDetail>(`/api/books/${id}`), api.get<LibraryData>("/api/library")]);
      setBook(b);
      setLib(l);
    } catch {
      setMissing(true);
    }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  /** 낙관적 업데이트 후 저장 */
  const patch = async (p: Partial<Book>) => {
    setBook((b) => (b ? { ...b, ...p } : b));
    await api.patch(`/api/books/${id}`, p);
  };

  if (missing) return <div className="p-10">도서를 찾을 수 없습니다. <Link href="/" className="underline">서재로</Link></div>;
  if (!book || !lib) return <div className="p-10 text-stone-500">불러오는 중…</div>;

  const catNames = book.categoryIds.map((c) => lib.categories.find((x) => x.id === c)?.name).filter(Boolean);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex justify-between items-center mb-5">
        <Link href="/" className="text-sm text-stone-500 hover:text-stone-900">← 서재로</Link>
        <button
          onClick={async () => {
            if (!confirm(`'${book.title}'을(를) 서재에서 삭제할까요? 요약·메모 파일도 함께 삭제됩니다.`)) return;
            await api.del(`/api/books/${id}`);
            router.push("/");
          }}
          className="text-xs text-stone-400 hover:text-red-600"
        >도서 삭제</button>
      </div>

      <header className="flex gap-6 items-start">
        <BookCover book={book} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-1 mb-2">
            {catNames.map((n) => <span key={n} className="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">{n}</span>)}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold">{book.title}</h1>
          {book.originalTitle && <p className="text-sm text-stone-500 italic">{book.originalTitle}</p>}
          <p className="mt-1 text-stone-700">{book.author}</p>
          <p className="text-xs text-stone-500 mt-1">
            {[book.publisher, book.publishedYear].filter(Boolean).join(" · ")} · 서재 등록 {book.registeredAt}
          </p>
          <ReviewTrack book={book} onPatch={patch} />
          <CategoryPicker book={book} lib={lib} onPatch={patch} />
        </div>
      </header>

      <nav className="flex gap-1 mt-8 border-b border-stone-300 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-sm whitespace-nowrap -mb-px border-b-2 ${tab === t.id ? "border-stone-900 font-semibold" : "border-transparent text-stone-500 hover:text-stone-800"}`}>
            {t.label}
            {t.id === "actions" && <span className="ml-1 text-xs text-amber-700">{book.actionItems.filter((a) => a.done).length}/{book.actionItems.length}</span>}
            {t.id === "notes" && <span className="ml-1 text-xs text-stone-400">{book.highlights.length}</span>}
          </button>
        ))}
      </nav>

      <div className="py-6">
        {tab === "summary" && <SummaryTab book={book} onPatch={patch} />}
        {tab === "actions" && <ActionsTab book={book} onPatch={patch} />}
        {tab === "notes" && <NotesTab book={book} onPatch={patch} />}
      </div>

      <RelatedBooks book={book} lib={lib} onAdded={load} />
    </div>
  );
}

/* ───────── 복습 진행 표시 ───────── */
function ReviewTrack({ book, onPatch }: { book: Book; onPatch: (p: Partial<Book>) => void }) {
  const today = todayStr();
  return (
    <div className="flex flex-wrap gap-1.5 mt-4">
      {REVIEW_STAGES.map((s) => {
        const done = book.reviews?.[`${s}`];
        const due = dueDate(book.registeredAt, s);
        const reached = due <= today;
        return (
          <button key={s}
            title={done ? `${done} 복습 완료 (클릭해 취소)` : `${due} 복습 예정`}
            onClick={() => onPatch({ reviews: { ...book.reviews, [`${s}`]: done ? null : today } })}
            className={`text-[11px] px-2 py-1 rounded-md border ${
              done ? "bg-emerald-600 text-white border-emerald-600" : reached ? "border-amber-500 text-amber-700 bg-amber-50" : "border-stone-300 text-stone-400"
            }`}>
            {done ? "✓ " : ""}{s}일차 · {due.slice(5)}
          </button>
        );
      })}
    </div>
  );
}

function CategoryPicker({ book, lib, onPatch }: { book: Book; lib: LibraryData; onPatch: (p: Partial<Book>) => void }) {
  const [open, setOpen] = useState(false);
  if (!open) return <button onClick={() => setOpen(true)} className="text-xs text-stone-400 hover:text-stone-700 mt-2">분류 변경</button>;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2 items-center">
      {lib.categories.map((c) => {
        const on = book.categoryIds.includes(c.id);
        return (
          <button key={c.id} onClick={() => onPatch({ categoryIds: on ? book.categoryIds.filter((x) => x !== c.id) : [...book.categoryIds, c.id] })}
            className={`text-[11px] px-2 py-0.5 rounded-full border ${on ? "bg-stone-900 text-white border-stone-900" : "border-stone-300"}`}>
            {c.name}
          </button>
        );
      })}
      <button onClick={() => setOpen(false)} className="text-xs text-stone-500 ml-1">닫기</button>
    </div>
  );
}

/* ───────── 탭 1: 핵심 요약 ───────── */
function SummaryTab({ book, onPatch }: { book: BookDetail; onPatch: (p: Partial<Book>) => void }) {
  const [kind, setKind] = useState<"short" | "long">("short");
  const [editingBg, setEditingBg] = useState(false);
  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-2 gap-4">
        <Card title="시대 배경">{book.background.era || <Empty />}</Card>
        <Card title="산업 배경">{book.background.industry || <Empty />}</Card>
      </div>

      <Card title="핵심 메시지 3줄" action={<button onClick={() => setEditingBg((v) => !v)} className="text-xs text-stone-500">{editingBg ? "닫기" : "편집"}</button>}>
        {editingBg ? (
          <BackgroundEditor book={book} onSave={(p) => { onPatch(p); setEditingBg(false); }} />
        ) : (
          <ol className="space-y-2">
            {book.coreMessages.map((m, i) => (
              <li key={i} className="flex gap-3">
                <span className="w-6 h-6 shrink-0 rounded-full bg-stone-900 text-white text-xs flex items-center justify-center">{i + 1}</span>
                <span className="leading-relaxed">{m}</span>
              </li>
            ))}
            {book.coreMessages.length === 0 && <Empty />}
          </ol>
        )}
      </Card>

      <div>
        <div className="flex items-center gap-2 mb-3">
          <h3 className="font-semibold">분량별 요약</h3>
          <div className="flex rounded-lg border border-stone-300 overflow-hidden text-xs bg-white">
            <button onClick={() => setKind("short")} className={`px-3 py-1.5 ${kind === "short" ? "bg-stone-900 text-white" : ""}`}>2,000자 압축본</button>
            <button onClick={() => setKind("long")} className={`px-3 py-1.5 ${kind === "long" ? "bg-stone-900 text-white" : ""}`}>10,000자 심화본</button>
          </div>
        </div>
        <NoteEditor key={kind} bookId={book.id} kind={kind} initial={book.notes[kind]}
          placeholder={kind === "short" ? "약 2,000자 분량의 압축 요약을 마크다운으로 작성하세요." : "약 10,000자 분량의 심화 요약을 마크다운으로 작성하세요."} />
      </div>
    </div>
  );
}

function BackgroundEditor({ book, onSave }: { book: Book; onSave: (p: Partial<Book>) => void }) {
  const [era, setEra] = useState(book.background.era);
  const [industry, setIndustry] = useState(book.background.industry);
  const [msgs, setMsgs] = useState(book.coreMessages.join("\n"));
  const f = "w-full px-3 py-2 rounded-lg border border-stone-300 text-sm";
  return (
    <div className="space-y-2">
      <textarea rows={3} value={msgs} onChange={(e) => setMsgs(e.target.value)} className={f} placeholder="핵심 메시지 (한 줄에 하나, 최대 3줄)" />
      <input value={era} onChange={(e) => setEra(e.target.value)} className={f} placeholder="시대 배경" />
      <input value={industry} onChange={(e) => setIndustry(e.target.value)} className={f} placeholder="산업 배경" />
      <button onClick={() => onSave({ coreMessages: msgs.split("\n").map((s) => s.trim()).filter(Boolean).slice(0, 3), background: { era, industry } })}
        className="px-3 py-1.5 text-sm rounded-lg bg-stone-900 text-white">저장</button>
    </div>
  );
}

/** 마크다운 파일(data/notes/*.md)을 보고/고치는 공용 편집기 */
function NoteEditor({ bookId, kind, initial, placeholder }: { bookId: string; kind: NoteKind; initial: string; placeholder: string }) {
  const [text, setText] = useState(initial);
  const [saved, setSaved] = useState(initial);
  const [editing, setEditing] = useState(!initial);
  const [status, setStatus] = useState("");
  const dirty = text !== saved;
  const chars = [...text].length;
  const charsNoSpace = [...text.replace(/\s/g, "")].length;

  const save = async () => {
    setStatus("저장 중…");
    try {
      await api.put(`/api/books/${bookId}/notes/${kind}`, { content: text });
      setSaved(text);
      setStatus("저장됨");
      setEditing(false);
    } catch (e) {
      setStatus(`저장 실패: ${(e as Error).message}`);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-stone-200">
      <div className="flex items-center justify-between px-4 py-2 border-b border-stone-100 text-xs text-stone-500">
        <span>{chars.toLocaleString()}자 (공백 제외 {charsNoSpace.toLocaleString()}자) · <code>data/notes/{bookId}--{kind}.md</code></span>
        <div className="flex items-center gap-3">
          {status && <span>{status}</span>}
          {editing ? (
            <>
              {saved && <button onClick={() => { setText(saved); setEditing(false); }} className="hover:text-stone-900">취소</button>}
              <button onClick={save} disabled={!dirty} className="px-2.5 py-1 rounded bg-stone-900 text-white disabled:opacity-40">저장</button>
            </>
          ) : (
            <button onClick={() => { setEditing(true); setStatus(""); }} className="hover:text-stone-900">편집</button>
          )}
        </div>
      </div>
      {editing ? (
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder}
          className="w-full min-h-[420px] p-4 text-sm font-mono leading-relaxed outline-none rounded-b-xl" />
      ) : (
        <div className="p-5 sm:p-7"><Markdown source={text} /></div>
      )}
    </div>
  );
}

/* ───────── 탭 2: 실전 실행 인사이트 ───────── */
function ActionsTab({ book, onPatch }: { book: Book; onPatch: (p: Partial<Book>) => void }) {
  const [draft, setDraft] = useState("");
  const items = book.actionItems;
  const done = items.filter((a) => a.done).length;
  const update = (next: ActionItem[]) => onPatch({ actionItems: next });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-stone-200 rounded-full">
          <div className="h-2 bg-amber-500 rounded-full transition-all" style={{ width: items.length ? `${(done / items.length) * 100}%` : 0 }} />
        </div>
        <span className="text-sm font-semibold">{done}/{items.length} 실행 완료</span>
      </div>
      <p className="text-xs text-stone-500">내 현재 직무에 바로 적용할 행동입니다. 실행했으면 체크하고, 항목은 더블클릭해 고칠 수 있습니다.</p>
      <ul className="space-y-2">
        {items.map((a, i) => (
          <li key={a.id} className={`flex gap-3 items-start bg-white rounded-xl border p-4 ${a.done ? "border-emerald-200 bg-emerald-50/50" : "border-stone-200"}`}>
            <input type="checkbox" checked={a.done} className="mt-1 w-4 h-4 accent-emerald-600"
              onChange={() => update(items.map((x) => (x.id === a.id ? { ...x, done: !x.done, doneAt: !x.done ? todayStr() : null } : x)))} />
            <div className="flex-1">
              <span className="text-xs font-bold text-stone-400 mr-2">ACTION {i + 1}</span>
              <EditableText value={a.text} className={a.done ? "line-through text-stone-400" : ""}
                onSave={(text) => update(items.map((x) => (x.id === a.id ? { ...x, text } : x)))} />
              {a.done && a.doneAt && <div className="text-[11px] text-emerald-700 mt-1">{a.doneAt} 실행</div>}
            </div>
            <button onClick={() => update(items.filter((x) => x.id !== a.id))} className="text-stone-300 hover:text-red-600 text-sm">✕</button>
          </li>
        ))}
      </ul>
      <form onSubmit={(e) => { e.preventDefault(); if (!draft.trim()) return; update([...items, { id: `a-${Date.now()}`, text: draft.trim(), done: false }]); setDraft(""); }} className="flex gap-2">
        <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="새 액션 아이템 추가" className="flex-1 px-3 py-2 rounded-lg border border-stone-300 text-sm bg-white" />
        <button className="px-4 py-2 rounded-lg bg-stone-900 text-white text-sm">추가</button>
      </form>
    </div>
  );
}

function EditableText({ value, onSave, className = "" }: { value: string; onSave: (v: string) => void; className?: string }) {
  const [editing, setEditing] = useState(false);
  const [v, setV] = useState(value);
  if (!editing) return <span onDoubleClick={() => { setV(value); setEditing(true); }} className={`leading-relaxed cursor-text ${className}`}>{value}</span>;
  return (
    <textarea autoFocus value={v} onChange={(e) => setV(e.target.value)} rows={2}
      onBlur={() => { setEditing(false); if (v.trim() && v !== value) onSave(v.trim()); }}
      className="w-full mt-1 px-2 py-1 text-sm rounded border border-stone-300" />
  );
}

/* ───────── 탭 3: 북마크 & 메모 ───────── */
function NotesTab({ book, onPatch }: { book: BookDetail; onPatch: (p: Partial<Book>) => void }) {
  const [text, setText] = useState("");
  const [page, setPage] = useState("");
  const add = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    onPatch({ highlights: [{ id: `h-${Date.now()}`, text: text.trim(), page: page.trim() || undefined, createdAt: todayStr() }, ...book.highlights] });
    setText("");
    setPage("");
  };
  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <section>
        <h3 className="font-semibold mb-3">인상 깊은 문장</h3>
        <form onSubmit={add} className="bg-white rounded-xl border border-stone-200 p-3 space-y-2 mb-3">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder="밑줄 그은 문장을 옮겨 적으세요" className="w-full text-sm outline-none resize-none" />
          <div className="flex gap-2">
            <input value={page} onChange={(e) => setPage(e.target.value)} placeholder="쪽/챕터 (선택)" className="flex-1 px-2 py-1.5 text-xs rounded border border-stone-200" />
            <button className="px-3 py-1.5 text-xs rounded-lg bg-amber-500 text-stone-900 font-semibold">하이라이트 저장</button>
          </div>
        </form>
        <ul className="space-y-2">
          {book.highlights.map((h) => (
            <li key={h.id} className="group bg-amber-50 border-l-4 border-amber-400 rounded-r-lg p-3">
              <p className="text-sm leading-relaxed">“{h.text}”</p>
              <div className="flex justify-between text-[11px] text-stone-500 mt-1.5">
                <span>{[h.page, h.createdAt].filter(Boolean).join(" · ")}</span>
                <button onClick={() => onPatch({ highlights: book.highlights.filter((x) => x.id !== h.id) })} className="opacity-0 group-hover:opacity-100 hover:text-red-600">삭제</button>
              </div>
            </li>
          ))}
          {book.highlights.length === 0 && <p className="text-sm text-stone-500">아직 저장한 문장이 없습니다.</p>}
        </ul>
      </section>
      <section>
        <h3 className="font-semibold mb-3">내 현장 적용 메모</h3>
        <NoteEditor bookId={book.id} kind="memo" initial={book.notes.memo}
          placeholder={"이 책을 내 업무에 어떻게 적용했는지 기록하세요.\n\n## 적용한 상황\n- \n\n## 결과와 다음 시도\n- "} />
      </section>
    </div>
  );
}

/* ───────── 연관 도서 추천 ───────── */
function RelatedBooks({ book, lib, onAdded }: { book: Book; lib: LibraryData; onAdded: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  if (!book.related.length) return null;
  const inWish = (t: string) => lib.wishlist.some((w) => w.title === t);
  const owned = (t: string) => lib.books.some((b) => b.title === t);
  return (
    <section className="mt-6 pt-6 border-t border-stone-300">
      <h2 className="font-semibold mb-1">함께 읽으면 좋은 책</h2>
      <p className="text-xs text-stone-500 mb-4">이 책의 문제의식을 다른 각도에서 넓혀 줄 책들입니다.</p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {book.related.map((r) => {
          const state = owned(r.title) ? "owned" : inWish(r.title) ? "wish" : "none";
          return (
            <div key={r.title} className="bg-white rounded-xl border border-stone-200 p-4 flex flex-col">
              <div className="font-semibold text-sm">{r.title}</div>
              <div className="text-xs text-stone-500">{r.author}</div>
              <p className="text-xs text-stone-700 mt-2 leading-relaxed flex-1">{r.reason}</p>
              <button
                disabled={state !== "none" || busy === r.title}
                onClick={async () => { setBusy(r.title); await api.post("/api/wishlist", { ...r, fromBookId: book.id }); setBusy(null); onAdded(); }}
                className={`mt-3 text-xs py-1.5 rounded-lg font-medium ${state === "none" ? "bg-stone-900 text-white hover:bg-stone-700" : "bg-stone-100 text-stone-500"}`}>
                {state === "owned" ? "이미 서재에 있음" : state === "wish" ? "✓ 읽을 책에 담김" : "+ 읽을 책에 추가"}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Card({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-stone-200 p-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-xs font-semibold text-stone-500 tracking-wide">{title}</h3>
        {action}
      </div>
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  );
}

const Empty = () => <span className="text-stone-400">아직 작성되지 않았습니다.</span>;
