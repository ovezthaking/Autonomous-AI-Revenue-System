"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideIdea,
  decideListing,
  fetchIdeas,
  fetchListings,
  fetchOrders,
  type Order,
  type ProductIdea,
  type ProductListing,
} from "@/lib/api";

export default function ShopPage() {
  const [ideas, setIdeas] = useState<Array<ProductIdea>>([]);
  const [blocked, setBlocked] = useState<Array<ProductIdea>>([]);
  const [listings, setListings] = useState<Array<ProductListing>>([]);
  const [orders, setOrders] = useState<Array<Order>>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [proposedData, blockedData, listingsData, ordersData] =
        await Promise.all([
          fetchIdeas("proposed"),
          fetchIdeas("blocked"),
          fetchListings(),
          fetchOrders(),
        ]);
      setIdeas(proposedData);
      setBlocked(blockedData);
      setListings(listingsData);
      setOrders(ordersData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load shop data");
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      await load();
    };
    void init();
  }, [load]);

  const handleIdeaDecision = async (
    id: string,
    action: "approve" | "reject",
  ) => {
    await decideIdea(id, action);
    await load();
  };

  const handleListingDecision = async (
    id: string,
    action: "approve" | "reject",
  ) => {
    await decideListing(id, action);
    await load();
  };

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-6">
      <h1 className="text-2xl font-bold">Sygnały i sklep</h1>
      {error && (
        <p className="rounded bg-red-100 p-3 text-sm text-red-700">{error}</p>
      )}

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
                    onClick={() => void handleIdeaDecision(idea.id, "approve")}
                    className="rounded bg-green-600 px-3 py-1 text-sm text-white"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleIdeaDecision(idea.id, "reject")}
                    className="rounded bg-red-600 px-3 py-1 text-sm text-white"
                  >
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

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
                      onClick={() =>
                        void handleListingDecision(listing.id, "approve")
                      }
                      className="rounded bg-green-600 px-3 py-1 text-sm text-white"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        void handleListingDecision(listing.id, "reject")
                      }
                      className="rounded bg-red-600 px-3 py-1 text-sm text-white"
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

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Zamówienia</h2>
        {orders.length === 0 ? (
          <p className="text-sm text-gray-500">Brak zamówień.</p>
        ) : (
          <ul className="space-y-2">
            {orders.map((order) => (
              <li
                key={order.id}
                className="flex items-center justify-between rounded border p-3 text-sm"
              >
                <span>
                  {order.provider} · {order.email ?? "brak e-maila"} ·{" "}
                  {(order.amount_cents / 100).toFixed(2)} {order.currency}
                </span>
                <span className="font-mono text-xs">{order.status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
