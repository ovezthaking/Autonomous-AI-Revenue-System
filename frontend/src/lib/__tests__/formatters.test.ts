import { describe, expect, it } from "vitest";
import type { AgentTask, Recommendation } from "@/lib/api";
import {
  breakdownLabel,
  chapterStatusBadge,
  formatPrice,
  orderStatusBadge,
  productStatusBadge,
  researchErrors,
  taskLabel,
} from "@/lib/formatters";

const makeTask = (overrides: Partial<AgentTask> = {}): AgentTask => ({
  id: "task-1",
  type: "research_programs",
  status: "succeeded",
  output: null,
  error: null,
  created_at: "2026-11-01T00:00:00Z",
  ...overrides,
});

const makeRecommendation = (
  overrides: Partial<Recommendation> = {},
): Recommendation => ({
  id: "rec-1",
  name: "Prog",
  url: "https://example.com",
  network: "awin",
  category: "saas",
  rationale: "Good fit",
  score: 80,
  status: "proposed",
  application_status: "not_applied",
  network_program_id: null,
  applied_at: null,
  affiliate_link: null,
  extras: null,
  created_at: "2026-11-01T00:00:00Z",
  ...overrides,
});

describe("formatters", () => {
  describe("taskLabel", () => {
    it("returns 'idle' when task list is empty", () => {
      expect(taskLabel([])).toBe("idle");
    });

    it("returns status of the first task", () => {
      expect(
        taskLabel([
          makeTask({ status: "running" }),
          makeTask({ status: "succeeded" }),
        ]),
      ).toBe("running");
    });
  });

  describe("researchErrors", () => {
    it("returns empty array when no research_programs task exists", () => {
      expect(researchErrors([makeTask({ type: "generate_content" })])).toEqual(
        [],
      );
    });

    it("returns empty array when output or errors is not an array", () => {
      expect(researchErrors([makeTask({ output: null })])).toEqual([]);
      expect(
        researchErrors([
          makeTask({ output: { errors: "invalid" as unknown as [] } }),
        ]),
      ).toEqual([]);
    });

    it("filters and returns only valid { url, error } entries", () => {
      const tasks = [
        makeTask({
          output: {
            errors: [
              { url: "https://a.test", error: "rejected" },
              { url: 123, error: "bad" } as unknown as {
                url: string;
                error: string;
              },
              null as unknown as { url: string; error: string },
              { url: "https://b.test", error: "timeout" },
            ],
          },
        }),
      ];
      expect(researchErrors(tasks)).toEqual([
        { url: "https://a.test", error: "rejected" },
        { url: "https://b.test", error: "timeout" },
      ]);
    });
  });

  describe("breakdownLabel", () => {
    it("returns null when extras or score_breakdown is missing or empty", () => {
      expect(breakdownLabel(makeRecommendation({ extras: null }))).toBeNull();
      expect(breakdownLabel(makeRecommendation({ extras: {} }))).toBeNull();
      expect(
        breakdownLabel(makeRecommendation({ extras: { score_breakdown: {} } })),
      ).toBeNull();
    });

    it("formats breakdown entries joined by middle dot", () => {
      const rec = makeRecommendation({
        extras: {
          score_breakdown: { commission: 40, cookie: 20, network: 10 },
        },
      });
      expect(breakdownLabel(rec)).toBe(
        "commission 40 · cookie 20 · network 10",
      );
    });
  });

  describe("formatPrice", () => {
    it("formats cents in default USD and custom currency", () => {
      expect(formatPrice(1900)).toBe("$19.00");
      expect(formatPrice(2550, "EUR")).toBe("€25.50");
    });
  });

  describe("productStatusBadge", () => {
    it.each([
      ["draft", "bg-neutral-100 text-neutral-800 border-neutral-300"],
      [
        "outlining",
        "bg-amber-100 text-amber-800 border-amber-300 animate-pulse",
      ],
      ["outlined", "bg-blue-100 text-blue-800 border-blue-300"],
      [
        "writing",
        "bg-yellow-100 text-yellow-800 border-yellow-300 animate-pulse",
      ],
      ["assembled", "bg-purple-100 text-purple-800 border-purple-300"],
      [
        "live",
        "bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold",
      ],
      [
        "archived",
        "bg-neutral-100 text-neutral-400 border-neutral-200 line-through",
      ],
      ["unknown", "bg-neutral-100 text-neutral-700 border-neutral-300"],
    ])("returns badge class for status %s", (status, expected) => {
      expect(productStatusBadge(status)).toBe(expected);
    });
  });

  describe("chapterStatusBadge", () => {
    it.each([
      ["written", "bg-emerald-100 text-emerald-800 border-emerald-300"],
      ["failed", "bg-red-100 text-red-800 border-red-300 font-semibold"],
      ["pending", "bg-neutral-100 text-neutral-600 border-neutral-300"],
      ["other", "bg-neutral-100 text-neutral-600 border-neutral-300"],
    ])("returns badge class for chapter status %s", (status, expected) => {
      expect(chapterStatusBadge(status)).toBe(expected);
    });
  });

  describe("orderStatusBadge", () => {
    it.each([
      ["fulfilled", "bg-emerald-100 text-emerald-800"],
      ["refunded", "bg-red-100 text-red-800"],
      ["needs_review", "bg-amber-100 text-amber-800"],
      ["pending", "bg-neutral-100 text-neutral-700"],
    ])("returns badge class for order status %s", (status, expected) => {
      expect(orderStatusBadge(status)).toBe(expected);
    });
  });
});
