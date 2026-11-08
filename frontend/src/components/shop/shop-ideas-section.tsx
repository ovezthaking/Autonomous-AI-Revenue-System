import type { ProductIdea } from "@/lib/api";

type ShopIdeasSectionProps = {
  ideas: ProductIdea[];
  busyId: string | null;
  onDecideIdea: (id: string, action: "approve" | "reject") => void;
};

export function ShopIdeasSection({
  ideas,
  busyId,
  onDecideIdea,
}: ShopIdeasSectionProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">Pomysły</h2>
      {ideas.length === 0 ? (
        <p className="text-sm text-gray-500">Brak oczekujących pomysłów.</p>
      ) : (
        <ul className="space-y-2">
          {ideas.map((idea) => (
            <li
              key={idea.id}
              className="flex items-center justify-between rounded border p-3"
            >
              <div>
                <p className="font-medium">{idea.title}</p>
                <p className="text-xs text-gray-500">
                  Kind: {idea.kind} · Score: {idea.score.toFixed(2)} (
                  {JSON.stringify(idea.score_breakdown)})
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busyId === idea.id}
                  onClick={() => onDecideIdea(idea.id, "approve")}
                  className="rounded bg-green-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={busyId === idea.id}
                  onClick={() => onDecideIdea(idea.id, "reject")}
                  className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
