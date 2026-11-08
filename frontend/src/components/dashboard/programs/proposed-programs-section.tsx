import { Button } from "@/components/ui/button";
import type { Recommendation } from "@/lib/api";
import { breakdownLabel } from "@/lib/formatters";

type ProposedProgramsSectionProps = {
  proposed: Recommendation[];
  busyId: string | null;
  onDecideProgram: (id: string, action: "approve" | "reject") => void;
};

export function ProposedProgramsSection({
  proposed,
  busyId,
  onDecideProgram,
}: ProposedProgramsSectionProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">Proposed affiliate programs</h2>
      {proposed.length === 0 ? (
        <p className="text-sm text-neutral-500">No pending recommendations.</p>
      ) : null}
      <ul className="space-y-4">
        {proposed.map((item) => {
          const breakdown = breakdownLabel(item);
          return (
            <li key={item.id} className="rounded border bg-white p-4">
              <div className="flex items-center gap-2">
                <div className="font-medium">{item.name}</div>
                {item.score != null ? (
                  <span className="rounded bg-neutral-100 px-2 py-0.5 font-mono text-xs">
                    {item.score}
                  </span>
                ) : null}
              </div>
              {breakdown ? (
                <p className="mt-1 text-xs text-neutral-600">{breakdown}</p>
              ) : null}
              {item.rationale ? (
                <p className="mt-1 text-sm text-neutral-700">
                  {item.rationale}
                </p>
              ) : null}
              {item.url ? (
                <a
                  className="mt-1 block text-xs text-blue-600 underline"
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {item.url}
                </a>
              ) : null}
              {typeof item.extras?.evidence_url === "string" ? (
                <a
                  className="mt-0.5 block text-xs text-neutral-500 underline"
                  href={item.extras.evidence_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  evidence source
                </a>
              ) : null}
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  disabled={busyId === item.id}
                  onClick={() => onDecideProgram(item.id, "approve")}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={busyId === item.id}
                  onClick={() => onDecideProgram(item.id, "reject")}
                >
                  Reject
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
