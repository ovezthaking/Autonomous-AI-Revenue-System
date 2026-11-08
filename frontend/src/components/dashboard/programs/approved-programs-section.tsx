"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Recommendation } from "@/lib/api";

type ApprovedProgramRowProps = {
  item: Recommendation;
  isBusy: boolean;
  onSaveLink: (id: string, link: string) => Promise<boolean>;
};

function ApprovedProgramRow({
  item,
  isBusy,
  onSaveLink,
}: ApprovedProgramRowProps) {
  const [linkDraft, setLinkDraft] = useState<string | null>(null);
  const currentValue = linkDraft ?? item.affiliate_link ?? "";

  return (
    <li className="rounded border bg-white p-4">
      <div className="flex items-center gap-2">
        <div className="font-medium">{item.name}</div>
        {item.application_status ? (
          <span className="rounded bg-neutral-100 px-2 py-0.5 font-mono text-xs">
            {item.application_status}
          </span>
        ) : null}
      </div>
      {item.rationale ? (
        <p className="mt-1 text-sm text-neutral-600">{item.rationale}</p>
      ) : null}
      <div className="mt-3 flex gap-2">
        <input
          type="text"
          value={currentValue}
          onChange={(event) => setLinkDraft(event.target.value)}
          placeholder="Affiliate link (manual / fallback)"
          className="min-w-0 flex-1 rounded border px-2.5 py-1 text-sm"
        />
        <Button
          size="sm"
          variant="secondary"
          disabled={isBusy}
          onClick={() => {
            void onSaveLink(item.id, currentValue).then((ok) => {
              if (ok) setLinkDraft(null);
            });
          }}
        >
          Save link
        </Button>
      </div>
    </li>
  );
}

type ApprovedProgramsSectionProps = {
  approved: Recommendation[];
  busyId: string | null;
  onSaveLink: (id: string, link: string) => Promise<boolean>;
};

export function ApprovedProgramsSection({
  approved,
  busyId,
  onSaveLink,
}: ApprovedProgramsSectionProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">Approved affiliate programs</h2>
      {approved.length === 0 ? (
        <p className="text-sm text-neutral-500">No approved programs.</p>
      ) : null}
      <ul className="space-y-4">
        {approved.map((item) => (
          <ApprovedProgramRow
            key={item.id}
            item={item}
            isBusy={busyId === item.id}
            onSaveLink={onSaveLink}
          />
        ))}
      </ul>
    </section>
  );
}
