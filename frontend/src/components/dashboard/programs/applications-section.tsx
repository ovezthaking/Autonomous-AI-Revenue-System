"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Recommendation } from "@/lib/api";

type ApplicationRowProps = {
  item: Recommendation;
  isBusy: boolean;
  onMarkApplied: (id: string) => void;
  onMarkActive: (
    id: string,
    network: string,
    networkProgramId?: string,
  ) => void;
  onMarkDeclined: (id: string) => void;
};

function ApplicationRow({
  item,
  isBusy,
  onMarkApplied,
  onMarkActive,
  onMarkDeclined,
}: ApplicationRowProps) {
  const [networkDraft, setNetworkDraft] = useState<string | null>(null);
  const [programIdDraft, setProgramIdDraft] = useState<string | null>(null);

  const selectedNetwork =
    networkDraft ?? (item.network ? item.network.toLowerCase() : "manual");
  const currentProgramId = programIdDraft ?? item.network_program_id ?? "";

  return (
    <li className="space-y-2 rounded border bg-white p-4">
      <div className="flex items-center gap-2">
        <h3 className="font-medium">{item.name}</h3>
        <span className="rounded bg-neutral-100 px-2 py-0.5 font-mono text-xs">
          {item.application_status ?? "not_applied"}
        </span>
        {item.extras?.needs_reminder ? (
          <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
            Przypomnienie (&gt;14 dni)
          </span>
        ) : null}
      </div>
      {item.url ? (
        <p className="break-all text-xs text-blue-600 underline">
          <a href={item.url} target="_blank" rel="noopener noreferrer">
            {item.url}
          </a>
        </p>
      ) : null}
      {item.rationale ? (
        <p className="text-sm text-neutral-700">{item.rationale}</p>
      ) : null}
      {item.extras?.facts ? (
        <p className="break-all font-mono text-xs text-neutral-500">
          {JSON.stringify(item.extras.facts)}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-2 pt-2">
        {item.application_status === "not_applied" ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={isBusy}
            onClick={() => onMarkApplied(item.id)}
          >
            Zaaplikowano
          </Button>
        ) : null}
        <select
          value={selectedNetwork}
          onChange={(e) => setNetworkDraft(e.target.value)}
          className="rounded border px-2 py-1 text-xs"
        >
          <option value="manual">manual</option>
          <option value="awin">awin</option>
          <option value="impact">impact</option>
          <option value="cj">cj</option>
          <option value="amazon">amazon</option>
        </select>
        <input
          type="text"
          value={currentProgramId}
          onChange={(e) => setProgramIdDraft(e.target.value)}
          placeholder="network_program_id"
          className="rounded border px-2 py-1 text-xs"
        />
        <Button
          size="sm"
          disabled={isBusy}
          onClick={() =>
            onMarkActive(
              item.id,
              selectedNetwork,
              currentProgramId || undefined,
            )
          }
        >
          Approve
        </Button>
        <Button
          size="sm"
          variant="destructive"
          disabled={isBusy}
          onClick={() => onMarkDeclined(item.id)}
        >
          Reject
        </Button>
      </div>
    </li>
  );
}

type ApplicationsSectionProps = {
  applications: Recommendation[];
  busyId: string | null;
  onMarkApplied: (id: string) => void;
  onMarkActive: (
    id: string,
    network: string,
    networkProgramId?: string,
  ) => void;
  onMarkDeclined: (id: string) => void;
};

export function ApplicationsSection({
  applications,
  busyId,
  onMarkApplied,
  onMarkActive,
  onMarkDeclined,
}: ApplicationsSectionProps) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-medium">To Apply</h2>
      {applications.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No programs waiting for approve.
        </p>
      ) : null}
      <ul className="space-y-4">
        {applications.map((item) => (
          <ApplicationRow
            key={item.id}
            item={item}
            isBusy={busyId === item.id}
            onMarkApplied={onMarkApplied}
            onMarkActive={onMarkActive}
            onMarkDeclined={onMarkDeclined}
          />
        ))}
      </ul>
    </section>
  );
}
