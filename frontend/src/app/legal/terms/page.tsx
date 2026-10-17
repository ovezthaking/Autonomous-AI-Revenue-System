import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 text-gray-800">
      <Link href="/" className="text-xs text-gray-500 hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-gray-900">
        Terms of Service
      </h1>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-gray-700">
        <p>
          These Terms of Service govern purchases of digital publications
          (e-books in PDF and EPUB formats) offered through this store.
        </p>
        <p>
          <strong>1. License:</strong> Upon full payment Confirmation, you are
          granted a personal, non-exclusive, non-transferable license to
          download and read the purchased digital publication for your own use.
          Redistribution, resale, or public uploading of the files is
          prohibited.
        </p>
        <p>
          <strong>2. Delivery:</strong> Delivery is performed electronically via
          a time-limited, quota-controlled download link issued after verified
          payment confirmation.
        </p>
        <p>
          <strong>3. Pricing &amp; Taxes:</strong> Prices are displayed clearly
          prior to checkout. Applicable VAT or sales taxes are calculated during
          checkout by the payment provider or Merchant of Record.
        </p>
      </div>
    </main>
  );
}
