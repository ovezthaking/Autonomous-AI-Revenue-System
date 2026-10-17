import Link from "next/link";

export default function ContactPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 text-gray-800">
      <Link href="/" className="text-xs text-gray-500 hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-gray-900">
        Contact &amp; Seller Information
      </h1>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-gray-700">
        <p>
          For order support, download assistance, or billing inquiries, please
          reach out with your Checkout Session ID or Order ID:
        </p>
        <ul className="list-inside list-disc space-y-1">
          <li>
            <strong>Support Email:</strong> support@example.com
          </li>
          <li>
            <strong>Response Time:</strong> Within 1–2 business days
          </li>
        </ul>
      </div>
    </main>
  );
}
