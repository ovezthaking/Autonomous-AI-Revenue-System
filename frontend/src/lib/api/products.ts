import { API, parse } from "./client";
import type {
  Chapter,
  DownloadVerification,
  Order,
  Product,
  ProductSample,
} from "./types";

export const fetchProducts = async (
  status?: string,
): Promise<Array<Product>> => {
  const url = status
    ? `${API}/products?status=${encodeURIComponent(status)}`
    : `${API}/products`;
  const res = await fetch(url, { cache: "no-store" });
  return parse<Array<Product>>(res);
};

export const fetchProductChapters = async (
  productId: string,
): Promise<Array<Chapter>> => {
  const res = await fetch(`${API}/products/${productId}/chapters`, {
    cache: "no-store",
  });
  return parse<Array<Chapter>>(res);
};

export const proposeProducts = async (
  niche: string,
): Promise<{ status: string }> => {
  const res = await fetch(`${API}/products/propose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ niche }),
  });
  return parse<{ status: string }>(res);
};

export const decideProduct = async (
  id: string,
  action: "approve" | "reject",
  expectedStatus: string,
  comment?: string,
): Promise<Product> => {
  const res = await fetch(`${API}/products/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      expected_status: expectedStatus,
      comment: comment ?? null,
    }),
  });
  return parse<Product>(res);
};

export const recordProductReview = async (
  id: string,
  reviewer: string,
): Promise<Product> => {
  const res = await fetch(`${API}/products/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer }),
  });
  return parse<Product>(res);
};

export const retryProductChapters = async (
  id: string,
): Promise<{ status: string }> => {
  const res = await fetch(`${API}/products/${id}/retry-chapters`, {
    method: "POST",
  });
  return parse<{ status: string }>(res);
};

export const fetchProductAssetUrl = async (
  id: string,
  assetType: "pdf" | "epub",
): Promise<string> => {
  const res = await fetch(
    `${API}/products/${id}/asset-url?asset_type=${encodeURIComponent(assetType)}`,
    { cache: "no-store" },
  );
  const data = await parse<{ url: string }>(res);
  return data.url;
};

export const fetchOrders = async (): Promise<Array<Order>> => {
  const res = await fetch(`${API}/orders`, { cache: "no-store" });
  return parse<Array<Order>>(res);
};

export const fetchOrderBySession = async (
  sessionId: string,
): Promise<{ id: string; status: string }> => {
  const res = await fetch(
    `${API}/orders/by-session/${encodeURIComponent(sessionId)}`,
    { cache: "no-store" },
  );
  return parse<{ id: string; status: string }>(res);
};

export const fetchLiveProducts = async (): Promise<Array<Product>> => {
  const res = await fetch(`${API}/products/live`, { cache: "no-store" });
  return parse<Array<Product>>(res);
};

export const fetchProductBySlug = async (slug: string): Promise<Product> => {
  const res = await fetch(
    `${API}/products/by-slug/${encodeURIComponent(slug)}`,
    { cache: "no-store" },
  );
  return parse<Product>(res);
};

export const fetchProductSample = async (
  slug: string,
): Promise<ProductSample> => {
  const res = await fetch(
    `${API}/products/by-slug/${encodeURIComponent(slug)}/sample`,
    { cache: "no-store" },
  );
  return parse<ProductSample>(res);
};

export const createCheckout = async (
  slug: string,
  consentImmediateDelivery: boolean = true,
  source?: string | null,
): Promise<{ url: string; session_id: string }> => {
  const res = await fetch(`${API}/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      slug,
      consent_immediate_delivery: consentImmediateDelivery,
      source: source ?? null,
    }),
  });
  return parse<{ url: string; session_id: string }>(res);
};

export const verifyDownloadToken = async (
  token: string,
): Promise<DownloadVerification> => {
  const res = await fetch(`${API}/download/${encodeURIComponent(token)}`, {
    cache: "no-store",
  });
  return parse<DownloadVerification>(res);
};

export const consumeDownloadToken = async (
  token: string,
): Promise<{
  url: string;
  downloads_used: number;
  max_downloads: number;
  remaining_downloads: number;
}> => {
  const res = await fetch(`${API}/download/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  return parse<{
    url: string;
    downloads_used: number;
    max_downloads: number;
    remaining_downloads: number;
  }>(res);
};
