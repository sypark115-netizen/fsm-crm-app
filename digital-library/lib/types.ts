// 서재 전체에서 공유하는 데이터 타입

export type Category = {
  id: string;
  name: string;
};

export type ActionItem = {
  id: string;
  text: string;
  done: boolean;
  doneAt?: string | null;
};

export type Highlight = {
  id: string;
  text: string;
  page?: string;
  createdAt: string;
};

export type RelatedBook = {
  title: string;
  author: string;
  reason: string;
};

/** 에빙하우스 복습 단계(등록일 기준 경과일) */
export const REVIEW_STAGES = [1, 3, 7, 30] as const;
export type ReviewStage = (typeof REVIEW_STAGES)[number];

export type Book = {
  id: string;
  title: string;
  originalTitle?: string;
  author: string;
  publisher?: string;
  publishedYear?: string;
  categoryIds: string[];
  coverColor: string;
  registeredAt: string; // YYYY-MM-DD
  background: { era: string; industry: string };
  coreMessages: string[]; // 3줄
  actionItems: ActionItem[];
  highlights: Highlight[];
  reviews: Partial<Record<`${ReviewStage}`, string | null>>; // 완료일 or null
  related: RelatedBook[];
};

export type WishItem = {
  id: string;
  title: string;
  author: string;
  reason: string;
  fromBookId?: string;
  addedAt: string;
};

export type LibraryData = {
  categories: Category[];
  books: Book[];
  wishlist: WishItem[];
};

/** data/notes/{bookId}--{kind}.md */
export const NOTE_KINDS = ["short", "long", "memo"] as const;
export type NoteKind = (typeof NOTE_KINDS)[number];

export type BookDetail = Book & { notes: Record<NoteKind, string> };
