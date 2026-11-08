import { API, parse } from "./client";
import type {
  AgentTask,
  ContentItem,
  ContentMetricRow,
  Publication,
} from "./types";

export const fetchContent = async (): Promise<Array<ContentItem>> => {
  const res = await fetch(`${API}/content`, { cache: "no-store" });
  return parse<Array<ContentItem>>(res);
};

export const fetchRecentTasks = async (): Promise<Array<AgentTask>> => {
  const res = await fetch(`${API}/tasks?limit=5`, { cache: "no-store" });
  return parse<Array<AgentTask>>(res);
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

export const fetchMetricsByContent = async (): Promise<
  Array<ContentMetricRow>
> => {
  const res = await fetch(`${API}/metrics/by-content`, { cache: "no-store" });
  return parse<Array<ContentMetricRow>>(res);
};
