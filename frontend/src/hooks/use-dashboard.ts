"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decide,
  decideContent,
  decideProduct,
  fetchApplications,
  fetchBrokenLinks,
  fetchContent,
  fetchMetricsByContent,
  fetchNeedsReview,
  fetchOrders,
  fetchProductAssetUrl,
  fetchProducts,
  fetchRecentTasks,
  fetchRecommendations,
  markApplicationActive,
  markApplicationApplied,
  markApplicationDeclined,
  proposeProducts,
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
  type ContentItem,
  type ContentMetricRow,
  type Order,
  type Product,
  type Publication,
  type Recommendation,
} from "@/lib/api";

export function useDashboard() {
  const [proposed, setProposed] = useState<Recommendation[]>([]);
  const [approved, setApproved] = useState<Recommendation[]>([]);
  const [rejected, setRejected] = useState<Recommendation[]>([]);
  const [applications, setApplications] = useState<Recommendation[]>([]);
  const [brokenLinks, setBrokenLinks] = useState<AffiliateLink[]>([]);
  const [contentMetrics, setContentMetrics] = useState<ContentMetricRow[]>([]);
  const [content, setContent] = useState<ContentItem[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [needsReview, setNeedsReview] = useState<Publication[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [runningResearch, setRunningResearch] = useState<boolean>(false);
  const [runningContent, setRunningContent] = useState<boolean>(false);
  const [publishing, setPublishing] = useState<boolean>(false);
  const [proposingProducts, setProposingProducts] = useState<boolean>(false);

  const reload = useCallback(async () => {
    const [
      proposedRows,
      approvedRows,
      rejectedRows,
      applicationRows,
      brokenRows,
      metricRows,
      contentRows,
      taskRows,
      reviewRows,
      productRows,
      orderRows,
    ] = await Promise.all([
      fetchRecommendations("proposed"),
      fetchRecommendations("approved"),
      fetchRecommendations("rejected"),
      fetchApplications(),
      fetchBrokenLinks(),
      fetchMetricsByContent(),
      fetchContent(),
      fetchRecentTasks(),
      fetchNeedsReview(),
      fetchProducts(),
      fetchOrders(),
    ]);

    setProposed(proposedRows);
    setApproved(approvedRows);
    setRejected(
      [...rejectedRows].sort((a, b) =>
        (b.updated_at ?? "").localeCompare(a.updated_at ?? ""),
      ),
    );
    setApplications(applicationRows);
    setBrokenLinks(brokenRows);
    setContentMetrics(metricRows);
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

    void init();

    const intervalId = setInterval(() => {
      reload().catch((e: Error) => console.error("Auto-refresh failed: ", e));
    }, 5000);

    return () => clearInterval(intervalId);
  }, [reload]);

  const withBusyAction = async (
    id: string,
    fallbackMessage: string,
    fn: () => Promise<void>,
  ): Promise<boolean> => {
    setBusyId(id);
    setError(null);
    try {
      await fn();
      await reload();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : fallbackMessage);
      return false;
    } finally {
      setBusyId(null);
    }
  };

  const onDecideProgram = (id: string, action: "approve" | "reject") =>
    withBusyAction(id, "decide failed", async () => {
      await decide(id, action);
    });

  const onSaveLink = (id: string, link: string) =>
    withBusyAction(id, "save link failed", async () => {
      await setAffiliateLink(id, link);
    });

  const onMarkApplied = (id: string) =>
    withBusyAction(id, "mark applied failed", async () => {
      await markApplicationApplied(id);
    });

  const onMarkActive = (
    id: string,
    network: string,
    networkProgramId?: string,
  ) =>
    withBusyAction(id, "activate failed", async () => {
      await markApplicationActive(id, network.toLowerCase(), networkProgramId);
    });

  const onMarkDeclined = (id: string) =>
    withBusyAction(id, "mark declined failed", async () => {
      await markApplicationDeclined(id);
    });

  const onRepairLink = (id: string, destinationUrl: string) =>
    withBusyAction(id, "repair link failed", async () => {
      await repairAffiliateLink(id, destinationUrl);
    });

  const onDecideContent = (id: string, action: "approve" | "reject") =>
    withBusyAction(id, "decide failed", async () => {
      await decideContent(id, action);
    });

  const onScheduleContent = (id: string) =>
    withBusyAction(id, "schedule failed", async () => {
      await scheduleContent(id);
    });

  const onResolvePublication = (
    id: string,
    resolution: "published" | "not_published",
    externalId?: string,
  ) =>
    withBusyAction(id, "resolve publication failed", async () => {
      await resolvePublication(id, resolution, externalId);
    });

  const onDecideProduct = (product: Product, action: "approve" | "reject") =>
    withBusyAction(product.id, "Product decision failed", async () => {
      await decideProduct(product.id, action, product.status);
    });

  const onRecordReview = async (
    productId: string,
    reviewer: string,
  ): Promise<boolean> => {
    const trimmed = reviewer.trim();
    if (!trimmed) {
      setError("Reviewer name is required before approving to LIVE");
      return false;
    }
    return withBusyAction(productId, "Review submission failed", async () => {
      await recordProductReview(productId, trimmed);
    });
  };

  const onRetryChapters = (productId: string) =>
    withBusyAction(productId, "Retry chapters failed", async () => {
      await retryProductChapters(productId);
    });

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

  const onProposeProducts = async (niche: string) => {
    const trimmed = niche.trim();
    if (!trimmed) return;
    setProposingProducts(true);
    setError(null);
    try {
      await proposeProducts(trimmed);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Propose failed");
    } finally {
      setProposingProducts(false);
    }
  };

  const onRunResearch = async () => {
    setRunningResearch(true);
    setError(null);
    try {
      await runResearch(5);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "research failed");
    } finally {
      setRunningResearch(false);
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

  return {
    proposed,
    approved,
    rejected,
    applications,
    brokenLinks,
    contentMetrics,
    content,
    tasks,
    products,
    orders,
    needsReview,
    error,
    setError,
    busyId,
    runningResearch,
    runningContent,
    publishing,
    proposingProducts,
    onDecideProgram,
    onSaveLink,
    onMarkApplied,
    onMarkActive,
    onMarkDeclined,
    onRepairLink,
    onDecideContent,
    onScheduleContent,
    onResolvePublication,
    onDecideProduct,
    onRecordReview,
    onRetryChapters,
    onOpenAsset,
    onProposeProducts,
    onRunResearch,
    onRunContent,
    onPublishDue,
  };
}
