import type { AgentTask, Recommendation, ResearchError } from "@/lib/api";

export function taskLabel(tasks: AgentTask[]): string {
  if (tasks.length === 0) return "idle";
  return tasks[0].status;
}

export function researchErrors(tasks: AgentTask[]): ResearchError[] {
  const research = tasks.find((task) => task.type === "research_programs");
  const errors = research?.output?.errors;
  if (!Array.isArray(errors)) return [];
  return errors.filter(
    (item) => typeof item?.url === "string" && typeof item?.error === "string",
  );
}

export function breakdownLabel(item: Recommendation): string | null {
  const breakdown = item.extras?.score_breakdown;
  if (!breakdown) return null;
  const parts = Object.entries(breakdown).map(
    ([name, points]) => `${name} ${points}`,
  );
  return parts.length > 0 ? parts.join(" · ") : null;
}

export function formatPrice(cents: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(cents / 100);
}

export function productStatusBadge(status: string): string {
  switch (status) {
    case "draft":
      return "bg-neutral-100 text-neutral-800 border-neutral-300";
    case "outlining":
      return "bg-amber-100 text-amber-800 border-amber-300 animate-pulse";
    case "outlined":
      return "bg-blue-100 text-blue-800 border-blue-300";
    case "writing":
      return "bg-yellow-100 text-yellow-800 border-yellow-300 animate-pulse";
    case "assembled":
      return "bg-purple-100 text-purple-800 border-purple-300";
    case "live":
      return "bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold";
    case "archived":
      return "bg-neutral-100 text-neutral-400 border-neutral-200 line-through";
    default:
      return "bg-neutral-100 text-neutral-700 border-neutral-300";
  }
}

export function chapterStatusBadge(status: string): string {
  switch (status) {
    case "written":
      return "bg-emerald-100 text-emerald-800 border-emerald-300";
    case "failed":
      return "bg-red-100 text-red-800 border-red-300 font-semibold";
    case "pending":
    default:
      return "bg-neutral-100 text-neutral-600 border-neutral-300";
  }
}

export function orderStatusBadge(status: string): string {
  switch (status) {
    case "fulfilled":
      return "bg-emerald-100 text-emerald-800";
    case "refunded":
      return "bg-red-100 text-red-800";
    case "needs_review":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-neutral-100 text-neutral-700";
  }
}
