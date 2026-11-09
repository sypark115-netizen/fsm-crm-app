import { AGENTS } from "@/lib/agents";
import type { AuthorId } from "@/lib/types";

const SIZES = { sm: "h-6 w-6 text-[10px]", md: "h-9 w-9 text-xs", lg: "h-10 w-10 text-sm" } as const;

export function Avatar({ author, size = "md", pulse = false }: { author: AuthorId; size?: keyof typeof SIZES; pulse?: boolean }) {
  const a = AGENTS[author];
  return (
    <span className="relative inline-flex shrink-0">
      <span
        className={`${SIZES[size]} ${a.color} inline-flex items-center justify-center rounded-md font-semibold text-white`}
        aria-hidden
      >
        {a.initials}
      </span>
      {pulse && (
        <span className="absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
      )}
    </span>
  );
}
