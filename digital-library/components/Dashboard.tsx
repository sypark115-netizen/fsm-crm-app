"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import BookCover from "./BookCover";
import AddBookModal from "./AddBookModal";
import { getDueReviews, getUpcomingReviews, reviewProgress, todayStr } from "@/lib/review";
import type { Book, Category, LibraryData, WishItem } from "@/lib/types";
import { REVIEW_STAGES } from "@/lib/types";

type View = "grid" | "list";
const VIEW_KEY = "library:view";

export default function Dashboard() {
  const [data, setData] = useState<LibraryData | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState<string>("all");
  const [view, setView] = useState<View>("grid");
  const [query, setQuery] = useState("");
  const [manageCats, setManageCats] = useState(false);
  const [adding, setAdding] = useState<null | { wish?: WishItem }>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.get<LibraryData>("/api/library"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
    try {
      const v = localStorage.getItem(VIEW_KEY);
      if (v === "grid" || v === "list") setView(v);
    } catch {}
  }, [load]);

  const changeView = (v: View) => {
    setView(v);
    try { localStorage.setItem(VIEW_KEY, v); } catch {}
  };

  const books = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.books.filter(
      (b) =>
        (active === "all" || b.categoryIds.includes(active)) &&
        (!q || `${b.title} ${b.originalTitle ?? ""} ${b.author}`.toLowerCase().includes(q)),
    );
  }, [data, active, query]);

  if (error) return <div className="p-10 text-red-700">불러오기 실패: {error}</div>;
  if (!data) return <div className="p-10 text-stone-500">서재를 여는 중…</div>;

  const catName = (id: string) => data.categories.find((c) => c.id === id)?.name ?? "";
  const counts = (id: string) => (id === "all" ? data.books.length : data.books.filter((b) => b.categoryIds.includes(id)).length);
  const totalActions = data.books.reduce((n, b) => n + b.actionItems.length, 0);
  const doneActions = data.books.reduce((n, b) => n + b.actionItems.filter((a) => a.done).length, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <header className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-xs tracking-widest text-stone-500">PERSONAL INSIGHT LIBRARY</p>
          <h1 className="text-2xl sm:text-3xl font-bold">인사이트 서재</h1>
          <p className="text-sm text-stone-500 mt-1">읽은 책을 내 업무의 다음 행동으로 바꾸는 곳</p>
        </div>
        <div className="flex gap-3 text-sm">
          <Stat label="소장 도서" value={`${data.books.length}권`} />
          <Stat label="실행 완료" value={`${doneActions}/${totalActions}`} />
          <Stat label="읽을 책" value={`${data.wishlist.length}권`} />
        </div>
      </header>

      <ReviewBoard books={data.books} onChange={load} />

      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_280px] gap-6 mt-6">
        {/* 카테고리 */}
        <aside className="min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-stone-600">분야별 책장</h2>
            <button onClick={() => setManageCats((v) => !v)} className="text-xs text-stone-500 hover:text-stone-900">
              {manageCats ? "완료" : "편집"}
            </button>
          </div>
          {manageCats ? (
            <CategoryManager categories={data.categories} onChange={load} onDeleted={(id) => active === id && setActive("all")} />
          ) : (
            <nav className="flex lg:flex-col gap-1 overflow-x-auto pb-1">
              {[{ id: "all", name: "전체" }, ...data.categories].map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActive(c.id)}
                  className={`text-left whitespace-nowrap px-3 py-2 rounded-lg text-sm flex justify-between gap-3 ${
                    active === c.id ? "bg-stone-900 text-white" : "hover:bg-stone-200 text-stone-700"
                  }`}
                >
                  <span>{c.name}</span>
                  <span className="opacity-60">{counts(c.id)}</span>
                </button>
              ))}
            </nav>
          )}
        </aside>

        {/* 책장 */}
        <main className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="제목·저자 검색"
              className="flex-1 min-w-[160px] px-3 py-2 rounded-lg border border-stone-300 bg-white text-sm"
            />
            <div className="flex rounded-lg border border-stone-300 overflow-hidden text-sm bg-white">
              {(["grid", "list"] as View[]).map((v) => (
                <button key={v} onClick={() => changeView(v)} className={`px-3 py-2 ${view === v ? "bg-stone-900 text-white" : ""}`}>
                  {v === "grid" ? "카드" : "리스트"}
                </button>
              ))}
            </div>
            <button onClick={() => setAdding({})} className="px-3 py-2 rounded-lg bg-amber-600 text-white text-sm font-medium hover:bg-amber-700">
              + 도서 등록
            </button>
          </div>

          {books.length === 0 ? (
            <div className="py-16 text-center text-stone-500 border-2 border-dashed border-stone-300 rounded-xl">이 책장에 아직 책이 없습니다.</div>
          ) : view === "grid" ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-4">
              {books.map((b) => (
                <Link key={b.id} href={`/books/${b.id}`} className="group bg-white rounded-xl p-3 shadow-sm hover:shadow-md transition border border-stone-200">
                  <div className="group-hover:-translate-y-0.5 transition"><BookCover book={b} /></div>
                  <div className="mt-3 font-semibold text-sm line-clamp-1">{b.title}</div>
                  <div className="text-xs text-stone-500 line-clamp-1">{b.author}</div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {b.categoryIds.map((c) => <Tag key={c}>{catName(c)}</Tag>)}
                  </div>
                  <Progress book={b} />
                </Link>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-stone-200 divide-y divide-stone-100">
              {books.map((b) => (
                <Link key={b.id} href={`/books/${b.id}`} className="flex items-center gap-4 p-3 hover:bg-stone-50">
                  <BookCover book={b} size="sm" />
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm">{b.title} <span className="text-stone-400 font-normal">· {b.author}</span></div>
                    <div className="text-xs text-stone-500 line-clamp-1 mt-0.5">{b.coreMessages[0]}</div>
                    <div className="flex flex-wrap gap-1 mt-1">{b.categoryIds.map((c) => <Tag key={c}>{catName(c)}</Tag>)}</div>
                  </div>
                  <div className="hidden sm:block w-40"><Progress book={b} /></div>
                  <div className="text-xs text-stone-400 w-20 text-right">{b.registeredAt}</div>
                </Link>
              ))}
            </div>
          )}
        </main>

        {/* 위시리스트 */}
        <aside className="min-w-0">
          <h2 className="text-sm font-semibold text-stone-600 mb-2">읽을 책 (위시리스트)</h2>
          <div className="bg-white rounded-xl border border-stone-200 divide-y divide-stone-100">
            {data.wishlist.length === 0 && <p className="p-4 text-sm text-stone-500">도서 상세의 ‘함께 읽으면 좋은 책’에서 추가하세요.</p>}
            {data.wishlist.map((w) => (
              <div key={w.id} className="p-3">
                <div className="text-sm font-semibold">{w.title}</div>
                <div className="text-xs text-stone-500">{w.author}</div>
                {w.reason && <p className="text-xs text-stone-600 mt-1 line-clamp-3">{w.reason}</p>}
                <div className="flex gap-3 mt-2 text-xs">
                  <button onClick={() => setAdding({ wish: w })} className="text-amber-700 hover:underline">서재에 등록</button>
                  <button onClick={async () => { await api.del(`/api/wishlist?id=${w.id}`); load(); }} className="text-stone-400 hover:text-red-600">삭제</button>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      {adding && (
        <AddBookModal
          categories={data.categories}
          defaultCategory={active !== "all" ? active : undefined}
          wish={adding.wish}
          onClose={() => setAdding(null)}
          onSaved={() => { setAdding(null); load(); }}
        />
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-stone-200 rounded-lg px-3 py-2 text-center min-w-[84px]">
      <div className="text-[11px] text-stone-500">{label}</div>
      <div className="font-bold">{value}</div>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="text-[10px] px-1.5 py-0.5 rounded bg-stone-100 text-stone-600">{children}</span>;
}

function Progress({ book }: { book: Book }) {
  const total = book.actionItems.length;
  const done = book.actionItems.filter((a) => a.done).length;
  return (
    <div className="mt-2 space-y-1">
      <div className="flex justify-between text-[10px] text-stone-500">
        <span>실행 {done}/{total}</span>
        <span>복습 {reviewProgress(book)}/{REVIEW_STAGES.length}</span>
      </div>
      <div className="h-1 bg-stone-100 rounded">
        <div className="h-1 bg-amber-500 rounded" style={{ width: total ? `${(done / total) * 100}%` : 0 }} />
      </div>
    </div>
  );
}

/** 에빙하우스 복습 리마인더 */
function ReviewBoard({ books, onChange }: { books: Book[]; onChange: () => void }) {
  const due = getDueReviews(books);
  const upcoming = getUpcomingReviews(books);
  const [busy, setBusy] = useState<string | null>(null);

  const complete = async (book: Book, stage: number) => {
    setBusy(book.id);
    await api.patch(`/api/books/${book.id}`, { reviews: { ...book.reviews, [`${stage}`]: todayStr() } });
    setBusy(null);
    onChange();
  };

  return (
    <section className="rounded-2xl bg-stone-900 text-stone-100 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <h2 className="font-semibold">오늘의 복습 <span className="text-amber-400">{due.length}</span></h2>
        <p className="text-xs text-stone-400">에빙하우스 망각곡선 · 등록일 기준 1일 / 3일 / 7일 / 30일 후</p>
      </div>
      {due.length === 0 ? (
        <p className="text-sm text-stone-400">오늘 복습할 책이 없습니다. 기억이 잘 유지되고 있어요.</p>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {due.map(({ book, stage, overdueDays }) => (
            <div key={book.id} className="flex items-center gap-3 bg-stone-800 rounded-xl p-3">
              <BookCover book={book} size="sm" />
              <div className="flex-1 min-w-0">
                <Link href={`/books/${book.id}`} className="text-sm font-semibold hover:underline line-clamp-1">{book.title}</Link>
                <div className="text-xs text-stone-400 mt-0.5">
                  <span className="text-amber-400 font-medium">{stage}일차 복습</span>
                  {overdueDays > 0 && <span className="ml-1 text-red-300">· {overdueDays}일 지남</span>}
                </div>
                <div className="text-[11px] text-stone-500 line-clamp-1 mt-0.5">{book.coreMessages[0]}</div>
              </div>
              <button
                disabled={busy === book.id}
                onClick={() => complete(book, stage)}
                className="text-xs px-2.5 py-1.5 rounded-lg bg-amber-500 text-stone-900 font-semibold hover:bg-amber-400 disabled:opacity-50 whitespace-nowrap"
              >
                복습 완료
              </button>
            </div>
          ))}
        </div>
      )}
      {upcoming.length > 0 && (
        <div className="mt-3 text-xs text-stone-400">
          다가오는 복습:{" "}
          {upcoming.map((u) => `${u.book.title} (${u.stage}일차, ${u.inDays}일 후)`).join(" · ")}
        </div>
      )}
    </section>
  );
}

function CategoryManager({ categories, onChange, onDeleted }: { categories: Category[]; onChange: () => void; onDeleted: (id: string) => void }) {
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const run = async (fn: () => Promise<unknown>) => {
    try { setErr(""); await fn(); onChange(); } catch (e) { setErr((e as Error).message); }
  };
  return (
    <div className="space-y-2">
      {categories.map((c) => (
        <div key={c.id} className="flex gap-1">
          <input
            defaultValue={c.name}
            onBlur={(e) => e.target.value.trim() && e.target.value !== c.name && run(() => api.patch("/api/categories", { id: c.id, name: e.target.value }))}
            className="flex-1 min-w-0 px-2 py-1.5 text-sm rounded border border-stone-300 bg-white"
          />
          <button
            title="삭제"
            onClick={() => confirm(`'${c.name}' 카테고리를 삭제할까요? (책은 삭제되지 않습니다)`) && run(async () => { await api.del(`/api/categories?id=${c.id}`); onDeleted(c.id); })}
            className="px-2 text-stone-400 hover:text-red-600"
          >✕</button>
        </div>
      ))}
      <form
        onSubmit={(e) => { e.preventDefault(); if (name.trim()) run(async () => { await api.post("/api/categories", { name }); setName(""); }); }}
        className="flex gap-1"
      >
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="새 카테고리" className="flex-1 min-w-0 px-2 py-1.5 text-sm rounded border border-dashed border-stone-400 bg-white" />
        <button className="px-2 text-sm text-amber-700 font-medium">추가</button>
      </form>
      {err && <p className="text-xs text-red-600">{err}</p>}
      <p className="text-[11px] text-stone-400">이름을 고친 뒤 칸 밖을 누르면 저장됩니다.</p>
    </div>
  );
}
