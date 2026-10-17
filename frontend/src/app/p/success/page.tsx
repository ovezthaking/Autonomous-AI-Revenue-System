"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchOrderBySession } from "@/lib/api";

function SuccessContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [orderStatus, setOrderStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;
    const poll = async () => {
      try {
        const res = await fetchOrderBySession(sessionId);
        if (active) setOrderStatus(res.status);
      } catch {
        // Ignore transient lookup errors while webhook is in flight
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [sessionId]);

  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-8 shadow-sm">
      <span className="inline-block rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
        Order Confirmed
      </span>
      <h1 className="mt-3 text-2xl font-bold text-gray-900">
        Thank you for your purchase!
      </h1>
      <p className="mt-2 text-sm text-gray-700">
        Your payment is being processed by our payment provider. As soon as the
        signed payment webhook is verified, your personal download link will be
        sent to your email address.
      </p>
      {sessionId && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-white p-4 text-xs text-gray-700">
          <div>
            <span className="font-semibold">Checkout Session:</span>{" "}
            <code className="font-mono">{sessionId}</code>
          </div>
          <div className="mt-1">
            <span className="font-semibold">Fulfillment Status:</span>{" "}
            <span className="uppercase font-medium text-emerald-700">
              {orderStatus ?? "awaiting webhook confirmation..."}
            </span>
          </div>
        </div>
      )}
      <div className="mt-6 flex gap-4 text-sm">
        <Link
          href="/"
          className="rounded-lg bg-emerald-700 px-4 py-2 font-medium text-white hover:bg-emerald-800"
        >
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function PurchaseSuccessPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <Suspense
        fallback={
          <div className="text-sm text-gray-500">Loading confirmation...</div>
        }
      >
        <SuccessContent />
      </Suspense>
    </main>
  );
}
