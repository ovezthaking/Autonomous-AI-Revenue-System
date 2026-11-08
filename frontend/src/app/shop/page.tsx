"use client";

import Link from "next/link";
import {
  ShopBlockedSection,
  ShopIdeasSection,
  ShopListingsSection,
  ShopOrdersSection,
} from "@/components/shop";
import { useShop } from "@/hooks/use-shop";

export default function ShopPage() {
  const {
    ideas,
    blocked,
    listings,
    orders,
    error,
    busyId,
    handleIdeaDecision,
    handleListingDecision,
  } = useShop();

  return (
    <main className="mx-auto max-w-5xl space-y-8 p-6">
      <div className="flex items-center justify-between border-b pb-4">
        <h1 className="text-2xl font-bold">Sygnały i sklep</h1>
        <Link
          href="/"
          className="rounded border bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200"
        >
          ← Back to Dashboard
        </Link>
      </div>

      {error && (
        <p className="rounded bg-red-100 p-3 text-sm text-red-700">{error}</p>
      )}

      <ShopIdeasSection
        ideas={ideas}
        busyId={busyId}
        onDecideIdea={(id, action) => void handleIdeaDecision(id, action)}
      />

      <ShopBlockedSection blocked={blocked} />

      <ShopListingsSection
        listings={listings}
        busyId={busyId}
        onDecideListing={(id, action) => void handleListingDecision(id, action)}
      />

      <ShopOrdersSection orders={orders} />
    </main>
  );
}
