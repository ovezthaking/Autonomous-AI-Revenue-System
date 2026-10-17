"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import {
  consumeDownloadToken,
  type DownloadVerification,
  verifyDownloadToken,
} from "@/lib/api";

export default function DownloadTokenPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [info, setInfo] = useState<DownloadVerification | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const verify = async () => {
      try {
        setLoading(true);
        const res = await verifyDownloadToken(token);
        if (active) {
          setInfo(res);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Invalid or expired download link",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    verify();
    return () => {
      active = false;
    };
  }, [token]);

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    setError(null);
    try {
      const res = await consumeDownloadToken(token);
      setInfo((prev) =>
        prev
          ? {
              ...prev,
              downloads_used: res.downloads_used,
              max_downloads: res.max_downloads,
              remaining_downloads: res.remaining_downloads,
            }
          : prev,
      );
      window.open(res.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16 text-gray-800">
        <p className="text-sm text-gray-500">Verifying download link...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16 text-gray-900">
      <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
        <span className="inline-block rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-800">
          Secure Digital Delivery
        </span>

        {info ? (
          <>
            <h1 className="mt-3 text-2xl font-bold text-gray-900">
              {info.title}
            </h1>
            <p className="mt-1 text-xs text-gray-500">
              Opening this page does not consume your download quota. A download
              is only counted when you click the button below.
            </p>

            <div className="mt-5 grid grid-cols-2 gap-3 rounded-lg bg-gray-50 p-4 text-xs text-gray-700">
              <div>
                <div className="text-gray-500">Downloads Used</div>
                <div className="mt-0.5 text-base font-bold text-gray-900">
                  {info.downloads_used} / {info.max_downloads}
                </div>
              </div>
              <div>
                <div className="text-gray-500">Expires At</div>
                <div className="mt-0.5 font-medium text-gray-900">
                  {new Date(info.expires_at).toLocaleString()}
                </div>
              </div>
            </div>

            {error && (
              <p className="mt-4 rounded bg-red-100 p-3 text-xs text-red-700">
                {error}
              </p>
            )}

            <button
              type="button"
              onClick={handleDownload}
              disabled={downloading || info.remaining_downloads <= 0}
              className="mt-6 w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {downloading
                ? "Generating Signed PDF Link..."
                : info.remaining_downloads <= 0
                  ? "Download Quota Exhausted"
                  : `Download E-Book (PDF) — ${info.remaining_downloads} remaining`}
            </button>
          </>
        ) : (
          <div className="mt-4">
            <h1 className="text-xl font-bold text-red-900">
              Download Link Unavailable
            </h1>
            <p className="mt-2 text-sm text-red-700">
              {error ??
                "This download link has expired, been revoked, or reached its maximum download limit."}
            </p>
          </div>
        )}

        <div className="mt-6 border-t border-gray-100 pt-4 text-xs text-gray-500">
          <Link href="/" className="hover:underline">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
