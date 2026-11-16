import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API, parse } from "@/lib/api/client";
import {
  decideContent,
  fetchContent,
  fetchMetricsByContent,
  fetchNeedsReview,
  fetchPublications,
  fetchRecentTasks,
  publishDue,
  resolvePublication,
  runContent,
  scheduleContent,
} from "@/lib/api/content";
import {
  consumeDownloadToken,
  createCheckout,
  decideProduct,
  fetchLiveProducts,
  fetchOrderBySession,
  fetchOrders,
  fetchProductAssetUrl,
  fetchProductBySlug,
  fetchProductChapters,
  fetchProducts,
  fetchProductSample,
  proposeProducts,
  recordProductReview,
  retryProductChapters,
  verifyDownloadToken,
} from "@/lib/api/products";
import {
  decide,
  fetchApplications,
  fetchBrokenLinks,
  fetchRecommendations,
  markApplicationActive,
  markApplicationApplied,
  markApplicationDeclined,
  repairAffiliateLink,
  runResearch,
  setAffiliateLink,
} from "@/lib/api/programs";
import {
  decideIdea,
  decideListing,
  fetchIdeas,
  fetchListings,
} from "@/lib/api/shop";

const jsonResponse = (data: unknown, status = 200): Response =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("api modules", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  describe("client", () => {
    it("uses default API url and respects NEXT_PUBLIC_API_URL when set", async () => {
      expect(API).toBe("http://localhost:8000");

      vi.resetModules();
      vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
      const customClient = await import("@/lib/api/client");
      expect(customClient.API).toBe("https://api.example.com");
    });

    it("parses ok response and throws Error on non-ok response", async () => {
      const ok = await parse<{ ok: boolean }>(jsonResponse({ ok: true }));
      expect(ok).toEqual({ ok: true });

      const bad = new Response("Not Found", { status: 404 });
      await expect(parse(bad)).rejects.toThrow("404 Not Found");
    });
  });

  describe("programs", () => {
    it("fetches recommendations with default and custom status", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse([{ id: "r1" }]));
      const resDefault = await fetchRecommendations();
      expect(resDefault).toEqual([{ id: "r1" }]);
      expect(fetchMock).toHaveBeenCalledWith(
        `${API}/recommendations?status=proposed`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchRecommendations("approved");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/recommendations?status=approved`,
        { cache: "no-store" },
      );
    });

    it("sends decide with and without comment", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await decide("r1", "approve");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/recommendations/r1/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ comment: null }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await decide("r1", "reject", "bad terms");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/recommendations/r1/reject`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ comment: "bad terms" }),
        },
      );
    });

    it("runs research with default and custom limit", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "t1" }));
      await runResearch();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/research/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 5 }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "t2" }));
      await runResearch(10);
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/research/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 10 }),
      });
    });

    it("manages affiliate links, applications, and broken links", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await setAffiliateLink("r1", "https://aff.test/1");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/recommendations/r1/affiliate-link`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ affiliate_link: "https://aff.test/1" }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchApplications();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/applications`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await markApplicationApplied("r1");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/applications/r1/applied`,
        { method: "POST" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await markApplicationActive("r1", "awin");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/applications/r1/active`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ network: "awin", network_program_id: null }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await markApplicationActive("r1", "awin", "prog-99");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/applications/r1/active`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            network: "awin",
            network_program_id: "prog-99",
          }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "r1" }));
      await markApplicationDeclined("r1");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/applications/r1/declined`,
        { method: "POST" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchBrokenLinks();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/links?status=broken`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "l1" }));
      await repairAffiliateLink("l1", "https://dest.test");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/links/l1`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ destination_url: "https://dest.test" }),
      });
    });
  });

  describe("content", () => {
    it("handles content, tasks, publications, and metrics endpoints", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchContent();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/content`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchRecentTasks();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/tasks?limit=5`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "t1" }));
      await runContent();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/content/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 3 }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "t2" }));
      await runContent(6);
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/content/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 6 }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "c1" }));
      await decideContent("c1", "approve");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/content/c1/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: null }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "c1" }));
      await scheduleContent("c1");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/content/c1/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ status: "queued" }));
      await publishDue();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/content/publish-due`, {
        method: "POST",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchNeedsReview();
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/publications/needs-review`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchPublications();
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/publications?limit=20`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ ok: true }));
      await resolvePublication("p1", "not_published");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/publications/p1/resolve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            resolution:
              "published" === ("not_published" as string)
                ? "published"
                : "not_published",
            external_id: null,
          }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ ok: true }));
      await resolvePublication("p1", "published", "ext-123");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/publications/p1/resolve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            resolution: "published",
            external_id: "ext-123",
          }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchMetricsByContent();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/metrics/by-content`, {
        cache: "no-store",
      });
    });
  });

  describe("products", () => {
    it("handles product, order, checkout, and download endpoints", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchProducts();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/products`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchProducts("live");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products?status=live`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchProductChapters("pr-1");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/pr-1/chapters`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ status: "queued" }));
      await proposeProducts("saas");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/products/propose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ niche: "saas" }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "pr-1" }));
      await decideProduct("pr-1", "approve", "draft");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/pr-1/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ expected_status: "draft", comment: null }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "pr-1" }));
      await decideProduct("pr-1", "reject", "draft", "not ready");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/pr-1/reject`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            expected_status: "draft",
            comment: "not ready",
          }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "pr-1" }));
      await recordProductReview("pr-1", "Alice");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/pr-1/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reviewer: "Alice" }),
        },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ status: "queued" }));
      await retryProductChapters("pr-1");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/pr-1/retry-chapters`,
        { method: "POST" },
      );

      fetchMock.mockResolvedValueOnce(
        jsonResponse({ url: "https://s3.test/book.pdf" }),
      );
      const assetUrl = await fetchProductAssetUrl("pr-1", "pdf");
      expect(assetUrl).toBe("https://s3.test/book.pdf");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/pr-1/asset-url?asset_type=pdf`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchOrders();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/orders`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(
        jsonResponse({ id: "o1", status: "fulfilled" }),
      );
      await fetchOrderBySession("sess-1");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/orders/by-session/sess-1`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchLiveProducts();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/products/live`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "pr-1" }));
      await fetchProductBySlug("my-book");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/by-slug/my-book`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(
        jsonResponse({
          slug: "my-book",
          title: "My Book",
          chapters: [],
          sample_chapter: null,
        }),
      );
      await fetchProductSample("my-book");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/products/by-slug/my-book/sample`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(
        jsonResponse({ url: "https://pay.test", session_id: "s1" }),
      );
      await createCheckout("my-book");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: "my-book",
          consent_immediate_delivery: true,
          source: null,
        }),
      });

      fetchMock.mockResolvedValueOnce(
        jsonResponse({ url: "https://pay.test", session_id: "s2" }),
      );
      await createCheckout("my-book", false, "blog-1");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: "my-book",
          consent_immediate_delivery: false,
          source: "blog-1",
        }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ status: "valid" }));
      await verifyDownloadToken("tok-1");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/download/tok-1`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(
        jsonResponse({
          url: "https://s3.test/dl",
          downloads_used: 1,
          max_downloads: 5,
          remaining_downloads: 4,
        }),
      );
      await consumeDownloadToken("tok-1");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/download/tok-1`, {
        method: "POST",
        headers: { Accept: "application/json" },
      });
    });
  });

  describe("shop", () => {
    it("handles ideas and listings endpoints", async () => {
      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchIdeas();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/ideas`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchIdeas("proposed");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/ideas?status=proposed`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "i1" }));
      await decideIdea("i1", "approve");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/ideas/i1/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: null }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "i1" }));
      await decideIdea("i1", "reject", "duplicate");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/ideas/i1/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: "duplicate" }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchListings();
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/listings`, {
        cache: "no-store",
      });

      fetchMock.mockResolvedValueOnce(jsonResponse([]));
      await fetchListings("draft");
      expect(fetchMock).toHaveBeenLastCalledWith(
        `${API}/listings?status=draft`,
        { cache: "no-store" },
      );

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "l1" }));
      await decideListing("l1", "approve");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/listings/l1/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: null }),
      });

      fetchMock.mockResolvedValueOnce(jsonResponse({ id: "l1" }));
      await decideListing("l1", "reject", "bad price");
      expect(fetchMock).toHaveBeenLastCalledWith(`${API}/listings/l1/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: "bad price" }),
      });
    });
  });
});
