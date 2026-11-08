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

export type ProductIdea = {
  id: string;
  term: string;
  title: string;
  kind: string;
  score: number;
  score_breakdown: Record<string, number>;
  status: string;
  blocked_reason: string | null;
  source_task_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ProductListing = {
  id: string;
  product_id: string;
  platform: string;
  handle: string;
  external_id: string | null;
  external_variant_id: string | null;
  status: string;
  last_synced_at: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type DashboardTab =
  "all" | "products" | "orders" | "programs" | "content";
