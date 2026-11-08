import type { ProductListing } from "@/lib/api";

type ShopListingsSectionProps = {
  listings: ProductListing[];
  busyId: string | null;
  onDecideListing: (id: string, action: "approve" | "reject") => void;
};

export function ShopListingsSection({
  listings,
  busyId,
  onDecideListing,
}: ShopListingsSectionProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">Produkty</h2>
      {listings.length === 0 ? (
        <p className="text-sm text-gray-500">Brak produktów w sklepie.</p>
      ) : (
        <ul className="space-y-2">
          {listings.map((listing) => (
            <li
              key={listing.id}
              className="flex items-center justify-between rounded border p-3"
            >
              <div>
                <p className="font-medium">{listing.handle}</p>
                <p className="text-xs text-gray-500">
                  Platforma: {listing.platform} · Status: {listing.status} ·
                  GID: {listing.external_id ?? "-"}
                </p>
              </div>
              {listing.status === "draft" && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busyId === listing.id}
                    onClick={() => onDecideListing(listing.id, "approve")}
                    className="rounded bg-green-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busyId === listing.id}
                    onClick={() => onDecideListing(listing.id, "reject")}
                    className="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
