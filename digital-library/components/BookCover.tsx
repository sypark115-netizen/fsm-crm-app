import type { Book } from "@/lib/types";

/** 이미지 없이 CSS로 그리는 표지 */
export default function BookCover({ book, size = "md" }: { book: Pick<Book, "title" | "author" | "coverColor">; size?: "sm" | "md" | "lg" }) {
  const dims = { sm: "w-12 h-16 text-[9px]", md: "w-full aspect-[3/4] text-sm", lg: "w-32 h-44 text-base" }[size];
  return (
    <div
      className={`${dims} relative rounded-md shadow-md overflow-hidden flex flex-col justify-between p-3 text-white shrink-0`}
      style={{ background: `linear-gradient(160deg, ${book.coverColor}, ${book.coverColor}cc 60%, #00000066)` }}
    >
      <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-black/25" />
      <div className={`font-bold leading-snug ${size === "sm" ? "line-clamp-3" : "line-clamp-4"}`}>{book.title}</div>
      {size !== "sm" && <div className="text-[0.7em] opacity-80 line-clamp-2">{book.author}</div>}
    </div>
  );
}
