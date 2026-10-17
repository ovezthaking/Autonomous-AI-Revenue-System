"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchLiveProducts, type Product } from "@/lib/api";

export default function StoreCatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchLiveProducts();
        if (active) {
          setProducts(data);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Failed to load catalog",
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
  }, []);

  const filtered = products.filter((p) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      p.title.toLowerCase().includes(q) ||
      (p.subtitle && p.subtitle.toLowerCase().includes(q)) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  });

  return (
    <main className="min-h-screen bg-neutral-50/50 text-gray-900">
      {/* Top Navbar */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/store" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white shadow-sm">
              📚
            </span>
            <span className="text-lg font-bold tracking-tight text-gray-900">
              AI Knowledge Store
            </span>
          </Link>
          <div className="flex items-center gap-4 text-xs font-medium text-gray-600">
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
              Instant PDF &amp; EPUB Delivery
            </span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="border-b border-gray-200 bg-white py-12">
        <div className="mx-auto max-w-6xl px-6">
          <div className="max-w-2xl">
            <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 sm:text-4xl">
              Practical Guides &amp; Playbooks for the AI Era
            </h1>
            <p className="mt-3 text-base text-gray-600">
              High-signal digital publications written for builders, operators,
              and engineers. Instant download upon verified checkout.
            </p>
          </div>

          <div className="mt-8 flex max-w-md items-center rounded-lg border border-gray-300 bg-white px-3 py-2 shadow-sm focus-within:border-indigo-600 focus-within:ring-1 focus-within:ring-indigo-600">
            <span className="text-gray-400">🔍</span>
            <input
              type="text"
              placeholder="Search e-books and guides..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="ml-2 w-full text-sm outline-none placeholder:text-gray-400"
            />
          </div>
        </div>
      </section>

      {/* Products Grid */}
      <section className="mx-auto max-w-6xl px-6 py-12">
        {loading ? (
          <div className="py-12 text-center text-sm text-gray-500">
            Loading published books...
          </div>
        ) : error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            {error}
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
            <div className="text-3xl">📖</div>
            <h2 className="mt-3 text-base font-semibold text-gray-900">
              {search
                ? "No products match your search"
                : "No products currently available"}
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              Check back soon for new published releases.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((product) => {
              const priceFormatted = `${(product.price_cents / 100).toFixed(2)} ${product.currency}`;
              return (
                <div
                  key={product.id}
                  className="flex flex-col justify-between overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition hover:shadow-md"
                >
                  <div className="p-6">
                    <div className="flex items-center justify-between">
                      <span className="rounded bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-700">
                        E-Book
                      </span>
                      <span className="text-sm font-extrabold text-gray-900">
                        {priceFormatted}
                      </span>
                    </div>

                    <h2 className="mt-4 text-lg font-bold text-gray-900">
                      {product.title}
                    </h2>
                    {product.subtitle && (
                      <p className="mt-1 text-xs font-medium text-gray-500">
                        {product.subtitle}
                      </p>
                    )}
                    {product.description && (
                      <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-gray-600">
                        {product.description}
                      </p>
                    )}

                    <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-gray-500">
                      <span className="rounded bg-gray-100 px-2 py-0.5">
                        PDF + EPUB
                      </span>
                      <span className="rounded bg-gray-100 px-2 py-0.5">
                        Free Sample Chapter
                      </span>
                    </div>
                  </div>

                  <div className="border-t border-gray-100 bg-gray-50/70 p-4">
                    <Link
                      href={`/p/${product.slug}`}
                      className="block w-full rounded-lg bg-indigo-600 py-2.5 text-center text-xs font-semibold text-white shadow-sm hover:bg-indigo-700"
                    >
                      View E-Book &amp; Sample →
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-8 text-xs text-gray-500">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6">
          <div>© {new Date().getFullYear()} AI Knowledge Digital Store</div>
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
        </div>
      </footer>
    </main>
  );
}
