import Link from "next/link";

export default function PurchaseCancelPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-8 shadow-sm">
        <span className="inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
          Checkout Cancelled
        </span>
        <h1 className="mt-3 text-2xl font-bold text-gray-900">
          Your checkout was cancelled
        </h1>
        <p className="mt-2 text-sm text-gray-700">
          No payment has been charged. You can return to the product page at any
          time if you would like to complete your order.
        </p>
        <div className="mt-6">
          <Link
            href="/"
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
