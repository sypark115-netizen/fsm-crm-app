// 샘플 데이터로 서재를 초기화한다.
//   npm run reset-data
// - data/seed/books.seed.json → data/books.json (복습 날짜를 '오늘' 기준으로 다시 계산)
// - data/seed/notes/*.md      → data/notes/*.md
// 주의: 현재 data/books.json 과 샘플 도서의 노트 파일을 덮어쓴다. 실행 전 백업본을 data/backup-*.json 으로 남긴다.
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = path.join(root, "data");
const seedDir = path.join(dataDir, "seed");

const pad = (n) => String(n).padStart(2, "0");
const dayStr = (daysAgo) => {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const addDays = (s, n) => {
  const [y, m, d] = s.split("-").map(Number);
  const dt = new Date(y, m - 1, d + n);
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`;
};

const seed = JSON.parse(await fs.readFile(path.join(seedDir, "books.seed.json"), "utf8"));

const books = seed.books.map(({ registeredDaysAgo, reviewsDone, ...b }) => {
  const registeredAt = dayStr(registeredDaysAgo);
  const reviews = {};
  for (const s of reviewsDone) reviews[String(s)] = addDays(registeredAt, s); // 제때 복습했다고 가정
  return {
    ...b,
    registeredAt,
    reviews,
    actionItems: b.actionItems.map((a) => ({ ...a, doneAt: a.done ? addDays(registeredAt, 1) : null })),
    highlights: b.highlights.map((h) => ({ ...h, createdAt: registeredAt })),
  };
});
const wishlist = seed.wishlist.map(({ addedDaysAgo, ...w }) => ({ ...w, addedAt: dayStr(addedDaysAgo) }));

const target = path.join(dataDir, "books.json");
try {
  await fs.copyFile(target, path.join(dataDir, `backup-${Date.now()}.json`));
} catch {}
await fs.writeFile(target, JSON.stringify({ categories: seed.categories, books, wishlist }, null, 2) + "\n");

await fs.mkdir(path.join(dataDir, "notes"), { recursive: true });
for (const f of await fs.readdir(path.join(seedDir, "notes"))) {
  await fs.copyFile(path.join(seedDir, "notes", f), path.join(dataDir, "notes", f));
}
console.log(`✓ 샘플 ${books.length}권으로 초기화했습니다 (기준일 ${dayStr(0)}).`);
