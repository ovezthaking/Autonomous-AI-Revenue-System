import { Button } from "@/components/ui/button";
import type { Publication } from "@/lib/api";

type NeedsReviewSectionProps = {
  needsReview: Publication[];
  busyId: string | null;
  onResolvePublication: (
    id: string,
    resolution: "published" | "not_published",
    externalId?: string,
  ) => void;
};

export function NeedsReviewSection({
  needsReview,
  busyId,
  onResolvePublication,
}: NeedsReviewSectionProps) {
  if (needsReview.length === 0) return null;

  return (
    <section className="rounded border border-amber-500 bg-amber-50/40 p-4">
      <h2 className="mb-3 text-base font-semibold text-amber-900">
        Publications needing review ({needsReview.length})
      </h2>
      <ul className="space-y-3">
        {needsReview.map((row) => (
          <li key={row.id} className="rounded border bg-white p-3 text-sm">
            <div className="font-medium text-neutral-900">
              {row.target} &bull;{" "}
              <span className="text-red-600">{row.error}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={busyId === row.id}
                onClick={() =>
                  onResolvePublication(
                    row.id,
                    "published",
                    row.external_id ?? "",
                  )
                }
              >
                Mark Published
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={busyId === row.id}
                onClick={() => onResolvePublication(row.id, "not_published")}
              >
                Not published
              </Button>
              {row.external_url ? (
                <a
                  href={row.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-xs text-blue-600 underline"
                >
                  Check on WordPress
                </a>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
