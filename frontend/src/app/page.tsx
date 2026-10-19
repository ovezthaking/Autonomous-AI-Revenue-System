"use client";
/* eslint-disable security/detect-object-injection */

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import {
  decide,
  decideContent,
  decideProduct,
  fetchApplications,
  fetchBrokenLinks,
  fetchContent,
  fetchNeedsReview,
  fetchOrders,
  fetchProductAssetUrl,
  fetchProductChapters,
  fetchProducts,
  fetchRecentTasks,
  fetchRecommendations,
  markApplicationActive,
  markApplicationApplied,
  markApplicationDeclined,
  proposeProducts,
  Publication,
  publishDue,
  recordProductReview,
  repairAffiliateLink,
  resolvePublication,
  retryProductChapters,
  runContent,
  runResearch,
  scheduleContent,
  setAffiliateLink,
  type AffiliateLink,
  type AgentTask,
  type Chapter,
  type ContentItem,
  type Order,
  type Product,
  type Recommendation,
  type ResearchError,
} from "@/lib/api";
import { Button } from "@/components/ui/button";

function taskLabel(tasks: AgentTask[]): string {
  if (tasks.length === 0) return "idle";
  return tasks[0].status;
}

function researchErrors(tasks: AgentTask[]): ResearchError[] {
  const research = tasks.find((task) => task.type === "research_programs");
  const errors = research?.output?.errors;
  if (!Array.isArray(errors)) return [];
  return errors.filter(
    (item) => typeof item?.url === "string" && typeof item?.error === "string",
  );
}

function breakdownLabel(item: Recommendation): string | null {
  const breakdown = item.extras?.score_breakdown;
  if (!breakdown) return null;
  const parts = Object.entries(breakdown).map(
    ([name, points]) => `${name} ${points}`,
  );
  return parts.length > 0 ? parts.join(" · ") : null;
}

function formatPrice(cents: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(cents / 100);
}

function productStatusBadge(status: string) {
  switch (status) {
    case "draft":
      return "bg-neutral-100 text-neutral-800 border-neutral-300";
    case "outlining":
      return "bg-amber-100 text-amber-800 border-amber-300 animate-pulse";
    case "outlined":
      return "bg-blue-100 text-blue-800 border-blue-300";
    case "writing":
      return "bg-yellow-100 text-yellow-800 border-yellow-300 animate-pulse";
    case "assembled":
      return "bg-purple-100 text-purple-800 border-purple-300";
    case "live":
      return "bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold";
    case "archived":
      return "bg-neutral-100 text-neutral-400 border-neutral-200 line-through";
    default:
      return "bg-neutral-100 text-neutral-700 border-neutral-300";
  }
}

function chapterStatusBadge(status: string) {
  switch (status) {
    case "written":
      return "bg-emerald-100 text-emerald-800 border-emerald-300";
    case "failed":
      return "bg-red-100 text-red-800 border-red-300 font-semibold";
    case "pending":
    default:
      return "bg-neutral-100 text-neutral-600 border-neutral-300";
  }
}

export default function DashboardPage() {
  const [proposed, setProposed] = useState<Recommendation[]>([]);
  const [approved, setApproved] = useState<Recommendation[]>([]);
  const [applications, setApplications] = useState<Recommendation[]>([]);
  const [brokenLinks, setBrokenLinks] = useState<AffiliateLink[]>([]);
  const [content, setContent] = useState<ContentItem[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [runningContent, setRunningContent] = useState<boolean>(false);
  const [publishing, setPublishing] = useState<boolean>(false);
  const [linkDrafts, setLinkDrafts] = useState<Record<string, string>>({});
  const [networkDrafts, setNetworkDrafts] = useState<Record<string, string>>(
    {},
  );
  const [programIdDrafts, setProgramIdDrafts] = useState<
    Record<string, string>
  >({});
  const [repairDrafts, setRepairDrafts] = useState<Record<string, string>>({});
  const [needsReview, setNeedsReview] = useState<Publication[]>([]);

  // Products state
  const [productFilter, setProductFilter] = useState<string>("all");
  const [nicheInput, setNicheInput] = useState<string>("crm");
  const [proposingProducts, setProposingProducts] = useState<boolean>(false);
  const [reviewerInputs, setReviewerInputs] = useState<Record<string, string>>(
    {},
  );
  const [expandedChapters, setExpandedChapters] = useState<
    Record<string, Chapter[]>
  >({});
  const [loadingChapters, setLoadingChapters] = useState<
    Record<string, boolean>
  >({});
  const [activeTab, setActiveTab] = useState<
    "all" | "products" | "orders" | "programs" | "content"
  >("all");

  const reload = useCallback(async () => {
    const [
      proposedRows,
      approvedRows,
      applicationRows,
      brokenRows,
      contentRows,
      taskRows,
      reviewRows,
      productRows,
      orderRows,
    ] = await Promise.all([
      fetchRecommendations("proposed"),
      fetchRecommendations("approved"),
      fetchApplications(),
      fetchBrokenLinks(),
      fetchContent(),
      fetchRecentTasks(),
      fetchNeedsReview(),
      fetchProducts(),
      fetchOrders(),
    ]);
    setProposed(proposedRows);
    setApproved(approvedRows);
    setApplications(applicationRows);
    setBrokenLinks(brokenRows);
    setContent(contentRows);
    setTasks(taskRows);
    setNeedsReview(reviewRows);
    setProducts(productRows);
    setOrders(orderRows);
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        await reload();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Błąd ładowania danych");
      }
    };

    init();

    const intervalId = setInterval(() => {
      reload().catch((e: Error) => console.error("Auto-refresh failed: ", e));
    }, 5000);

    return () => clearInterval(intervalId);
  }, [reload]);

  const onDecide = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    setError(null);
    try {
      await decide(id, action);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "decide failed");
    } finally {
      setBusyId(null);
    }
  };

  const onSaveLink = async (item: Recommendation) => {
    setBusyId(item.id);
    setError(null);
    try {
      const link = linkDrafts[item.id] ?? item.affiliate_link ?? "";
      await setAffiliateLink(item.id, link);
      setLinkDrafts((prev) => {
        const next = { ...prev };
        delete next[item.id];
        return next;
      });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "save link failed");
    } finally {
      setBusyId(null);
    }
  };

  const onMarkApplied = async (id: string) => {
    setBusyId(id);
    setError(null);
    try {
      await markApplicationApplied(id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "mark applied failed");
    } finally {
      setBusyId(null);
    }
  };

  const onMarkActive = async (item: Recommendation) => {
    setBusyId(item.id);
    setError(null);
    try {
      const network = (
        networkDrafts[item.id] ??
        item.network ??
        "manual"
      ).toLowerCase();
      const progId =
        programIdDrafts[item.id] ?? item.network_program_id ?? undefined;
      await markApplicationActive(item.id, network, progId);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "activate failed");
    } finally {
      setBusyId(null);
    }
  };

  const onMarkDeclined = async (id: string) => {
    setBusyId(id);
    setError(null);
    try {
      await markApplicationDeclined(id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "mark declined failed");
    } finally {
      setBusyId(null);
    }
  };

  const onRepairLink = async (link: AffiliateLink) => {
    setBusyId(link.id);
    setError(null);
    try {
      const dest = repairDrafts[link.id] ?? link.destination_url;
      await repairAffiliateLink(link.id, dest);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "repair link failed");
    } finally {
      setBusyId(null);
    }
  };

  const onRunResearch = async () => {
    setRunning(true);
    setError(null);
    try {
      await runResearch(5);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "research failed");
    } finally {
      setRunning(false);
    }
  };

  const onRunContent = async () => {
    setRunningContent(true);
    setError(null);
    try {
      await runContent(3);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "content failed");
    } finally {
      setRunningContent(false);
    }
  };

  const onDecideContent = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    setError(null);
    try {
      await decideContent(id, action);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "decide failed");
    } finally {
      setBusyId(null);
    }
  };

  const onSchedule = async (id: string) => {
    setBusyId(id);
    setError(null);
    try {
      await scheduleContent(id);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "schedule failed");
    } finally {
      setBusyId(null);
    }
  };

  const onPublishDue = async () => {
    setPublishing(true);
    setError(null);
    try {
      await publishDue();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "publish failed");
    } finally {
      setPublishing(false);
    }
  };

  // --- Product actions ---
  const onProposeProducts = async () => {
    if (!nicheInput.trim()) return;
    setProposingProducts(true);
    setError(null);
    try {
      await proposeProducts(nicheInput.trim());
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Propose failed");
    } finally {
      setProposingProducts(false);
    }
  };

  const onDecideProduct = async (
    product: Product,
    action: "approve" | "reject",
  ) => {
    setBusyId(product.id);
    setError(null);
    try {
      await decideProduct(product.id, action, product.status);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Product decision failed");
    } finally {
      setBusyId(null);
    }
  };

  const onToggleChapters = async (productId: string) => {
    if (expandedChapters[productId]) {
      setExpandedChapters((prev) => {
        const next = { ...prev };
        delete next[productId];
        return next;
      });
      return;
    }
    setLoadingChapters((prev) => ({ ...prev, [productId]: true }));
    try {
      const chapters = await fetchProductChapters(productId);
      setExpandedChapters((prev) => ({ ...prev, [productId]: chapters }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load chapters");
    } finally {
      setLoadingChapters((prev) => ({ ...prev, [productId]: false }));
    }
  };

  const onRecordReview = async (productId: string) => {
    const reviewer = reviewerInputs[productId]?.trim();
    if (!reviewer) {
      setError("Reviewer name is required before approving to LIVE");
      return;
    }
    setBusyId(productId);
    setError(null);
    try {
      await recordProductReview(productId, reviewer);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review submission failed");
    } finally {
      setBusyId(null);
    }
  };

  const onRetryChapters = async (productId: string) => {
    setBusyId(productId);
    setError(null);
    try {
      await retryProductChapters(productId);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry chapters failed");
    } finally {
      setBusyId(null);
    }
  };

  const onOpenAsset = async (productId: string, assetType: "pdf" | "epub") => {
    setBusyId(productId);
    setError(null);
    try {
      const url = await fetchProductAssetUrl(productId, assetType);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to generate download URL",
      );
    } finally {
      setBusyId(null);
    }
  };

  const errors = researchErrors(tasks);

  const filteredProducts = products.filter((p) => {
    if (productFilter === "all") return true;
    return p.status === productFilter;
  });

  const productCounts: Record<string, number> = {
    all: products.length,
    draft: products.filter((p) => p.status === "draft").length,
    outlined: products.filter((p) => p.status === "outlined").length,
    writing: products.filter((p) => p.status === "writing").length,
    assembled: products.filter((p) => p.status === "assembled").length,
    live: products.filter((p) => p.status === "live").length,
    archived: products.filter((p) => p.status === "archived").length,
  };

  return (
    <main className="mx-auto max-w-4xl space-y-8 p-6 md:p-8">
      {/* Header */}
      <div className="flex flex-col gap-2 border-b pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            HITL Revenue Swarm
          </h1>
          <p className="text-sm text-neutral-500">
            Human-in-the-loop control for autonomous affiliate research, content
            & e-books
          </p>
        </div>
        <div className="text-xs text-neutral-600 sm:text-right">
          <div>
            Last agent task:{" "}
            <strong className="font-semibold">{taskLabel(tasks)}</strong>
          </div>
          {errors.length > 0 ? (
            <span className="mt-1 block text-red-600">
              Research errors:{" "}
              {errors.map((item) => `${item.url} (${item.error})`).join("; ")}
            </span>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          <strong>Error:</strong> {error}
        </div>
      ) : null}

      {/* Main Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b pb-3 text-sm">
        <button
          type="button"
          onClick={() => setActiveTab("all")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeTab === "all"
              ? "bg-neutral-900 text-white font-medium"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
        >
          All Views
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("products")}
          className={`rounded px-3 py-1.5 transition-colors flex items-center gap-1.5 ${
            activeTab === "products"
              ? "bg-neutral-900 text-white font-medium"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
        >
          <span>E-books & Products</span>
          <span className="rounded-full bg-neutral-200 px-1.5 py-0.2 text-xs text-neutral-800">
            {products.length}
          </span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("orders")}
          className={`rounded px-3 py-1.5 transition-colors flex items-center gap-1.5 ${
            activeTab === "orders"
              ? "bg-neutral-900 text-white font-medium"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
        >
          <span>Orders</span>
          <span className="rounded-full bg-neutral-200 px-1.5 py-0.2 text-xs text-neutral-800">
            {orders.length}
          </span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("programs")}
          className={`rounded px-3 py-1.5 transition-colors flex items-center gap-1.5 ${
            activeTab === "programs"
              ? "bg-neutral-900 text-white font-medium"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
        >
          <span>Programs</span>
          <span className="rounded-full bg-neutral-200 px-1.5 py-0.2 text-xs text-neutral-800">
            {proposed.length}
          </span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("content")}
          className={`rounded px-3 py-1.5 transition-colors flex items-center gap-1.5 ${
            activeTab === "content"
              ? "bg-neutral-900 text-white font-medium"
              : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
          }`}
        >
          <span>Content</span>
          <span className="rounded-full bg-neutral-200 px-1.5 py-0.2 text-xs text-neutral-800">
            {content.length}
          </span>
        </button>
      </div>

      {/* Needs review section (Publications) */}
      {(activeTab === "all" || activeTab === "content") &&
      needsReview.length > 0 ? (
        <section className="rounded border border-amber-500 bg-amber-50/40 p-4">
          <h2 className="mb-3 text-base font-semibold text-amber-900">
            Publications needing review ({needsReview.length})
          </h2>
          <ul className="space-y-3">
            {needsReview.map((row: Publication) => (
              <li key={row.id} className="rounded border bg-white p-3 text-sm">
                <div className="font-medium text-neutral-900">
                  {row.target} &bull;{" "}
                  <span className="text-red-600">{row.error}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      resolvePublication(
                        row.id,
                        "published",
                        row.external_id ?? "",
                      )
                    }
                  >
                    Mark Published
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => resolvePublication(row.id, "not_published")}
                  >
                    Not published
                  </Button>
                  {row.external_url ? (
                    <a
                      href={row.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-xs text-blue-600 underline"
                    >
                      Check on WordPress
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* E-BOOKS & PRODUCTS */}
      {activeTab === "all" || activeTab === "products" ? (
        <section className="space-y-4 rounded-lg border bg-neutral-50/60 p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-neutral-900">
                E-books & Digital Products
              </h2>
              <p className="text-xs text-neutral-500">
                Generate topics, approve outlines, inspect chapter progress,
                review and publish to LIVE
              </p>
            </div>
            {/* Propose input bar */}
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
                onClick={onProposeProducts}
              >
                {proposingProducts ? "Proposing..." : "Propose Topics"}
              </Button>
            </div>
          </div>

          {/* Status filter pills */}
          <div className="flex flex-wrap gap-1.5 border-t pt-3 text-xs">
            {(
              [
                ["all", "All"],
                ["draft", "Drafts"],
                ["outlined", "Outlined"],
                ["writing", "Writing"],
                ["assembled", "Assembled"],
                ["live", "Live"],
                ["archived", "Archived"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setProductFilter(key)}
                className={`rounded px-2.5 py-1 transition-colors ${
                  productFilter === key
                    ? "bg-neutral-800 text-white font-medium"
                    : "bg-white border text-neutral-600 hover:bg-neutral-100"
                }`}
              >
                {label} ({productCounts[key] ?? 0})
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
              {filteredProducts.map((p) => {
                const chapters = expandedChapters[p.id];
                const isLoadingChapters = loadingChapters[p.id];
                const hasFailedChapters = chapters?.some(
                  (c) => c.status === "failed",
                );
                const reviewedAt = (p.extras?.reviewed_at as string) || null;
                const reviewedBy = (p.extras?.reviewed_by as string) || null;
                const isBusy = busyId === p.id;

                return (
                  <div
                    key={p.id}
                    className="space-y-3 rounded-lg border bg-white p-4 shadow-sm"
                  >
                    {/* Top Row: Title, Price, Status */}
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-semibold text-neutral-900">
                            {p.title}
                          </h3>
                          <span
                            className={`rounded border px-2 py-0.5 text-xs uppercase tracking-wider ${productStatusBadge(
                              p.status,
                            )}`}
                          >
                            {p.status}
                          </span>
                        </div>
                        {p.subtitle ? (
                          <p className="text-xs text-neutral-600">
                            {p.subtitle}
                          </p>
                        ) : null}
                        <p className="text-xs text-neutral-400">
                          slug: <code className="font-mono">{p.slug}</code>{" "}
                          &bull; {new Date(p.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="text-base font-bold text-neutral-900">
                          {formatPrice(p.price_cents, p.currency)}
                        </div>
                        <span className="text-[10px] text-neutral-400 uppercase tracking-wider">
                          {p.currency}
                        </span>
                      </div>
                    </div>

                    {/* Description / Angle */}
                    {p.description ? (
                      <p className="text-sm text-neutral-700 bg-neutral-50 p-2.5 rounded border border-neutral-100">
                        {p.description}
                      </p>
                    ) : null}

                    {/* Reviewer Audit Banner */}
                    {reviewedAt ? (
                      <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800">
                        ✓ <strong>Human review recorded:</strong> Reviewed by{" "}
                        <span className="font-semibold">
                          {reviewedBy ?? "verified"}
                        </span>{" "}
                        on {new Date(reviewedAt).toLocaleString()}
                      </div>
                    ) : p.status === "assembled" ? (
                      <div className="rounded border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
                        ⚠️ <strong>Human review required:</strong> Read the
                        generated book and record your name below before
                        publishing to LIVE.
                      </div>
                    ) : null}

                    {/* Collapsible Chapters Outline & Progress */}
                    {p.status !== "draft" && p.status !== "outlining" ? (
                      <div className="border-t pt-2">
                        <button
                          type="button"
                          onClick={() => onToggleChapters(p.id)}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 underline flex items-center gap-1"
                        >
                          {chapters
                            ? "Hide Outline / Chapters"
                            : "View Outline & Chapters"}
                          {isLoadingChapters ? " (Loading...)" : ""}
                        </button>

                        {chapters ? (
                          <div className="mt-3 space-y-2 border-l-2 border-neutral-200 pl-3">
                            <h4 className="text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                              Chapters ({chapters.length})
                            </h4>
                            {chapters.length === 0 ? (
                              <p className="text-xs text-neutral-500">
                                No chapters recorded.
                              </p>
                            ) : (
                              chapters.map((ch) => (
                                <div
                                  key={ch.id}
                                  className="rounded border bg-neutral-50/50 p-2 text-xs space-y-1"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="font-semibold text-neutral-800">
                                      {ch.position}. {ch.title}
                                    </span>
                                    <div className="flex items-center gap-2">
                                      {ch.tokens_used ? (
                                        <span className="text-[10px] text-neutral-500">
                                          {ch.tokens_used.toLocaleString()}{" "}
                                          tokens
                                        </span>
                                      ) : null}
                                      <span
                                        className={`rounded border px-1.5 py-0.2 text-[10px] uppercase ${chapterStatusBadge(
                                          ch.status,
                                        )}`}
                                      >
                                        {ch.status}
                                      </span>
                                    </div>
                                  </div>
                                  <p className="text-neutral-600 text-[11px]">
                                    {ch.brief}
                                  </p>
                                  {ch.error ? (
                                    <p className="text-red-600 font-mono text-[10px] bg-red-50 p-1 rounded">
                                      Error: {ch.error}
                                    </p>
                                  ) : null}
                                </div>
                              ))
                            )}
                          </div>
                        ) : null}
                      </div>
                    ) : null}

                    {/* Stage-Specific Actions Bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
                      {/* Left: Download / Preview links if assembled or live */}
                      <div className="flex flex-wrap gap-2">
                        {p.asset_pdf ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={isBusy}
                            onClick={() => onOpenAsset(p.id, "pdf")}
                          >
                            Preview PDF
                          </Button>
                        ) : null}
                        {p.asset_epub ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={isBusy}
                            onClick={() => onOpenAsset(p.id, "epub")}
                          >
                            Download EPUB
                          </Button>
                        ) : null}
                      </div>

                      {/* Right: Decision controls */}
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Draft stage */}
                        {p.status === "draft" ? (
                          <>
                            <Button
                              size="sm"
                              disabled={isBusy}
                              onClick={() => onDecideProduct(p, "approve")}
                            >
                              Approve (Generate Outline)
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={isBusy}
                              onClick={() => onDecideProduct(p, "reject")}
                            >
                              Reject
                            </Button>
                          </>
                        ) : null}

                        {/* Outlining stage */}
                        {p.status === "outlining" ? (
                          <span className="text-xs text-amber-700 italic">
                            Generating outline in background...
                          </span>
                        ) : null}

                        {/* Outlined stage */}
                        {p.status === "outlined" ? (
                          <>
                            <Button
                              size="sm"
                              disabled={isBusy}
                              onClick={() => onDecideProduct(p, "approve")}
                            >
                              Approve (Start Writing)
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={isBusy}
                              onClick={() => onDecideProduct(p, "reject")}
                            >
                              Reject
                            </Button>
                          </>
                        ) : null}

                        {/* Writing stage */}
                        {p.status === "writing" ? (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-neutral-500 italic">
                              Writing chapters...
                            </span>
                            {hasFailedChapters ? (
                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={isBusy}
                                onClick={() => onRetryChapters(p.id)}
                              >
                                Retry Failed Chapters
                              </Button>
                            ) : null}
                          </div>
                        ) : null}

                        {/* Assembled stage */}
                        {p.status === "assembled" ? (
                          <div className="flex flex-wrap items-center gap-2">
                            {!reviewedAt ? (
                              <div className="flex items-center gap-1.5">
                                <input
                                  type="text"
                                  placeholder="Reviewer name"
                                  value={reviewerInputs[p.id] ?? ""}
                                  onChange={(e) =>
                                    setReviewerInputs((prev) => ({
                                      ...prev,
                                      [p.id]: e.target.value,
                                    }))
                                  }
                                  className="rounded border px-2 py-1 text-xs"
                                />
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  disabled={
                                    isBusy || !reviewerInputs[p.id]?.trim()
                                  }
                                  onClick={() => onRecordReview(p.id)}
                                >
                                  Record Review
                                </Button>
                              </div>
                            ) : (
                              <Button
                                size="sm"
                                disabled={isBusy}
                                onClick={() => onDecideProduct(p, "approve")}
                              >
                                Approve to LIVE
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={isBusy}
                              onClick={() => onDecideProduct(p, "reject")}
                            >
                              Reject
                            </Button>
                          </div>
                        ) : null}

                        {/* Live stage */}
                        {p.status === "live" ? (
                          <div className="flex items-center gap-2">
                            <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800">
                              Ready for Sale
                            </span>
                            <Link
                              href={`/p/${p.slug}`}
                              className="rounded border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
                            >
                              Store Page (/p/{p.slug})
                            </Link>
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={isBusy}
                              onClick={() => onDecideProduct(p, "reject")}
                            >
                              Archive
                            </Button>
                          </div>
                        ) : null}

                        {/* Archived */}
                        {p.status === "archived" ? (
                          <span className="text-xs text-neutral-400 italic">
                            Archived
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ) : null}

      {/* ORDERS */}
      {activeTab === "all" || activeTab === "orders" ? (
        <section className="space-y-4 rounded-lg border bg-neutral-50/60 p-5">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">
              Customer Orders &amp; Fulfillment
            </h2>
            <p className="text-xs text-neutral-500">
              Checkout sessions, webhook fulfillment status, and download grants
            </p>
          </div>
          {orders.length === 0 ? (
            <p className="text-sm text-neutral-500">No orders recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {orders.map((order) => {
                const matchedProduct = products.find(
                  (p) => p.id === order.product_id,
                );
                return (
                  <div
                    key={order.id}
                    className="flex flex-col justify-between gap-2 rounded border bg-white p-3 text-xs sm:flex-row sm:items-center"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-neutral-900">
                          {matchedProduct?.title ?? order.product_id}
                        </span>
                        <span className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-[11px] uppercase text-neutral-700">
                          {order.provider}
                        </span>
                        <span
                          className={`rounded px-2 py-0.5 font-medium uppercase ${
                            order.status === "fulfilled"
                              ? "bg-emerald-100 text-emerald-800"
                              : order.status === "refunded"
                                ? "bg-red-100 text-red-800"
                                : order.status === "needs_review"
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-neutral-100 text-neutral-700"
                          }`}
                        >
                          {order.status}
                        </span>
                      </div>
                      <div className="text-neutral-500">
                        Session:{" "}
                        <code className="font-mono">
                          {order.provider_session_id}
                        </code>
                        {order.email ? ` • Buyer: ${order.email}` : ""}
                      </div>
                    </div>
                    <div className="text-right font-mono font-semibold text-neutral-900">
                      {formatPrice(order.amount_cents, order.currency)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ) : null}

      {/* PROPOSED PROGRAMS */}
      {activeTab === "all" || activeTab === "programs" ? (
        <section>
          <h2 className="mb-3 text-lg font-medium">
            Proposed affiliate programs
          </h2>
          {proposed.length === 0 ? (
            <p className="text-sm text-neutral-500">
              No pending recommendations.
            </p>
          ) : null}
          <ul className="space-y-4">
            {proposed.map((item) => {
              const breakdown = breakdownLabel(item);
              return (
                <li key={item.id} className="rounded border bg-white p-4">
                  <div className="flex items-center gap-2">
                    <div className="font-medium">{item.name}</div>
                    {item.score != null ? (
                      <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs font-mono">
                        {item.score}
                      </span>
                    ) : null}
                  </div>
                  {breakdown ? (
                    <p className="text-xs text-neutral-600 mt-1">{breakdown}</p>
                  ) : null}
                  {item.rationale ? (
                    <p className="text-sm mt-1 text-neutral-700">
                      {item.rationale}
                    </p>
                  ) : null}
                  {item.url ? (
                    <a
                      className="text-xs text-blue-600 underline block mt-1"
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {item.url}
                    </a>
                  ) : null}
                  {typeof item.extras?.evidence_url === "string" ? (
                    <a
                      className="block text-xs text-neutral-500 underline mt-0.5"
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
                      onClick={() => onDecide(item.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={busyId === item.id}
                      onClick={() => onDecide(item.id, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {/* APPROVED PROGRAMS */}
      {activeTab === "all" || activeTab === "programs" ? (
        <section>
          <h2 className="mb-3 text-lg font-medium">
            Approved affiliate programs
          </h2>
          {approved.length === 0 ? (
            <p className="text-sm text-neutral-500">No approved programs.</p>
          ) : null}
          <ul className="space-y-4">
            {approved.map((item) => (
              <li key={item.id} className="rounded border bg-white p-4">
                <div className="flex items-center gap-2">
                  <div className="font-medium">{item.name}</div>
                  {item.application_status ? (
                    <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs font-mono">
                      {item.application_status}
                    </span>
                  ) : null}
                </div>
                {item.rationale ? (
                  <p className="text-sm text-neutral-600 mt-1">
                    {item.rationale}
                  </p>
                ) : null}
                <div className="mt-3 flex gap-2">
                  <input
                    type="text"
                    value={linkDrafts[item.id] ?? item.affiliate_link ?? ""}
                    onChange={(event) =>
                      setLinkDrafts((prev) => ({
                        ...prev,
                        [item.id]: event.target.value,
                      }))
                    }
                    placeholder="Affiliate link (manual / fallback)"
                    className="min-w-0 flex-1 rounded border px-2.5 py-1 text-sm"
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busyId === item.id}
                    onClick={() => onSaveLink(item)}
                  >
                    Save link
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* APPLICATIONS PIPELINE (Do zaaplikowania) */}
      {activeTab === "all" || activeTab === "programs" ? (
        <section>
          <h2 className="mb-3 text-lg font-medium">Do zaaplikowania</h2>
          {applications.length === 0 ? (
            <p className="text-sm text-neutral-500">
              Brak programów czekających na aplikację lub akceptację.
            </p>
          ) : null}
          <ul className="space-y-4">
            {applications.map((item) => (
              <li
                key={item.id}
                className="rounded border bg-white p-4 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{item.name}</h3>
                  <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs font-mono">
                    {item.application_status ?? "not_applied"}
                  </span>
                  {item.extras?.needs_reminder ? (
                    <span className="rounded bg-amber-100 text-amber-800 px-2 py-0.5 text-xs font-semibold">
                      Przypomnienie (&gt;14 dni)
                    </span>
                  ) : null}
                </div>
                {item.url ? (
                  <p className="text-xs text-blue-600 underline break-all">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {item.url}
                    </a>
                  </p>
                ) : null}
                {item.rationale ? (
                  <p className="text-sm text-neutral-700">{item.rationale}</p>
                ) : null}
                {item.extras?.facts ? (
                  <p className="text-xs font-mono text-neutral-500">
                    {JSON.stringify(item.extras.facts)}
                  </p>
                ) : null}
                <div className="flex flex-wrap items-center gap-2 pt-2">
                  {item.application_status === "not_applied" ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busyId === item.id}
                      onClick={() => onMarkApplied(item.id)}
                    >
                      Zaaplikowano
                    </Button>
                  ) : null}
                  <select
                    value={
                      networkDrafts[item.id] ??
                      (item.network ? item.network.toLowerCase() : "manual")
                    }
                    onChange={(e) =>
                      setNetworkDrafts((prev) => ({
                        ...prev,
                        [item.id]: e.target.value,
                      }))
                    }
                    className="rounded border px-2 py-1 text-xs"
                  >
                    <option value="manual">manual</option>
                    <option value="awin">awin</option>
                    <option value="impact">impact</option>
                    <option value="cj">cj</option>
                    <option value="amazon">amazon</option>
                  </select>
                  <input
                    type="text"
                    value={
                      programIdDrafts[item.id] ?? item.network_program_id ?? ""
                    }
                    onChange={(e) =>
                      setProgramIdDrafts((prev) => ({
                        ...prev,
                        [item.id]: e.target.value,
                      }))
                    }
                    placeholder="network_program_id"
                    className="rounded border px-2 py-1 text-xs"
                  />
                  <Button
                    size="sm"
                    disabled={busyId === item.id}
                    onClick={() => onMarkActive(item)}
                  >
                    Aktywuj
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={busyId === item.id}
                    onClick={() => onMarkDeclined(item.id)}
                  >
                    Odrzucono
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* BROKEN LINKS (Zepsute linki) */}
      {activeTab === "all" || activeTab === "programs" ? (
        <section>
          <h2 className="mb-3 text-lg font-medium">Zepsute linki</h2>
          {brokenLinks.length === 0 ? (
            <p className="text-sm text-neutral-500">Brak zepsutych linków.</p>
          ) : null}
          <ul className="space-y-3">
            {brokenLinks.map((link) => (
              <li
                key={link.id}
                className="rounded border bg-white p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-600">
                  <span className="font-mono font-semibold">/go/{link.slug}</span>
                  <span>&bull;</span>
                  <span>{link.network}</span>
                  {link.program_name ? (
                    <>
                      <span>&bull;</span>
                      <span>{link.program_name}</span>
                    </>
                  ) : null}
                  {link.content_title ? (
                    <>
                      <span>&bull;</span>
                      <span>{link.content_title}</span>
                    </>
                  ) : null}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={repairDrafts[link.id] ?? link.destination_url}
                    onChange={(e) =>
                      setRepairDrafts((prev) => ({
                        ...prev,
                        [link.id]: e.target.value,
                      }))
                    }
                    className="min-w-0 flex-1 rounded border px-2.5 py-1 text-sm"
                  />
                  <Button
                    size="sm"
                    disabled={busyId === link.id}
                    onClick={() => onRepairLink(link)}
                  >
                    Napraw link
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* CONTENT */}
      {activeTab === "all" || activeTab === "content" ? (
        <section>
          <h2 className="mb-3 text-lg font-medium">Content items</h2>
          {content.length === 0 ? (
            <p className="text-sm text-neutral-500">
              No content generated yet.
            </p>
          ) : null}
          <ul className="space-y-4">
            {content.map((item) => (
              <li
                key={item.id}
                className="rounded border bg-white p-4 space-y-2"
              >
                <div className="font-medium">{item.title}</div>
                <pre className="whitespace-pre-wrap rounded bg-neutral-50 p-2 text-xs font-sans text-neutral-800">
                  {item.body}
                </pre>
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  <span>{item.channel}</span> &bull; <span>{item.status}</span>{" "}
                  &bull; <span>Contains disclosure</span>
                </div>
                {item.status === "draft" ? (
                  <div className="mt-2 flex gap-2">
                    <Button
                      size="sm"
                      disabled={busyId === item.id}
                      onClick={() => onDecideContent(item.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={busyId === item.id}
                      onClick={() => onDecideContent(item.id, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                ) : null}
                {item.status === "approved" ? (
                  <div className="mt-2">
                    <Button
                      size="sm"
                      disabled={busyId === item.id}
                      onClick={() => onSchedule(item.id)}
                    >
                      Schedule
                    </Button>
                  </div>
                ) : null}
                {item.status === "published" ? (
                  <p className="mt-2 text-xs text-neutral-500">
                    Published at: {item.published_at}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Action Triggers Bar */}
      <section className="flex flex-wrap gap-2 border-t pt-4">
        <Button type="button" disabled={running} onClick={onRunResearch}>
          {running ? "Running research..." : "Run research (5)"}
        </Button>
        <Button type="button" disabled={runningContent} onClick={onRunContent}>
          {runningContent ? "Running content..." : "Run content (3)"}
        </Button>
        <Button type="button" disabled={publishing} onClick={onPublishDue}>
          {publishing ? "Publishing..." : "Publish due"}
        </Button>
      </section>
    </main>
  );
}
