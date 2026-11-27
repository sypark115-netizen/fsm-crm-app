import { readLibrary, writeNote } from "@/lib/store";
import { bad, readJson } from "@/lib/http";
import { NOTE_KINDS, type NoteKind } from "@/lib/types";

type Ctx = { params: Promise<{ id: string; kind: string }> };

/** 요약(short/long) 또는 메모(memo) 마크다운 저장 */
export async function PUT(req: Request, { params }: Ctx) {
  const { id, kind } = await params;
  if (!NOTE_KINDS.includes(kind as NoteKind)) return bad("알 수 없는 노트 종류입니다.");
  const { books } = await readLibrary();
  if (!books.some((b) => b.id === id)) return bad("도서를 찾을 수 없습니다.", 404);
  const body = await readJson<{ content?: unknown }>(req);
  if (typeof body?.content !== "string") return bad("content 문자열이 필요합니다.");
  await writeNote(id, kind as NoteKind, body.content.slice(0, 60000));
  return Response.json({ ok: true });
}
