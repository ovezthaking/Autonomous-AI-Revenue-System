"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  createCheckout,
  fetchProductBySlug,
  fetchProductSample,
  type Product,
  type ProductSample,
} from "@/lib/api";

export default function ProductLandingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const [product, setProduct] = useState<Product | null>(null);
  const [sample, setSample] = useState<ProductSample | null>(null);
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [checkingOut, setCheckingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const [prod, samp] = await Promise.all([
          fetchProductBySlug(slug),
          fetchProductSample(slug),
        ]);
        if (active) {
          setProduct(prod);
          setSample(samp);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Product not available",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [slug]);

  const handleBuyNow = async () => {
    if (!consent || checkingOut) return;
    setCheckingOut(true);
    setError(null);
    try {
      const params = new URLSearchParams(window.location.search);
      const source = params.get("utm_content");
      const res = await createCheckout(slug, consent, source);
      window.location.href = res.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
      setCheckingOut(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-16 text-gray-800">
        <p className="text-sm text-gray-500">Loading product...</p>
      </main>
    );
  }

  if (!product) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-16 text-gray-800">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <h1 className="text-lg font-semibold text-red-900">
            Product Not Found
          </h1>
          <p className="mt-1 text-sm text-red-700">
            {error ?? "This e-book is not available for purchase right now."}
          </p>
          <Link
            href="/"
            className="mt-4 inline-block text-sm font-medium text-red-800 underline"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  const priceFormatted = `${(product.price_cents / 100).toFixed(2)} ${product.currency}`;
  const chapters = sample?.chapters ?? [];

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 text-gray-900">
      <div className="mb-6 flex items-center justify-between text-xs text-gray-500">
        <Link href="/store" className="hover:underline">
          ← All E-Books Store
        </Link>
        <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-medium text-emerald-800">
          Instant Digital Delivery (PDF + EPUB)
        </span>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-start">
          <div className="space-y-3">
            <span className="inline-block rounded bg-indigo-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
              Digital E-Book
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              {product.title}
            </h1>
            {product.subtitle && (
              <p className="text-lg text-gray-600">{product.subtitle}</p>
            )}
            {product.description && (
              <p className="mt-2 leading-relaxed text-gray-700">
                {product.description}
              </p>
            )}
          </div>

          <div className="w-full shrink-0 rounded-xl border border-indigo-100 bg-indigo-50/50 p-6 md:w-80">
            <div className="text-xs font-medium uppercase text-gray-500">
              One-Time Purchase
            </div>
            <div className="mt-1 text-3xl font-extrabold text-gray-900">
              {priceFormatted}
            </div>
            <ul className="mt-3 space-y-1 text-xs text-gray-600">
              <li>✓ Full PDF &amp; EPUB editions</li>
              <li>✓ {chapters.length} comprehensive chapters</li>
              <li>✓ Direct download link valid for 7 days</li>
            </ul>

            <label className="mt-4 flex cursor-pointer items-start gap-2 text-xs text-gray-700">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span>
                I expressly consent to immediate performance of the contract and
                acknowledge that I will lose my 14-day EU right of withdrawal
                once the digital download begins.
              </span>
            </label>

            {error && (
              <p className="mt-3 rounded bg-red-100 p-2 text-xs text-red-700">
                {error}
              </p>
            )}

            <button
              type="button"
              disabled={!consent || checkingOut}
              onClick={handleBuyNow}
              className="mt-4 w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {checkingOut
                ? "Redirecting to Checkout..."
                : `Buy Now — ${priceFormatted}`}
            </button>
          </div>
        </div>
      </section>

      {chapters.length > 0 && (
        <section className="mt-8 rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
          <h2 className="text-xl font-bold text-gray-900">
            Table of Contents ({chapters.length} Chapters)
          </h2>
          <ol className="mt-4 divide-y divide-gray-100">
            {chapters.map((ch) => (
              <li key={ch.position} className="py-3">
                <div className="font-medium text-gray-900">
                  Chapter {ch.position}: {ch.title}
                </div>
                {ch.brief && (
                  <p className="mt-0.5 text-sm text-gray-600">{ch.brief}</p>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}

      {sample?.sample_chapter && (
        <section className="mt-8 rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              Free Sample — Chapter {sample.sample_chapter.position}:{" "}
              {sample.sample_chapter.title}
            </h2>
            <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              Preview
            </span>
          </div>
          <div className="mt-4 max-h-96 overflow-y-auto whitespace-pre-wrap rounded-lg border border-gray-100 bg-gray-50 p-5 font-serif text-sm leading-relaxed text-gray-800">
            {sample.sample_chapter.body}
          </div>
        </section>
      )}

      <footer className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-gray-200 pt-6 text-xs text-gray-500">
        <div>© {new Date().getFullYear()} Revenue Swarm Digital Publishing</div>
        <div className="flex gap-4">
          <Link href="/legal/terms" className="hover:underline">
            Terms of Service
          </Link>
          <Link href="/legal/privacy" className="hover:underline">
            Privacy Policy
          </Link>
          <Link href="/legal/refunds" className="hover:underline">
            Refund Policy
          </Link>
          <Link href="/legal/contact" className="hover:underline">
            Contact
          </Link>
        </div>
      </footer>
    </main>
  );
}
