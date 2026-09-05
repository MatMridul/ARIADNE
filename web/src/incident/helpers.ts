/**
 * Incident feature — pure derivation helpers over the /api/simulate trace.
 * No API imports here beyond types from @/lib; no fetching, no domain logic.
 * Every derived value is traceable to a real field in the SimulateResponse.
 */
import type { Health } from "@/design/ui";
import type {
  IncidentTypeId,
  SimulateResponse,
  SimWindow,
} from "@/lib";

/** Human gloss for each incident type + the honest "correct outcome". */
export const INCIDENT_META: Record<
  IncidentTypeId,
  { label: string; correct: string; isThesis: boolean }
> = {
  A_shared_bank: {
    label: "Shared bank outage",
    correct: "Attribute to the shared bank (Bank-A), not two independent PSPs.",
    isThesis: true,
  },
  B_single_psp: {
    label: "Single PSP outage",
    correct: "Blame the one PSP — do NOT over-attribute to the bank.",
    isThesis: false,
  },
  C_method: {
    label: "Payment-method fault",
    correct: "Blame the payment method across PSPs.",
    isThesis: false,
  },
  D_ambiguous: {
    label: "Ambiguous noise dip",
    correct: "Do nothing — there is no real cause to act on.",
    isThesis: false,
  },
  E_coincidental: {
    label: "Coincidental dual outage",
    correct:
      "Blame two PSPs on different banks independently — no shared-bank claim.",
    isThesis: false,
  },
};

export const INCIDENT_ORDER: IncidentTypeId[] = [
  "A_shared_bank",
  "B_single_psp",
  "C_method",
  "D_ambiguous",
  "E_coincidental",
];

export const THRESHOLD_OPTIONS = [0.55, 0.7, 0.85] as const;

/** Map a per-node success delta to the design-system Health language. */
export function deltaHealth(delta: number): Health {
  if (delta <= -0.15) return "down";
  if (delta <= -0.04) return "degraded";
  return "healthy";
}

/** Confidence -> health tone for the ring / bars. */
export function confidenceHealth(confidence: number): Health {
  if (confidence >= 0.75) return "healthy";
  if (confidence >= 0.5) return "degraded";
  return "down";
}

/**
 * The representative window: the one whose detection.triggered is set and that
 * carries the most dropped_nodes (strongest signal). Falls back to the incident
 * midpoint, then window 0. Mirrors the server's "strongest detection" pick
 * documented in CONTRACT.md.
 */
export function representativeWindow(res: SimulateResponse): SimWindow {
  const triggered = res.windows.filter((w) => w.detection.triggered);
  if (triggered.length > 0) {
    return triggered.reduce((best, w) =>
      w.detection.dropped_nodes.length > best.detection.dropped_nodes.length
        ? w
        : best
    );
  }
  const mid = Math.floor(
    (res.incident.start_window + res.incident.end_window) / 2
  );
  return (
    res.windows.find((w) => w.window === mid) ??
    res.windows[0]
  );
}

/** The window index at which degradation is first detected, or null. */
export function firstDegradationWindow(res: SimulateResponse): number | null {
  const w = res.windows.find((x) => x.detection.triggered);
  return w ? w.window : null;
}

/** PSPs observed to have dropped, from the representative window's node stats. */
export function droppedPspStats(w: SimWindow) {
  return w.nodes
    .filter((n) => n.node_kind === "psp" && n.delta <= -0.04)
    .sort((a, b) => a.delta - b.delta);
}

/** Healthy control nodes (the "why not them" evidence). */
export function healthyControlStats(w: SimWindow) {
  return w.nodes
    .filter((n) => n.node_kind === "psp" && n.delta > -0.04)
    .sort((a, b) => b.success_rate - a.success_rate);
}

/** Human label for a node id (psp_1 -> PSP-1, bank_A -> Bank-A). */
export function prettyNodeId(id: string): string {
  if (id.startsWith("psp_")) return `PSP-${id.slice(4)}`;
  if (id.startsWith("bank_")) return `Bank-${id.slice(5)}`;
  return id.charAt(0).toUpperCase() + id.slice(1);
}

/** Overall success rate across method nodes in a window (revenue-weighted). */
export function windowSuccessRate(w: SimWindow): number {
  const methods = w.nodes.filter((n) => n.node_kind === "method");
  if (methods.length === 0) return 0;
  const totalVol = methods.reduce((s, n) => s + n.volume, 0);
  if (totalVol === 0) return 0;
  return (
    methods.reduce((s, n) => s + n.success_rate * n.volume, 0) / totalVol
  );
}

/** Revenue-at-risk estimate for a window: lost successful volume x avg amount.
 *  DERIVED from real node stats (baseline_rate - success_rate) * volume.
 *  Not a fabricated figure — it is a transparent function of measured deltas.
 *  Amount-per-txn is unknown at the node level, so we report LOST TRANSACTIONS
 *  as the honest unit and let money come only from money_recovered (real ₹). */
export function lostTxnsInWindow(w: SimWindow): number {
  return w.nodes
    .filter((n) => n.node_kind === "method")
    .reduce(
      (s, n) => s + Math.max(0, (n.baseline_rate - n.success_rate) * n.volume),
      0
    );
}

export function isDoNothing(kind: string): boolean {
  return kind === "do_nothing";
}
