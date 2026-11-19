import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import type { ProductIdea, ProductListing } from "@/lib/api";
import { useShop } from "@/hooks/use-shop";

vi.mock("@/lib/api", () => ({
  decideIdea: vi.fn(),
  decideListing: vi.fn(),
  fetchIdeas: vi.fn(),
  fetchListings: vi.fn(),
  fetchOrders: vi.fn(),
}));

const sampleIdea: ProductIdea = {
  id: "idea-1",
  term: "budget planner",
  title: "Budget Planner",
  kind: "printable",
  score: 0.9,
  score_breakdown: { demand: 0.5 },
  status: "proposed",
  blocked_reason: null,
  source_task_id: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

const sampleListing: ProductListing = {
  id: "list-1",
  product_id: "prod-1",
  platform: "shopify",
  handle: "rs-budget",
  external_id: "gid://1",
  external_variant_id: "gid://v1",
  status: "draft",
  last_synced_at: null,
  error: null,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

describe("useShop", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchIdeas).mockImplementation(async (status) =>
      status === "proposed" ? [sampleIdea] : [],
    );
    vi.mocked(api.fetchListings).mockResolvedValue([sampleListing]);
    vi.mocked(api.fetchOrders).mockResolvedValue([]);
  });

  it("loads shop data and handles load errors", async () => {
    const { result } = renderHook(() => useShop());

    await waitFor(() => {
      expect(result.current.ideas).toEqual([sampleIdea]);
    });
    expect(result.current.listings).toEqual([sampleListing]);
    expect(result.current.error).toBeNull();

    // Error instance on initial load
    vi.mocked(api.fetchListings).mockRejectedValueOnce(
      new Error("Shop offline"),
    );
    const { result: resErr } = renderHook(() => useShop());
    await waitFor(() => {
      expect(resErr.current.error).toBe("Shop offline");
    });

    // Non-Error on initial load
    vi.mocked(api.fetchListings).mockRejectedValueOnce("raw");
    const { result: resRaw } = renderHook(() => useShop());
    await waitFor(() => {
      expect(resRaw.current.error).toBe("Failed to load shop data");
    });
  });

  it("handles idea and listing decisions on success and failure", async () => {
    const { result } = renderHook(() => useShop());
    await waitFor(() => expect(result.current.ideas).toHaveLength(1));

    // handleIdeaDecision success, Error, non-Error
    vi.mocked(api.decideIdea).mockResolvedValueOnce(sampleIdea);
    await act(() => result.current.handleIdeaDecision("idea-1", "approve"));
    expect(api.decideIdea).toHaveBeenCalledWith("idea-1", "approve");

    vi.mocked(api.decideIdea).mockRejectedValueOnce(new Error("Idea err"));
    await act(() => result.current.handleIdeaDecision("idea-1", "reject"));
    expect(result.current.error).toBe("Idea err");

    vi.mocked(api.decideIdea).mockRejectedValueOnce("raw");
    await act(() => result.current.handleIdeaDecision("idea-1", "reject"));
    expect(result.current.error).toBe("Idea decision failed");

    // handleListingDecision success, Error, non-Error
    vi.mocked(api.decideListing).mockResolvedValueOnce(sampleListing);
    await act(() => result.current.handleListingDecision("list-1", "approve"));
    expect(api.decideListing).toHaveBeenCalledWith("list-1", "approve");

    vi.mocked(api.decideListing).mockRejectedValueOnce(new Error("List err"));
    await act(() => result.current.handleListingDecision("list-1", "reject"));
    expect(result.current.error).toBe("List err");

    vi.mocked(api.decideListing).mockRejectedValueOnce("raw");
    await act(() => result.current.handleListingDecision("list-1", "reject"));
    expect(result.current.error).toBe("Listing decision failed");
  });
});
