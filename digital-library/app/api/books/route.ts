import { mutateLibrary, newId, slugId, writeNote } from "@/lib/store";
import { bad, readJson, str } from "@/lib/http";
import { todayStr } from "@/lib/review";
import type { Book } from "@/lib/types";

const COLORS = ["#1e3a5f", "#7c2d12", "#14532d", "#4c1d95", "#713f12", "#134e4a", "#831843"];

/** 새 도서 등록 */
export async function POST(req: Request) {
  const body = await readJson<Record<string, unknown>>(req);
  if (!body) return bad("JSON 본문이 필요합니다.");
  const title = str(body.title, 200);
  const author = str(body.author, 200);
  if (!title || !author) return bad("제목과 저자는 필수입니다.");

  const lines = (v: unknown) =>
    (Array.isArray(v) ? v : typeof v === "string" ? v.split("\n") : [])
      .map((s) => str(s, 1000))
      .filter(Boolean);

  const book: Book = {
    id: slugId(str(body.originalTitle, 200) || title),
    title,
    originalTitle: str(body.originalTitle, 200) || undefined,
    author,
    publisher: str(body.publisher, 100) || undefined,
    publishedYear: str(body.publishedYear, 20) || undefined,
    categoryIds: Array.isArray(body.categoryIds) ? body.categoryIds.map((c) => str(c, 60)).filter(Boolean) : [],
    coverColor: COLORS[Math.floor(Math.random() * COLORS.length)],
    registeredAt: /^\d{4}-\d{2}-\d{2}$/.test(str(body.registeredAt)) ? str(body.registeredAt) : todayStr(),
    background: { era: str(body.era, 500), industry: str(body.industry, 500) },
    coreMessages: lines(body.coreMessages).slice(0, 3),
    actionItems: lines(body.actionItems).slice(0, 10).map((text) => ({ id: newId("a-"), text, done: false })),
    highlights: [],
    reviews: {},
    related: [],
  };

  await mutateLibrary((d) => {
    d.books.unshift(book);
    // 위시리스트에서 옮겨온 책이면 위시리스트에서 제거
    const wishId = str(body.fromWishId, 60);
    if (wishId) d.wishlist = d.wishlist.filter((w) => w.id !== wishId);
  });
  await writeNote(book.id, "short", "");
  await writeNote(book.id, "long", "");
  await writeNote(book.id, "memo", "");
  return Response.json(book, { status: 201 });
}
