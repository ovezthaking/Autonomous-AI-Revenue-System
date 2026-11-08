import type { Recommendation } from "@/lib/api";

type RejectedProgramsSectionProps = {
  rejected: Recommendation[];
};

export function RejectedProgramsSection({
  rejected,
}: RejectedProgramsSectionProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">Rejected programs</h2>
      {rejected.length === 0 ? (
        <p className="text-sm text-neutral-500">No rejected programs.</p>
      ) : null}
      <ul className="space-y-4">
        {rejected.map((item) => (
          <li key={item.id} className="rounded border bg-white p-4">
            <div className="font-medium">{item.name}</div>
            {item.rationale ? (
              <p className="mt-1 text-sm text-neutral-600">{item.rationale}</p>
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
          </li>
        ))}
      </ul>
    </section>
  );
}
