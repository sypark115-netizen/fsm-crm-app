import { deleteNotes, mutateLibrary, readBookDetail } from "@/lib/store";
import { bad, readJson } from "@/lib/http";
import type { Book } from "@/lib/types";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_req: Request, { params }: Ctx) {
  const { id } = await params;
  const book = await readBookDetail(id);
  return book ? Response.json(book) : bad("도서를 찾을 수 없습니다.", 404);
}

// 클라이언트가 바꿀 수 있는 필드만 허용
const EDITABLE: (keyof Book)[] = [
  "title", "originalTitle", "author", "publisher", "publishedYear", "categoryIds",
  "background", "coreMessages", "actionItems", "highlights", "reviews", "related",
  "registeredAt", "coverColor",
];

export async function PATCH(req: Request, { params }: Ctx) {
  const { id } = await params;
  const patch = await readJson<Partial<Book>>(req);
  if (!patch || typeof patch !== "object") return bad("JSON 본문이 필요합니다.");

  const updated = await mutateLibrary((d) => {
    const book = d.books.find((b) => b.id === id);
    if (!book) return null;
    for (const key of EDITABLE) {
      if (key in patch) (book as Record<string, unknown>)[key] = patch[key];
    }
    return book;
  });
  return updated ? Response.json(updated) : bad("도서를 찾을 수 없습니다.", 404);
}

export async function DELETE(_req: Request, { params }: Ctx) {
  const { id } = await params;
  const removed = await mutateLibrary((d) => {
    const before = d.books.length;
    d.books = d.books.filter((b) => b.id !== id);
    return d.books.length !== before;
  });
  if (!removed) return bad("도서를 찾을 수 없습니다.", 404);
  await deleteNotes(id);
  return Response.json({ ok: true });
}
