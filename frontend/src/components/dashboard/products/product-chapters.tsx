import type { Chapter } from "@/lib/api";
import { chapterStatusBadge } from "@/lib/formatters";

type ProductChaptersProps = {
  chapters: Chapter[];
};

export function ProductChapters({ chapters }: ProductChaptersProps) {
  return (
    <div className="mt-3 space-y-2 border-l-2 border-neutral-200 pl-3">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-700">
        Chapters ({chapters.length})
      </h4>
      {chapters.length === 0 ? (
        <p className="text-xs text-neutral-500">No chapters recorded.</p>
      ) : (
        chapters.map((ch) => (
          <div
            key={ch.id}
            className="space-y-1 rounded border bg-neutral-50/50 p-2 text-xs"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-neutral-800">
                {ch.position}. {ch.title}
              </span>
              <div className="flex items-center gap-2">
                {ch.tokens_used ? (
                  <span className="text-[10px] text-neutral-500">
                    {ch.tokens_used.toLocaleString()} tokens
                  </span>
                ) : null}
                <span
                  className={`rounded border px-1.5 py-0.2 text-[10px] uppercase ${chapterStatusBadge(
                    ch.status,
                  )}`}
                >
                  {ch.status}
                </span>
              </div>
            </div>
            <p className="text-[11px] text-neutral-600">{ch.brief}</p>
            {ch.error ? (
              <p className="rounded bg-red-50 p-1 font-mono text-[10px] text-red-600">
                Error: {ch.error}
              </p>
            ) : null}
          </div>
        ))
      )}
    </div>
  );
}
