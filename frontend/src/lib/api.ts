const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Recommendation = {
  id: string;
  name: string;
  url: string | null;
  network: string | null;
  category: string | null;
  rationale: string | null;
  status: string;
  source_task_id?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type ContentItem = {
  id: string;
  title: string;
  body: string;
  channel: string;
  status: string;
  created_at: string;
};

export type AgentTask = {
  id: string;
  type: string;
  status: string;
  output: { text?: string } | null;
  error: string | null;
  created_at: string;
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
