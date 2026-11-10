import { profileOf } from "@/lib/agents";
import type { User } from "@/lib/types";

const SIZES = { sm: "h-6 w-6 text-[10px]", md: "h-9 w-9 text-xs", lg: "h-10 w-10 text-sm" } as const;

export function Avatar({
  author,
  users = {},
  size = "md",
  pulse = false,
}: {
  author: string;
  users?: Record<string, User>;
  size?: keyof typeof SIZES;
  pulse?: boolean;
}) {
  const p = profileOf(author, users);
  return (
    <span className="relative inline-flex shrink-0" title={p.name}>
      <span
        className={`${SIZES[size]} ${p.color} inline-flex items-center justify-center font-semibold text-white ${p.isAgent ? "rounded-md" : "rounded-full"}`}
        aria-hidden
      >
        {p.initials}
      </span>
      {pulse && (
        <span className="absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500" />
      )}
    </span>
  );
}
