const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ScoreBreakdown = Record<string, number>;

export type RecommendationExtras = {
  evidence_url?: string | null;
  score_breakdown?: ScoreBreakdown | null;
  facts?: Record<string, unknown> | null;
  needs_reminder?: boolean;
  declined_until?: string | null;
};

export type ResearchError = {
  url: string;
  error: string;
};

export type Recommendation = {
  id: string;
  name: string;
  url: string | null;
  affiliate_link: string | null;
  network: string | null;
  network_program_id?: string | null;
  application_status?: string;
  applied_at?: string | null;
  activated_at?: string | null;
  allow_redirect?: boolean;
  category: string | null;
  rationale: string | null;
  extras: RecommendationExtras | null;
  status: string;
  score: number | null;
  source_task_id?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type AffiliateLink = {
  id: string;
  program_id: string;
  program_name: string | null;
  content_item_id: string | null;
  content_title: string | null;
  destination_url: string;
  tracking_url: string;
  slug: string;
  subid: string;
  network: string;
  status: string;
  last_checked_at: string | null;
  created_at: string;
};

export type ContentItem = {
  id: string;
  affiliate_program_id: string | null;
  title: string;
  body: string;
  channel: string;
  status: string;
  scheduled_for: string | null;
  published_at: string | null;
  created_at: string;
};

export type AgentTask = {
  id: string;
  type: string;
  status: string;
  output: {
    text?: string;
    errors?: ResearchError[];
  } | null;
  error: string | null;
  created_at: string;
};

export type Publication = {
  id: string;
  content_item_id: string;
  target: string;
  status: string;
  attempts: number;
  external_id: string | null;
  external_url: string | null;
  error: string | null;
  updated_at: string;
};

export type Product = {
  id: string;
  kind: string;
  slug: string;
  title: string;
  subtitle: string | null;
  description: string | null;
  price_cents: number;
  currency: string;
  status: string;
  asset_pdf: string | null;
  asset_epub: string | null;
  extras: Record<string, unknown> | null;
  updated_at: string;
  created_at: string;
};

export type Chapter = {
  id: string;
  position: number;
  title: string;
  brief: string;
  status: string;
  error: string | null;
  tokens_used: number | null;
};

const parse = async <T>(res: Response): Promise<T> => {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
};

export const fetchRecommendations = async (
  status: string = "proposed",
): Promise<Array<Recommendation>> => {
  const res = await fetch(
    `${API}/recommendations?status=${encodeURIComponent(status)}`,
    { cache: "no-store" },
  );
  return parse<Array<Recommendation>>(res);
};

export const fetchContent = async (): Promise<Array<ContentItem>> => {
  const res = await fetch(`${API}/content`, { cache: "no-store" });
  return parse<Array<ContentItem>>(res);
};

export const fetchRecentTasks = async (): Promise<Array<AgentTask>> => {
  const res = await fetch(`${API}/tasks?limit=5`, { cache: "no-store" });
  return parse<Array<AgentTask>>(res);
};

export const decide = async (
  id: string,
  action: "approve" | "reject",
  comment?: string,
): Promise<Recommendation> => {
  const res = await fetch(`${API}/recommendations/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment: comment ?? null }),
  });
  return parse<Recommendation>(res);
};

export const runResearch = async (limit = 5): Promise<AgentTask> => {
  const res = await fetch(`${API}/research/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ limit }),
  });
  return parse<AgentTask>(res);
};

export const setAffiliateLink = async (id: string, link: string) => {
  const res = await fetch(`${API}/recommendations/${id}/affiliate-link`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ affiliate_link: link }),
  });
  return parse<Recommendation>(res);
};

export const runContent = async (limit = 3) => {
  const res = await fetch(`${API}/content/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ limit }),
  });
  return parse<AgentTask>(res);
};

export const decideContent = async (
  id: string,
  action: "approve" | "reject",
) => {
  const res = await fetch(`${API}/content/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment: null }),
  });
  return parse<ContentItem>(res);
};

export const scheduleContent = async (id: string) => {
  const res = await fetch(`${API}/content/${id}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return parse<ContentItem>(res);
};

export const publishDue = async () => {
  const res = await fetch(`${API}/content/publish-due`, { method: "POST" });
  return parse<{ status: string }>(res);
};

export const fetchNeedsReview = async (): Promise<Array<Publication>> => {
  const res = await fetch(`${API}/publications/needs-review`, {
    cache: "no-store",
  });
  return parse<Array<Publication>>(res);
};

export const fetchPublications = async (): Promise<Array<Publication>> => {
  const res = await fetch(`${API}/publications?limit=20`, {
    cache: "no-store",
  });
  return parse<Array<Publication>>(res);
};

export const resolvePublication = async (
  id: string,
  resolution: "published" | "not_published",
  externalId?: string,
): Promise<void> => {
  const res = await fetch(`${API}/publications/${id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resolution,
      external_id: externalId ?? null,
    }),
  });
  await parse(res);
};

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

export type Order = {
  id: string;
  product_id: string;
  provider: string;
  provider_session_id: string;
  provider_payment_id: string | null;
  email: string | null;
  amount_cents: number;
  currency: string;
  status: string;
  consent_immediate_delivery: boolean;
  fulfilled_at: string | null;
  extras: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type ProductSample = {
  slug: string;
  title: string;
  chapters: Array<{ position: number; title: string; brief: string }>;
  sample_chapter: {
    position: number;
    title: string;
    body: string;
  } | null;
};

export type DownloadVerification = {
  status: string;
  title: string;
  slug: string;
  downloads_used: number;
  max_downloads: number;
  remaining_downloads: number;
  expires_at: string;
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

export const fetchApplications = async (): Promise<Array<Recommendation>> => {
  const res = await fetch(`${API}/applications`, { cache: "no-store" });
  return parse<Array<Recommendation>>(res);
};

export const markApplicationApplied = async (
  id: string,
): Promise<Recommendation> => {
  const res = await fetch(`${API}/applications/${id}/applied`, {
    method: "POST",
  });
  return parse<Recommendation>(res);
};

export const markApplicationActive = async (
  id: string,
  network: string,
  networkProgramId?: string,
): Promise<Recommendation> => {
  const res = await fetch(`${API}/applications/${id}/active`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      network,
      network_program_id: networkProgramId || null,
    }),
  });
  return parse<Recommendation>(res);
};

export const markApplicationDeclined = async (
  id: string,
): Promise<Recommendation> => {
  const res = await fetch(`${API}/applications/${id}/declined`, {
    method: "POST",
  });
  return parse<Recommendation>(res);
};

export const fetchBrokenLinks = async (): Promise<Array<AffiliateLink>> => {
  const res = await fetch(`${API}/links?status=broken`, { cache: "no-store" });
  return parse<Array<AffiliateLink>>(res);
};

export const repairAffiliateLink = async (
  id: string,
  destinationUrl: string,
): Promise<AffiliateLink> => {
  const res = await fetch(`${API}/links/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ destination_url: destinationUrl }),
  });
  return parse<AffiliateLink>(res);
};

export type ContentMetricRow = {
  id: string;
  title: string;
  publication: string | null;
  clicks: number;
  conversions: number;
  affiliate_cents: number;
  own_cents: number;
  pending_cents: number;
  cost_cents: number;
};

export const fetchMetricsByContent = async (): Promise<
  Array<ContentMetricRow>
> => {
  const res = await fetch(`${API}/metrics/by-content`, { cache: "no-store" });
  return parse<Array<ContentMetricRow>>(res);
};
