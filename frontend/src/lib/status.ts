import type { VendorStatus, VendorSummary } from "./types";

export const PIPELINE_STAGES = [
  { key: "intake", label: "Intake" },
  { key: "review", label: "Review" },
  { key: "evidence", label: "Evidence Gaps" },
  { key: "risk", label: "Risk Scoring" },
  { key: "approval", label: "Approval" },
] as const;

export type StageKey = (typeof PIPELINE_STAGES)[number]["key"];

function lower(value?: string | null) {
  return (value || "").toLowerCase();
}

export function resolveStageFromStatus(
  vendor: Pick<VendorSummary, "status" | "approval_status">,
): StageKey {
  const status = lower(vendor.status);
  const approvalStatus = lower(vendor.approval_status);

  if (
    approvalStatus ||
    status.includes("approval") ||
    status.includes("approved") ||
    status.includes("rejected") ||
    status.includes("conditional")
  ) {
    return "approval";
  }
  if (status.includes("risk")) {
    return "risk";
  }
  if (status.includes("evidence")) {
    return "evidence";
  }
  if (
    status.includes("review") ||
    status.includes("security") ||
    status.includes("compliance") ||
    status.includes("financial")
  ) {
    return "review";
  }
  if (status.includes("processing") || status.includes("intake")) {
    return "intake";
  }
  return "review";
}

export function resolveStageFromVendorStatus(status: VendorStatus): StageKey {
  const currentPhase = lower(status.current_phase);
  if (currentPhase.includes("approval") || lower(status.approval_status)) {
    return "approval";
  }
  if (currentPhase.includes("risk")) {
    return "risk";
  }
  if (currentPhase.includes("evidence")) {
    return "evidence";
  }
  if (currentPhase.includes("intake") || currentPhase.includes("processing")) {
    return "intake";
  }
  return "review";
}

export function deriveStageCounts(vendors: VendorSummary[]) {
  return vendors.reduce<Record<StageKey, number>>(
    (counts, vendor) => {
      const stage = resolveStageFromStatus(vendor);
      counts[stage] += 1;
      return counts;
    },
    {
      intake: 0,
      review: 0,
      evidence: 0,
      risk: 0,
      approval: 0,
    },
  );
}

export function toneForRisk(riskLevel?: string | null) {
  const normalized = lower(riskLevel);
  if (normalized.includes("high")) {
    return "danger";
  }
  if (normalized.includes("moderate") || normalized.includes("medium")) {
    return "warning";
  }
  if (normalized.includes("low")) {
    return "info";
  }
  return "muted";
}

export function toneForStatus(status?: string | null) {
  const normalized = lower(status);
  if (
    normalized.includes("error") ||
    normalized.includes("rejected") ||
    normalized.includes("failed")
  ) {
    return "danger";
  }
  if (
    normalized.includes("pending") ||
    normalized.includes("processing") ||
    normalized.includes("review")
  ) {
    return "warning";
  }
  if (
    normalized.includes("approved") ||
    normalized.includes("completed") ||
    normalized.includes("received")
  ) {
    return "info";
  }
  return "muted";
}
