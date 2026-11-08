"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideIdea,
  decideListing,
  fetchIdeas,
  fetchListings,
  fetchOrders,
  type Order,
  type ProductIdea,
  type ProductListing,
} from "@/lib/api";

export function useShop() {
  const [ideas, setIdeas] = useState<Array<ProductIdea>>([]);
  const [blocked, setBlocked] = useState<Array<ProductIdea>>([]);
  const [listings, setListings] = useState<Array<ProductListing>>([]);
  const [orders, setOrders] = useState<Array<Order>>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [proposedData, blockedData, listingsData, ordersData] =
        await Promise.all([
          fetchIdeas("proposed"),
          fetchIdeas("blocked"),
          fetchListings(),
          fetchOrders(),
        ]);
      setIdeas(proposedData);
      setBlocked(blockedData);
      setListings(listingsData);
      setOrders(ordersData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load shop data");
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      await load();
    };
    void init();
  }, [load]);

  const handleIdeaDecision = async (
    id: string,
    action: "approve" | "reject",
  ) => {
    setBusyId(id);
    try {
      await decideIdea(id, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Idea decision failed");
    } finally {
      setBusyId(null);
    }
  };

  const handleListingDecision = async (
    id: string,
    action: "approve" | "reject",
  ) => {
    setBusyId(id);
    try {
      await decideListing(id, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Listing decision failed");
    } finally {
      setBusyId(null);
    }
  };

  return {
    ideas,
    blocked,
    listings,
    orders,
    error,
    busyId,
    handleIdeaDecision,
    handleListingDecision,
  };
}
