import Link from "next/link";
import type { AgentTask } from "@/lib/api";
import { researchErrors, taskLabel } from "@/lib/formatters";

type DashboardHeaderProps = {
  tasks: AgentTask[];
};

export function DashboardHeader({ tasks }: DashboardHeaderProps) {
  const errors = researchErrors(tasks);

  return (
    <div className="flex flex-col gap-2 border-b pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">
            HITL Revenue Swarm
          </h1>
          <Link
            href="/shop"
            className="rounded border bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700 hover:bg-neutral-200"
          >
            Shop &amp; Trends →
          </Link>
          <Link
            href="/store"
            className="rounded border bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
          >
            Public Store →
          </Link>
        </div>
        <p className="text-sm text-neutral-500">
          Human-in-the-loop control for autonomous affiliate research, content
          &amp; e-books
        </p>
      </div>
      <div className="text-xs text-neutral-600 sm:text-right">
        <div>
          Last agent task:{" "}
          <strong className="font-semibold">{taskLabel(tasks)}</strong>
        </div>
        {errors.length > 0 ? (
          <span className="mt-1 block text-red-600">
            Research errors:{" "}
            {errors.map((item) => `${item.url} (${item.error})`).join("; ")}
          </span>
        ) : null}
      </div>
    </div>
  );
}
