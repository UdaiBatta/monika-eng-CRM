import { describe, expect, it } from "vitest";

import { employeeLabel, statusLabel } from "@/production/lib/terminology";

describe("employee-facing Workshop terminology", () => {
  it.each([
    ["ENGINEERING_REVIEW", "Workshop Review"],
    ["ENGINEERING_REVIEWING", "Workshop Reviewing"],
    ["ENGINEERING_ACCEPTED", "Workshop Accepted"],
    ["READY_FOR_ENGINEERING", "Ready for Workshop"],
    ["FEASIBLE", "Workshop Approved"],
    ["NOT_FEASIBLE", "Workshop Cannot Approve"],
  ])("presents %s as %s", (value, expected) => {
    expect(statusLabel(value)).toBe(expected);
  });

  it("preserves the legitimate future Detailed Engineering term", () => {
    expect(employeeLabel("Ready for Detailed Engineering")).toBe(
      "Ready for Detailed Engineering",
    );
  });

  it("normalizes backend display labels without changing identifiers", () => {
    expect(statusLabel("ACCEPTED", "Engineering Accepted")).toBe(
      "Workshop accepted",
    );
  });
});

