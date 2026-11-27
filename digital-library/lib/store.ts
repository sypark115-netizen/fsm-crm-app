// 로컬 파일 저장소 (서버 전용)
// - data/books.json : 카테고리·도서 메타·체크리스트·북마크·복습 기록·위시리스트
// - data/notes/{bookId}--{short|long|memo}.md : 2,000자 압축본 / 10,000자 심화본 / 현장 적용 메모
import "server-only";
import { promises as fs } from "fs";
import path from "path";
import { randomUUID } from "crypto";
import type { BookDetail, LibraryData, NoteKind } from "./types";
import { NOTE_KINDS } from "./types";

const DATA_DIR = path.join(process.cwd(), "data");
const BOOKS_FILE = path.join(DATA_DIR, "books.json");
const NOTES_DIR = path.join(DATA_DIR, "notes");

// 동시 요청이 서로의 변경을 덮어쓰지 않도록 쓰기 작업을 한 줄로 세운다.
let queue: Promise<unknown> = Promise.resolve();
function serialize<T>(task: () => Promise<T>): Promise<T> {
  const run = queue.then(task, task);
  queue = run.catch(() => undefined);
  return run;
}

/** 임시 파일에 쓴 뒤 rename → 쓰는 도중 꺼져도 원본이 깨지지 않음 */
async function atomicWrite(file: string, content: string) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${randomUUID()}.tmp`;
  await fs.writeFile(tmp, content, "utf8");
  await fs.rename(tmp, file);
}

export async function readLibrary(): Promise<LibraryData> {
  try {
    const raw = await fs.readFile(BOOKS_FILE, "utf8");
    return JSON.parse(raw) as LibraryData;
  } catch (e: unknown) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return { categories: [], books: [], wishlist: [] };
    }
    throw e;
  }
}

/** 읽기-수정-쓰기를 원자적으로 수행. mutate가 반환한 값을 그대로 돌려준다. */
export function mutateLibrary<T>(mutate: (data: LibraryData) => T | Promise<T>): Promise<T> {
  return serialize(async () => {
    const data = await readLibrary();
    const result = await mutate(data);
    await atomicWrite(BOOKS_FILE, JSON.stringify(data, null, 2) + "\n");
    return result;
  });
}

function notePath(bookId: string, kind: NoteKind) {
  // bookId는 경로 탈출을 막기 위해 안전 문자만 허용
  if (!/^[a-z0-9-]+$/i.test(bookId)) throw new Error("invalid book id");
  return path.join(NOTES_DIR, `${bookId}--${kind}.md`);
}

export async function readNote(bookId: string, kind: NoteKind): Promise<string> {
  try {
    return await fs.readFile(notePath(bookId, kind), "utf8");
  } catch (e: unknown) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return "";
    throw e;
  }
}

export function writeNote(bookId: string, kind: NoteKind, content: string) {
  return serialize(() => atomicWrite(notePath(bookId, kind), content));
}

export function deleteNotes(bookId: string) {
  return serialize(async () => {
    for (const kind of NOTE_KINDS) {
      await fs.rm(notePath(bookId, kind), { force: true });
    }
  });
}

export async function readBookDetail(id: string): Promise<BookDetail | null> {
  const data = await readLibrary();
  const book = data.books.find((b) => b.id === id);
  if (!book) return null;
  const [short, long, memo] = await Promise.all(NOTE_KINDS.map((k) => readNote(id, k)));
  return { ...book, notes: { short, long, memo } };
}

export function newId(prefix = "") {
  return prefix + randomUUID().slice(0, 8);
}

export function slugId(title: string) {
  const ascii = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return (ascii || "book") + "-" + randomUUID().slice(0, 6);
}
