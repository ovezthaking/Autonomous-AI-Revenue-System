import type { ProductIdea } from "@/lib/api";

type ShopBlockedSectionProps = {
  blocked: ProductIdea[];
};

export function ShopBlockedSection({ blocked }: ShopBlockedSectionProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">Zablokowane</h2>
      {blocked.length === 0 ? (
        <p className="text-sm text-gray-500">Brak zablokowanych fraz.</p>
      ) : (
        <ul className="space-y-2">
          {blocked.map((idea) => (
            <li
              key={idea.id}
              className="flex items-center justify-between rounded border bg-gray-50 p-3"
            >
              <div>
                <p className="font-medium">{idea.term}</p>
                <p className="text-xs text-red-600">
                  Powód: {idea.blocked_reason ?? "blocked"}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
