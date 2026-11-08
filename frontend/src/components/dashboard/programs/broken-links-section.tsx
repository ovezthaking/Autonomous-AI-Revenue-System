"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { AffiliateLink } from "@/lib/api";

type BrokenLinkRowProps = {
  link: AffiliateLink;
  isBusy: boolean;
  onRepairLink: (id: string, destinationUrl: string) => Promise<boolean>;
};

function BrokenLinkRow({ link, isBusy, onRepairLink }: BrokenLinkRowProps) {
  const [repairDraft, setRepairDraft] = useState<string | null>(null);
  const currentUrl = repairDraft ?? link.destination_url;

  return (
    <li className="space-y-2 rounded border bg-white p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-600">
        <span className="font-mono font-semibold">/go/{link.slug}</span>
        <span>&bull;</span>
        <span>{link.network}</span>
        {link.program_name ? (
          <>
            <span>&bull;</span>
            <span>{link.program_name}</span>
          </>
        ) : null}
        {link.content_title ? (
          <>
            <span>&bull;</span>
            <span>{link.content_title}</span>
          </>
        ) : null}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={currentUrl}
          onChange={(e) => setRepairDraft(e.target.value)}
          className="min-w-0 flex-1 rounded border px-2.5 py-1 text-sm"
        />
        <Button
          size="sm"
          disabled={isBusy}
          onClick={() => {
            void onRepairLink(link.id, currentUrl).then((ok) => {
              if (ok) setRepairDraft(null);
            });
          }}
        >
          Napraw link
        </Button>
      </div>
    </li>
  );
}

type BrokenLinksSectionProps = {
  brokenLinks: AffiliateLink[];
  busyId: string | null;
  onRepairLink: (id: string, destinationUrl: string) => Promise<boolean>;
};

export function BrokenLinksSection({
  brokenLinks,
  busyId,
  onRepairLink,
}: BrokenLinksSectionProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">Broken links</h2>
      {brokenLinks.length === 0 ? (
        <p className="text-sm text-neutral-500">No broken links.</p>
      ) : null}
      <ul className="space-y-3">
        {brokenLinks.map((link) => (
          <BrokenLinkRow
            key={link.id}
            link={link}
            isBusy={busyId === link.id}
            onRepairLink={onRepairLink}
          />
        ))}
      </ul>
    </section>
  );
}
