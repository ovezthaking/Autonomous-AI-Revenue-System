"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { fetchProductChapters, type Chapter, type Product } from "@/lib/api";
import { formatPrice, productStatusBadge } from "@/lib/formatters";
import { ProductChapters } from "./product-chapters";

type ProductCardProps = {
  product: Product;
  isBusy: boolean;
  onDecideProduct: (product: Product, action: "approve" | "reject") => void;
  onRecordReview: (productId: string, reviewer: string) => void;
  onRetryChapters: (productId: string) => Promise<boolean>;
  onOpenAsset: (productId: string, assetType: "pdf" | "epub") => void;
  onError: (message: string) => void;
};

export function ProductCard({
  product,
  isBusy,
  onDecideProduct,
  onRecordReview,
  onRetryChapters,
  onOpenAsset,
  onError,
}: ProductCardProps) {
  const [chapters, setChapters] = useState<Chapter[] | null>(null);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);
  const [reviewerName, setReviewerName] = useState("");

  const hasFailedChapters =
    chapters?.some((c) => c.status === "failed") ?? false;
  const reviewedAt = (product.extras?.reviewed_at as string) || null;
  const reviewedBy = (product.extras?.reviewed_by as string) || null;

  const handleToggleChapters = async () => {
    if (chapters !== null) {
      setChapters(null);
      return;
    }
    setIsLoadingChapters(true);
    try {
      const loaded = await fetchProductChapters(product.id);
      setChapters(loaded);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load chapters");
    } finally {
      setIsLoadingChapters(false);
    }
  };

  const handleRetryChapters = async () => {
    const ok = await onRetryChapters(product.id);
    if (ok && chapters !== null) {
      try {
        const loaded = await fetchProductChapters(product.id);
        setChapters(loaded);
      } catch {
        // Ignore background chapter refresh error
      }
    }
  };

  return (
    <div className="space-y-3 rounded-lg border bg-white p-4 shadow-sm">
      {/* Top Row: Title, Price, Status */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-neutral-900">
              {product.title}
            </h3>
            <span
              className={`rounded border px-2 py-0.5 text-xs uppercase tracking-wider ${productStatusBadge(
                product.status,
              )}`}
            >
              {product.status}
            </span>
          </div>
          {product.subtitle ? (
            <p className="text-xs text-neutral-600">{product.subtitle}</p>
          ) : null}
          <p className="text-xs text-neutral-400">
            slug: <code className="font-mono">{product.slug}</code> &bull;{" "}
            {new Date(product.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="text-right">
          <div className="text-base font-bold text-neutral-900">
            {formatPrice(product.price_cents, product.currency)}
          </div>
          <span className="text-[10px] uppercase tracking-wider text-neutral-400">
            {product.currency}
          </span>
        </div>
      </div>

      {/* Description / Angle */}
      {product.description ? (
        <p className="rounded border border-neutral-100 bg-neutral-50 p-2.5 text-sm text-neutral-700">
          {product.description}
        </p>
      ) : null}

      {/* Reviewer Audit Banner */}
      {reviewedAt ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800">
          ✓ <strong>Human review recorded:</strong> Reviewed by{" "}
          <span className="font-semibold">{reviewedBy ?? "verified"}</span> on{" "}
          {new Date(reviewedAt).toLocaleString()}
        </div>
      ) : product.status === "assembled" ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
          ⚠️ <strong>Human review required:</strong> Read the generated book and
          record your name below before publishing to LIVE.
        </div>
      ) : null}

      {/* Collapsible Chapters Outline & Progress */}
      {product.status !== "draft" && product.status !== "outlining" ? (
        <div className="border-t pt-2">
          <button
            type="button"
            onClick={() => void handleToggleChapters()}
            className="flex items-center gap-1 text-xs font-medium text-blue-600 underline hover:text-blue-800"
          >
            {chapters !== null
              ? "Hide Outline / Chapters"
              : "View Outline & Chapters"}
            {isLoadingChapters ? " (Loading...)" : ""}
          </button>

          {chapters !== null ? <ProductChapters chapters={chapters} /> : null}
        </div>
      ) : null}

      {/* Stage-Specific Actions Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        {/* Left: Download / Preview links if assembled or live */}
        <div className="flex flex-wrap gap-2">
          {product.asset_pdf ? (
            <Button
              size="sm"
              variant="outline"
              disabled={isBusy}
              onClick={() => onOpenAsset(product.id, "pdf")}
            >
              Preview PDF
            </Button>
          ) : null}
          {product.asset_epub ? (
            <Button
              size="sm"
              variant="outline"
              disabled={isBusy}
              onClick={() => onOpenAsset(product.id, "epub")}
            >
              Download EPUB
            </Button>
          ) : null}
        </div>

        {/* Right: Decision controls */}
        <div className="flex flex-wrap items-center gap-2">
          {product.status === "draft" ? (
            <>
              <Button
                size="sm"
                disabled={isBusy}
                onClick={() => onDecideProduct(product, "approve")}
              >
                Approve (Generate Outline)
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={isBusy}
                onClick={() => onDecideProduct(product, "reject")}
              >
                Reject
              </Button>
            </>
          ) : null}

          {product.status === "outlining" ? (
            <span className="text-xs italic text-amber-700">
              Generating outline in background...
            </span>
          ) : null}

          {product.status === "outlined" ? (
            <>
              <Button
                size="sm"
                disabled={isBusy}
                onClick={() => onDecideProduct(product, "approve")}
              >
                Approve (Start Writing)
              </Button>
              <Button
                size="sm"
                variant="destructive"
                disabled={isBusy}
                onClick={() => onDecideProduct(product, "reject")}
              >
                Reject
              </Button>
            </>
          ) : null}

          {product.status === "writing" ? (
            <div className="flex items-center gap-2">
              <span className="text-xs italic text-neutral-500">
                Writing chapters...
              </span>
              {hasFailedChapters ? (
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={isBusy}
                  onClick={() => void handleRetryChapters()}
                >
                  Retry Failed Chapters
                </Button>
              ) : null}
            </div>
          ) : null}

          {product.status === "assembled" ? (
            <div className="flex flex-wrap items-center gap-2">
              {!reviewedAt ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    placeholder="Reviewer name"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    className="rounded border px-2 py-1 text-xs"
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={isBusy || !reviewerName.trim()}
                    onClick={() => onRecordReview(product.id, reviewerName)}
                  >
                    Record Review
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  disabled={isBusy}
                  onClick={() => onDecideProduct(product, "approve")}
                >
                  Approve to LIVE
                </Button>
              )}
              <Button
                size="sm"
                variant="destructive"
                disabled={isBusy}
                onClick={() => onDecideProduct(product, "reject")}
              >
                Reject
              </Button>
            </div>
          ) : null}

          {product.status === "live" ? (
            <div className="flex items-center gap-2">
              <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800">
                Ready for Sale
              </span>
              <Link
                href={`/p/${product.slug}`}
                className="rounded border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
              >
                Store Page (/p/{product.slug})
              </Link>
              <Button
                size="sm"
                variant="destructive"
                disabled={isBusy}
                onClick={() => onDecideProduct(product, "reject")}
              >
                Archive
              </Button>
            </div>
          ) : null}

          {product.status === "archived" ? (
            <span className="text-xs italic text-neutral-400">Archived</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
