import { mutateLibrary, newId } from "@/lib/store";
import { bad, readJson, str } from "@/lib/http";
import { todayStr } from "@/lib/review";

/** 읽을 책(위시리스트) 추가 — 같은 제목은 중복 추가하지 않음 */
export async function POST(req: Request) {
  const body = await readJson<Record<string, unknown>>(req);
  const title = str(body?.title, 200);
  if (!title) return bad("제목이 필요합니다.");
  const item = await mutateLibrary((d) => {
    const exists = d.wishlist.find((w) => w.title === title);
    if (exists) return exists;
    const w = {
      id: newId("w-"),
      title,
      author: str(body?.author, 200),
      reason: str(body?.reason, 1000),
      fromBookId: str(body?.fromBookId, 80) || undefined,
      addedAt: todayStr(),
    };
    d.wishlist.unshift(w);
    return w;
  });
  return Response.json(item, { status: 201 });
}

export async function DELETE(req: Request) {
  const id = new URL(req.url).searchParams.get("id") ?? "";
  await mutateLibrary((d) => {
    d.wishlist = d.wishlist.filter((w) => w.id !== id);
  });
  return Response.json({ ok: true });
}
