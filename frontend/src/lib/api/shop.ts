import { API, parse } from "./client";
import type { ProductIdea, ProductListing } from "./types";

export const fetchIdeas = async (
  status?: string,
): Promise<Array<ProductIdea>> => {
  const url = status
    ? `${API}/ideas?status=${encodeURIComponent(status)}`
    : `${API}/ideas`;
  const res = await fetch(url, { cache: "no-store" });
  return parse<Array<ProductIdea>>(res);
};

export const decideIdea = async (
  id: string,
  action: "approve" | "reject",
  comment?: string,
): Promise<ProductIdea> => {
  const res = await fetch(`${API}/ideas/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment: comment ?? null }),
  });
  return parse<ProductIdea>(res);
};

export const fetchListings = async (
  status?: string,
): Promise<Array<ProductListing>> => {
  const url = status
    ? `${API}/listings?status=${encodeURIComponent(status)}`
    : `${API}/listings`;
  const res = await fetch(url, { cache: "no-store" });
  return parse<Array<ProductListing>>(res);
};

export const decideListing = async (
  id: string,
  action: "approve" | "reject",
  comment?: string,
): Promise<ProductListing> => {
  const res = await fetch(`${API}/listings/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment: comment ?? null }),
  });
  return parse<ProductListing>(res);
};
