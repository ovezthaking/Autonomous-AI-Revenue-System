import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("utils", () => {
  it("merges class names using cn", () => {
    expect(cn("px-2", false && "hidden", "py-1")).toBe("px-2 py-1");
  });
});
