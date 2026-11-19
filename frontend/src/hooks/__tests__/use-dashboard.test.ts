import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import type { Product, Recommendation } from "@/lib/api";
import { useDashboard } from "@/hooks/use-dashboard";

vi.mock("@/lib/api", () => ({
  decide: vi.fn(),
  decideContent: vi.fn(),
  decideProduct: vi.fn(),
  fetchApplications: vi.fn(),
  fetchBrokenLinks: vi.fn(),
  fetchContent: vi.fn(),
  fetchMetricsByContent: vi.fn(),
  fetchNeedsReview: vi.fn(),
  fetchOrders: vi.fn(),
  fetchProductAssetUrl: vi.fn(),
  fetchProducts: vi.fn(),
  fetchRecentTasks: vi.fn(),
  fetchRecommendations: vi.fn(),
  markApplicationActive: vi.fn(),
  markApplicationApplied: vi.fn(),
  markApplicationDeclined: vi.fn(),
  proposeProducts: vi.fn(),
  publishDue: vi.fn(),
  recordProductReview: vi.fn(),
  repairAffiliateLink: vi.fn(),
  resolvePublication: vi.fn(),
  retryProductChapters: vi.fn(),
  runContent: vi.fn(),
  runResearch: vi.fn(),
  scheduleContent: vi.fn(),
  setAffiliateLink: vi.fn(),
}));

const makeRec = (id: string, updated_at?: string | null): Recommendation => ({
  id,
  name: `Program ${id}`,
  url: "https://example.com",
  affiliate_link: null,
  network: "awin",
  category: "saas",
  rationale: "Good",
  extras: null,
  status: "rejected",
  score: 75,
  created_at: "2026-11-01T00:00:00Z",
  updated_at,
});

const dummyProduct: Product = {
  id: "prod-1",
  kind: "ebook",
  slug: "ebook-1",
  title: "Ebook 1",
  subtitle: null,
  description: null,
  price_cents: 1900,
  currency: "USD",
  status: "draft",
  asset_pdf: "ebooks/1.pdf",
  asset_epub: "ebooks/1.epub",
  extras: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

function setupDefaultLoadMocks() {
  vi.mocked(api.fetchRecommendations).mockImplementation(async (status) => {
    if (status === "rejected") {
      return [
        makeRec("r-old", "2026-11-01T00:00:00Z"),
        makeRec("r-null", null),
        makeRec("r-new", "2026-11-05T00:00:00Z"),
      ];
    }
    return [];
  });
  vi.mocked(api.fetchApplications).mockResolvedValue([]);
  vi.mocked(api.fetchBrokenLinks).mockResolvedValue([]);
  vi.mocked(api.fetchMetricsByContent).mockResolvedValue([]);
  vi.mocked(api.fetchContent).mockResolvedValue([]);
  vi.mocked(api.fetchRecentTasks).mockResolvedValue([]);
  vi.mocked(api.fetchNeedsReview).mockResolvedValue([]);
  vi.mocked(api.fetchProducts).mockResolvedValue([dummyProduct]);
  vi.mocked(api.fetchOrders).mockResolvedValue([]);
}

describe("useDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultLoadMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("loads initial data and sorts rejected recommendations by updated_at desc", async () => {
    const { result, unmount } = renderHook(() => useDashboard());

    await waitFor(() => {
      expect(result.current.rejected.map((r) => r.id)).toEqual([
        "r-new",
        "r-old",
        "r-null",
      ]);
    });
    expect(result.current.products).toEqual([dummyProduct]);
    unmount();
  });

  it("handles initial load errors (Error and non-Error) and auto-refresh interval", async () => {
    vi.useFakeTimers();
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    vi.mocked(api.fetchApplications).mockRejectedValueOnce(
      new Error("Init load error"),
    );
    const { result, unmount } = renderHook(() => useDashboard());

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.error).toBe("Init load error");

    // Auto-refresh failure logs to console.error
    vi.mocked(api.fetchApplications).mockRejectedValueOnce(
      new Error("Refresh failed"),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(errSpy).toHaveBeenCalled();
    unmount();

    // Non-Error on initial load
    vi.mocked(api.fetchApplications).mockRejectedValueOnce("string error");
    const { result: res2, unmount: unmount2 } = renderHook(() =>
      useDashboard(),
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(res2.current.error).toBe("Błąd ładowania danych");
    unmount2();
  });

  it("executes all withBusyAction wrappers on success and failure", async () => {
    const { result } = renderHook(() => useDashboard());
    await waitFor(() => expect(result.current.products).toHaveLength(1));

    vi.mocked(api.decide).mockResolvedValueOnce(makeRec("1"));
    expect(
      await act(() => result.current.onDecideProgram("1", "approve")),
    ).toBe(true);
    expect(api.decide).toHaveBeenCalledWith("1", "approve");

    vi.mocked(api.setAffiliateLink).mockResolvedValueOnce(makeRec("1"));
    expect(
      await act(() => result.current.onSaveLink("1", "https://aff.test")),
    ).toBe(true);

    vi.mocked(api.markApplicationApplied).mockResolvedValueOnce(makeRec("1"));
    expect(await act(() => result.current.onMarkApplied("1"))).toBe(true);

    vi.mocked(api.markApplicationActive).mockResolvedValueOnce(makeRec("1"));
    expect(
      await act(() => result.current.onMarkActive("1", "AWIN", "p-1")),
    ).toBe(true);
    expect(api.markApplicationActive).toHaveBeenCalledWith("1", "awin", "p-1");

    vi.mocked(api.markApplicationDeclined).mockResolvedValueOnce(makeRec("1"));
    expect(await act(() => result.current.onMarkDeclined("1"))).toBe(true);

    vi.mocked(api.repairAffiliateLink).mockResolvedValueOnce({} as never);
    expect(
      await act(() => result.current.onRepairLink("l1", "https://dest.test")),
    ).toBe(true);

    vi.mocked(api.decideContent).mockResolvedValueOnce({} as never);
    expect(
      await act(() => result.current.onDecideContent("c1", "approve")),
    ).toBe(true);

    vi.mocked(api.scheduleContent).mockResolvedValueOnce({} as never);
    expect(await act(() => result.current.onScheduleContent("c1"))).toBe(true);

    vi.mocked(api.resolvePublication).mockResolvedValueOnce(undefined);
    expect(
      await act(() =>
        result.current.onResolvePublication("pub1", "published", "ext1"),
      ),
    ).toBe(true);

    vi.mocked(api.decideProduct).mockResolvedValueOnce(dummyProduct);
    expect(
      await act(() => result.current.onDecideProduct(dummyProduct, "approve")),
    ).toBe(true);

    vi.mocked(api.retryProductChapters).mockResolvedValueOnce({
      status: "queued",
    });
    expect(await act(() => result.current.onRetryChapters("prod-1"))).toBe(
      true,
    );

    // Failure with Error instance and non-Error in withBusyAction
    vi.mocked(api.decide).mockRejectedValueOnce(new Error("Boom"));
    expect(await act(() => result.current.onDecideProgram("1", "reject"))).toBe(
      false,
    );
    expect(result.current.error).toBe("Boom");

    vi.mocked(api.decide).mockRejectedValueOnce("raw fail");
    expect(await act(() => result.current.onDecideProgram("1", "reject"))).toBe(
      false,
    );
    expect(result.current.error).toBe("decide failed");
  });

  it("validates reviewer in onRecordReview and opens assets in onOpenAsset", async () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    const { result } = renderHook(() => useDashboard());
    await waitFor(() => expect(result.current.products).toHaveLength(1));

    // Blank reviewer
    expect(
      await act(() => result.current.onRecordReview("prod-1", "   ")),
    ).toBe(false);
    expect(result.current.error).toBe(
      "Reviewer name is required before approving to LIVE",
    );

    // Valid reviewer
    vi.mocked(api.recordProductReview).mockResolvedValueOnce(dummyProduct);
    expect(
      await act(() => result.current.onRecordReview("prod-1", " Alice ")),
    ).toBe(true);
    expect(api.recordProductReview).toHaveBeenCalledWith("prod-1", "Alice");

    // onOpenAsset success, Error, and non-Error
    vi.mocked(api.fetchProductAssetUrl).mockResolvedValueOnce(
      "https://s3.test/1.pdf",
    );
    await act(() => result.current.onOpenAsset("prod-1", "pdf"));
    expect(openSpy).toHaveBeenCalledWith(
      "https://s3.test/1.pdf",
      "_blank",
      "noopener,noreferrer",
    );

    vi.mocked(api.fetchProductAssetUrl).mockRejectedValueOnce(
      new Error("No asset"),
    );
    await act(() => result.current.onOpenAsset("prod-1", "epub"));
    expect(result.current.error).toBe("No asset");

    vi.mocked(api.fetchProductAssetUrl).mockRejectedValueOnce("bad");
    await act(() => result.current.onOpenAsset("prod-1", "epub"));
    expect(result.current.error).toBe("Failed to generate download URL");
  });

  it("handles onProposeProducts, onRunResearch, onRunContent, and onPublishDue", async () => {
    const { result } = renderHook(() => useDashboard());
    await waitFor(() => expect(result.current.products).toHaveLength(1));

    // onProposeProducts empty niche ignored
    await act(() => result.current.onProposeProducts("   "));
    expect(api.proposeProducts).not.toHaveBeenCalled();

    vi.mocked(api.proposeProducts).mockResolvedValueOnce({ status: "queued" });
    await act(() => result.current.onProposeProducts(" AI tools "));
    expect(api.proposeProducts).toHaveBeenCalledWith("AI tools");

    vi.mocked(api.proposeProducts).mockRejectedValueOnce(
      new Error("Propose err"),
    );
    await act(() => result.current.onProposeProducts("AI"));
    expect(result.current.error).toBe("Propose err");

    vi.mocked(api.proposeProducts).mockRejectedValueOnce("raw");
    await act(() => result.current.onProposeProducts("AI"));
    expect(result.current.error).toBe("Propose failed");

    // onRunResearch
    vi.mocked(api.runResearch).mockResolvedValueOnce({} as never);
    await act(() => result.current.onRunResearch());
    expect(api.runResearch).toHaveBeenCalledWith(5);

    vi.mocked(api.runResearch).mockRejectedValueOnce(new Error("Res err"));
    await act(() => result.current.onRunResearch());
    expect(result.current.error).toBe("Res err");

    vi.mocked(api.runResearch).mockRejectedValueOnce("raw");
    await act(() => result.current.onRunResearch());
    expect(result.current.error).toBe("research failed");

    // onRunContent
    vi.mocked(api.runContent).mockResolvedValueOnce({} as never);
    await act(() => result.current.onRunContent());
    expect(api.runContent).toHaveBeenCalledWith(3);

    vi.mocked(api.runContent).mockRejectedValueOnce(new Error("Cnt err"));
    await act(() => result.current.onRunContent());
    expect(result.current.error).toBe("Cnt err");

    vi.mocked(api.runContent).mockRejectedValueOnce("raw");
    await act(() => result.current.onRunContent());
    expect(result.current.error).toBe("content failed");

    // onPublishDue
    vi.mocked(api.publishDue).mockResolvedValueOnce({ status: "ok" });
    await act(() => result.current.onPublishDue());
    expect(api.publishDue).toHaveBeenCalled();

    vi.mocked(api.publishDue).mockRejectedValueOnce(new Error("Pub err"));
    await act(() => result.current.onPublishDue());
    expect(result.current.error).toBe("Pub err");

    vi.mocked(api.publishDue).mockRejectedValueOnce("raw");
    await act(() => result.current.onPublishDue());
    expect(result.current.error).toBe("publish failed");
  });
});
