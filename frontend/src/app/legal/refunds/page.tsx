import Link from "next/link";

export default function RefundsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 text-gray-800">
      <Link href="/" className="text-xs text-gray-500 hover:underline">
        ← Back
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-gray-900">Refund Policy</h1>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-gray-700">
        <p>
          <strong>EU Digital Content Withdrawal Waiver:</strong> In accordance
          with EU Consumer Rights Directive Article 16(m), by consenting to
          immediate performance of the contract and receiving your digital
          download link, you acknowledge that you waive your statutory 14-day
          right of withdrawal.
        </p>
        <p>
          <strong>Defective Files or Duplicate Charges:</strong> If your file is
          corrupted, unreadable, or you were charged more than once due to a
          technical error, please contact us within 14 days for a replacement or
          full refund. Upon refund issuance, associated download tokens are
          automatically revoked.
        </p>
      </div>
    </main>
  );
}
