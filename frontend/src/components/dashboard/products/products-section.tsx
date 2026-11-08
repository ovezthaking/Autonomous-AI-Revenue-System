"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Product } from "@/lib/api";
import { ProductCard } from "./product-card";

type ProductsSectionProps = {
  products: Product[];
  busyId: string | null;
  proposingProducts: boolean;
  onProposeProducts: (niche: string) => void;
  onDecideProduct: (product: Product, action: "approve" | "reject") => void;
  onRecordReview: (productId: string, reviewer: string) => void;
  onRetryChapters: (productId: string) => Promise<boolean>;
  onOpenAsset: (productId: string, assetType: "pdf" | "epub") => void;
  onError: (message: string) => void;
};

export function ProductsSection({
  products,
  busyId,
  proposingProducts,
  onProposeProducts,
  onDecideProduct,
  onRecordReview,
  onRetryChapters,
  onOpenAsset,
  onError,
}: ProductsSectionProps) {
  const [productFilter, setProductFilter] = useState<string>("all");
  const [nicheInput, setNicheInput] = useState<string>("crm");

  const filterOptions = [
    { key: "all", label: "All", count: products.length },
    {
      key: "draft",
      label: "Drafts",
      count: products.filter((p) => p.status === "draft").length,
    },
    {
      key: "outlined",
      label: "Outlined",
      count: products.filter((p) => p.status === "outlined").length,
    },
    {
      key: "writing",
      label: "Writing",
      count: products.filter((p) => p.status === "writing").length,
    },
    {
      key: "assembled",
      label: "Assembled",
      count: products.filter((p) => p.status === "assembled").length,
    },
    {
      key: "live",
      label: "Live",
      count: products.filter((p) => p.status === "live").length,
    },
    {
      key: "archived",
      label: "Archived",
      count: products.filter((p) => p.status === "archived").length,
    },
  ];

  const filteredProducts = products.filter((p) =>
    productFilter === "all" ? true : p.status === productFilter,
  );

  return (
    <section className="space-y-4 rounded-lg border bg-neutral-50/60 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900">
            E-books &amp; Digital Products
          </h2>
          <p className="text-xs text-neutral-500">
            Generate topics, approve outlines, inspect chapter progress, review
            and publish to LIVE
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={nicheInput}
            onChange={(e) => setNicheInput(e.target.value)}
            placeholder="Niche (e.g. crm, dev tools)"
            className="w-48 rounded border bg-white px-2.5 py-1 text-sm outline-none focus:border-neutral-800"
          />
          <Button
            type="button"
            disabled={proposingProducts || !nicheInput.trim()}
            onClick={() => onProposeProducts(nicheInput)}
          >
            {proposingProducts ? "Proposing..." : "Propose Topics"}
          </Button>
        </div>
      </div>

      {/* Status filter pills */}
      <div className="flex flex-wrap gap-1.5 border-t pt-3 text-xs">
        {filterOptions.map(({ key, label, count }) => (
          <button
            key={key}
            type="button"
            onClick={() => setProductFilter(key)}
            className={`rounded px-2.5 py-1 transition-colors ${
              productFilter === key
                ? "bg-neutral-800 font-medium text-white"
                : "border bg-white text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            {label} ({count})
          </button>
        ))}
      </div>

      {/* Products List */}
      {filteredProducts.length === 0 ? (
        <div className="rounded border border-dashed bg-white p-6 text-center text-sm text-neutral-500">
          No products found in this category. Use{" "}
          <strong>Propose Topics</strong> above to start.
        </div>
      ) : (
        <div className="space-y-4">
          {filteredProducts.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              isBusy={busyId === product.id}
              onDecideProduct={onDecideProduct}
              onRecordReview={onRecordReview}
              onRetryChapters={onRetryChapters}
              onOpenAsset={onOpenAsset}
              onError={onError}
            />
          ))}
        </div>
      )}
    </section>
  );
}
