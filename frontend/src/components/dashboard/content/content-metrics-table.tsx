import type { ContentMetricRow } from "@/lib/api";
import { formatPrice } from "@/lib/formatters";

type ContentMetricsTableProps = {
  contentMetrics: ContentMetricRow[];
};

export function ContentMetricsTable({
  contentMetrics,
}: ContentMetricsTableProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">Revenue by content</h2>
      {contentMetrics.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No content attribution metrics yet.
        </p>
      ) : (
        <div className="overflow-x-auto rounded border bg-white">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-neutral-50 text-neutral-600">
              <tr>
                <th className="px-3 py-2 font-medium">Title</th>
                <th className="px-3 py-2 font-medium">Publication</th>
                <th className="px-3 py-2 text-right font-medium">Clicks</th>
                <th className="px-3 py-2 text-right font-medium">
                  Conversions
                </th>
                <th className="px-3 py-2 text-right font-medium">
                  Affiliate rev.
                </th>
                <th className="px-3 py-2 text-right font-medium">
                  Pending (oczekujące)
                </th>
                <th className="px-3 py-2 text-right font-medium">Own sales</th>
                <th className="px-3 py-2 text-right font-medium">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {contentMetrics.map((row) => (
                <tr key={row.id || row.title}>
                  <td className="px-3 py-2 font-medium text-neutral-900">
                    {row.title}
                  </td>
                  <td className="px-3 py-2 text-neutral-600">
                    {row.publication ? (
                      <a
                        href={row.publication}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="break-all text-blue-600 underline"
                      >
                        {row.publication}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {row.clicks}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {row.conversions}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-semibold text-emerald-700">
                    {formatPrice(row.affiliate_cents)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-amber-700">
                    {formatPrice(row.pending_cents)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-semibold text-indigo-700">
                    {formatPrice(row.own_cents)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-neutral-500">
                    {formatPrice(row.cost_cents)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
