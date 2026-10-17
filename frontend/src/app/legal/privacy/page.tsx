import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 text-gray-800">
      <Link href="/" className="text-xs text-gray-500 hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-gray-900">Privacy Policy</h1>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-gray-700">
        <p>
          We process only the minimum personal data required to fulfill your
          digital order and comply with tax and accounting obligations.
        </p>
        <p>
          <strong>Data Collected:</strong> Your email address, order reference,
          transaction amount/currency, and IP address at the time of download
          for fraud and abuse prevention. Payment card details are processed
          exclusively by our PCI-compliant payment provider and are never stored
          on our servers.
        </p>
        <p>
          <strong>Retention &amp; Rights:</strong> Under GDPR, you have the
          right to access, rectify, or request erasure of your personal data,
          subject to statutory tax retention periods.
        </p>
      </div>
    </main>
  );
}
