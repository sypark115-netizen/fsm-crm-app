import { mutateLibrary, newId } from "@/lib/store";
import { bad, readJson, str } from "@/lib/http";

/** 카테고리 추가 */
export async function POST(req: Request) {
  const name = str((await readJson<{ name?: string }>(req))?.name, 40);
  if (!name) return bad("카테고리 이름이 필요합니다.");
  const cat = await mutateLibrary((d) => {
    if (d.categories.some((c) => c.name === name)) return null;
    const c = { id: newId("c-"), name };
    d.categories.push(c);
    return c;
  });
  return cat ? Response.json(cat, { status: 201 }) : bad("이미 있는 카테고리입니다.", 409);
}

/** 카테고리 이름 수정 */
export async function PATCH(req: Request) {
  const body = await readJson<{ id?: string; name?: string }>(req);
  const id = str(body?.id, 60);
  const name = str(body?.name, 40);
  if (!id || !name) return bad("id와 name이 필요합니다.");
  const ok = await mutateLibrary((d) => {
    const c = d.categories.find((c) => c.id === id);
    if (c) c.name = name;
    return !!c;
  });
  return ok ? Response.json({ id, name }) : bad("카테고리를 찾을 수 없습니다.", 404);
}

/** 카테고리 삭제 (책은 남고 해당 분류만 해제) */
export async function DELETE(req: Request) {
  const id = new URL(req.url).searchParams.get("id") ?? "";
  const ok = await mutateLibrary((d) => {
    const before = d.categories.length;
    d.categories = d.categories.filter((c) => c.id !== id);
    d.books.forEach((b) => (b.categoryIds = b.categoryIds.filter((c) => c !== id)));
    return d.categories.length !== before;
  });
  return ok ? Response.json({ ok: true }) : bad("카테고리를 찾을 수 없습니다.", 404);
}
