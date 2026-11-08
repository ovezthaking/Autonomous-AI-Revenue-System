import { API, parse } from "./client";
import type { AffiliateLink, AgentTask, Recommendation } from "./types";

export const fetchRecommendations = async (
  status: string = "proposed",
): Promise<Array<Recommendation>> => {
  const res = await fetch(
    `${API}/recommendations?status=${encodeURIComponent(status)}`,
    { cache: "no-store" },
  );
  return parse<Array<Recommendation>>(res);
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
