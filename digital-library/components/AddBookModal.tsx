"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "./api";
import type { Book, Category, WishItem } from "@/lib/types";

export default function AddBookModal({
  categories, defaultCategory, wish, onClose, onSaved,
}: {
  categories: Category[];
  defaultCategory?: string;
  wish?: WishItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const router = useRouter();
  const [form, setForm] = useState({
    title: wish?.title ?? "", originalTitle: "", author: wish?.author ?? "", publisher: "", publishedYear: "",
    era: "", industry: "", coreMessages: "", actionItems: "",
  });
  const [cats, setCats] = useState<string[]>(defaultCategory ? [defaultCategory] : []);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const book = await api.post<Book>("/api/books", { ...form, categoryIds: cats, fromWishId: wish?.id });
      onSaved();
      router.push(`/books/${book.id}`);
    } catch (e) {
      setErr((e as Error).message);
      setSaving(false);
    }
  };

  const field = "w-full px-3 py-2 rounded-lg border border-stone-300 text-sm";
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto p-6 space-y-3">
        <h2 className="text-lg font-bold">도서 등록</h2>
        <p className="text-xs text-stone-500">오늘 날짜로 등록되며, 1·3·7·30일 후 복습 대상에 자동으로 오릅니다. 요약과 메모는 등록 후 상세 화면에서 작성합니다.</p>
        <div className="grid grid-cols-2 gap-2">
          <input required placeholder="제목 *" value={form.title} onChange={set("title")} className={field} />
          <input placeholder="원제" value={form.originalTitle} onChange={set("originalTitle")} className={field} />
          <input required placeholder="저자 *" value={form.author} onChange={set("author")} className={field} />
          <div className="grid grid-cols-2 gap-2">
            <input placeholder="출판사" value={form.publisher} onChange={set("publisher")} className={field} />
            <input placeholder="출간연도" value={form.publishedYear} onChange={set("publishedYear")} className={field} />
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {categories.map((c) => {
            const on = cats.includes(c.id);
            return (
              <button type="button" key={c.id} onClick={() => setCats(on ? cats.filter((x) => x !== c.id) : [...cats, c.id])}
                className={`text-xs px-2.5 py-1 rounded-full border ${on ? "bg-stone-900 text-white border-stone-900" : "border-stone-300"}`}>
                {c.name}
              </button>
            );
          })}
        </div>
        <input placeholder="시대 배경" value={form.era} onChange={set("era")} className={field} />
        <input placeholder="산업 배경" value={form.industry} onChange={set("industry")} className={field} />
        <textarea placeholder="핵심 메시지 3줄 (한 줄에 하나)" rows={3} value={form.coreMessages} onChange={set("coreMessages")} className={field} />
        <textarea placeholder="실전 액션 아이템 (한 줄에 하나, 5~7개 권장)" rows={5} value={form.actionItems} onChange={set("actionItems")} className={field} />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg hover:bg-stone-100">취소</button>
          <button disabled={saving} className="px-4 py-2 text-sm rounded-lg bg-amber-600 text-white font-medium disabled:opacity-50">{saving ? "저장 중…" : "등록"}</button>
        </div>
      </form>
    </div>
  );
}
