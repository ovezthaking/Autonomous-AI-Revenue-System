const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ScoreBreakdown = Record<string, number>;

export type RecommendationExtras = {
  evidence_url?: string | null;
  score_breakdown?: ScoreBreakdown | null;
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
  category: string | null;
  rationale: string | null;
  extras: RecommendationExtras | null;
  status: string;
  score: number | null;
  source_task_id?: string | null;
  created_at: string;
  updated_at?: string | null;
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
