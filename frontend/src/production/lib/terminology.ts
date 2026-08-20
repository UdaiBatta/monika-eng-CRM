const employeeLabels: Record<string, string> = {
  ENGINEERING_REVIEW: "Workshop Review",
  ENGINEERING_REVIEWING: "Workshop Reviewing",
  ENGINEERING_ACCEPTED: "Workshop Accepted",
  READY_FOR_ENGINEERING: "Ready for Workshop",
  FEASIBLE: "Workshop Approved",
  FEASIBLE_WITH_CONDITIONS: "Workshop Approved with Conditions",
  NOT_FEASIBLE: "Workshop Cannot Approve",
  ENGINEERING: "Workshop / Technical Labour",
};

/** Presentation-only terminology. Internal API, model, and audit identifiers stay stable. */
export function employeeLabel(value: string) {
  const exact = employeeLabels[value.toUpperCase()];
  if (exact) return exact;

  return value
    .replace(/engineering feasibility/gi, "Workshop Review")
    .replace(/engineering review/gi, "Workshop Review")
    .replace(/engineering handoff/gi, "Workshop handoff")
    .replace(/engineering owner/gi, "Workshop owner")
    .replace(/engineering work/gi, "Workshop work")
    .replace(/engineering clarification/gi, "Workshop clarification")
    .replace(/sent to engineering/gi, "sent to Workshop")
    .replace(/send to engineering/gi, "send to Workshop")
    .replace(/waiting for engineering/gi, "waiting for Workshop")
    .replace(/ready for engineering/gi, "ready for Workshop")
    .replace(/engineering accepted/gi, "Workshop accepted")
    .replace(/engineering reviewing/gi, "Workshop reviewing");
}

export function statusLabel(value: string, supplied?: string) {
  if (supplied) return employeeLabel(supplied);
  const exact = employeeLabel(value);
  if (exact !== value) return exact;
  return employeeLabel(
    value
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/^./, (letter) => letter.toUpperCase()),
  );
}
