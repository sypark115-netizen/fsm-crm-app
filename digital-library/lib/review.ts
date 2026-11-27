// 에빙하우스 복습 스케줄 계산 (클라이언트/서버 공용 순수 함수)
import type { Book, ReviewStage } from "./types";
import { REVIEW_STAGES } from "./types";

const DAY = 24 * 60 * 60 * 1000;

/** 'YYYY-MM-DD' → 로컬 자정 기준 Date */
function parseDate(d: string) {
  const [y, m, day] = d.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, day);
}

export function todayStr(now = new Date()) {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function daysSince(dateStr: string, now = new Date()) {
  return Math.floor((parseDate(todayStr(now)).getTime() - parseDate(dateStr).getTime()) / DAY);
}

export function dueDate(registeredAt: string, stage: ReviewStage) {
  return todayStr(new Date(parseDate(registeredAt).getTime() + stage * DAY));
}

export type ReviewTask = {
  book: Book;
  stage: ReviewStage;
  dueOn: string;
  overdueDays: number; // 0 = 오늘이 복습일
};

/**
 * 책마다 '도래했지만 아직 완료하지 않은 가장 이른 단계' 하나를 복습 대상으로 낸다.
 * (여러 단계가 밀려 있어도 한 번에 하나씩 처리하도록)
 */
export function getDueReviews(books: Book[], now = new Date()): ReviewTask[] {
  const elapsed = (b: Book) => daysSince(b.registeredAt, now);
  const tasks: ReviewTask[] = [];
  for (const book of books) {
    const days = elapsed(book);
    const stage = REVIEW_STAGES.find((s) => days >= s && !book.reviews?.[`${s}`]);
    if (stage) tasks.push({ book, stage, dueOn: dueDate(book.registeredAt, stage), overdueDays: days - stage });
  }
  return tasks.sort((a, b) => b.overdueDays - a.overdueDays);
}

/** 아직 도래하지 않은 다음 복습 */
export function getUpcomingReviews(books: Book[], now = new Date(), withinDays = 7) {
  const out: { book: Book; stage: ReviewStage; dueOn: string; inDays: number }[] = [];
  for (const book of books) {
    const days = daysSince(book.registeredAt, now);
    const next = REVIEW_STAGES.find((s) => s > days && !book.reviews?.[`${s}`]);
    if (next && next - days <= withinDays) {
      out.push({ book, stage: next, dueOn: dueDate(book.registeredAt, next), inDays: next - days });
    }
  }
  return out.sort((a, b) => a.inDays - b.inDays);
}

export function reviewProgress(book: Book) {
  return REVIEW_STAGES.filter((s) => book.reviews?.[`${s}`]).length;
}
