/**
 * Deterministic layered layout for the Merchant -> Method -> PSP -> Bank flow.
 * Left-to-right columns; positions are pure functions of the topology so the
 * graph never jitters between renders. React Flow consumes {x,y} in flow-space.
 */
import type { Topology } from "@/lib";

export const COL_X = {
  merchant: 0,
  method: 260,
  psp: 560,
  bank: 860,
} as const;

const ROW_GAP = 120;
const NODE_H = 64;

/** Vertically center a column of `count` rows around y=0, return the i-th y. */
function rowY(i: number, count: number): number {
  const total = (count - 1) * ROW_GAP;
  return i * ROW_GAP - total / 2;
}

export interface Positioned {
  id: string;
  x: number;
  y: number;
}

export function layoutPositions(t: Topology): Record<string, Positioned> {
  const pos: Record<string, Positioned> = {};

  // Merchant: single node, vertically centered against the tallest column.
  const tallest = Math.max(t.methods.length, t.psps.length, t.banks.length);
  pos[t.merchant.id] = {
    id: t.merchant.id,
    x: COL_X.merchant,
    y: rowY(Math.floor((tallest - 1) / 2), 1) - NODE_H / 2 + 0,
  };
  // Center merchant on the overall vertical span instead:
  pos[t.merchant.id].y = 0;

  t.methods.forEach((m, i) => {
    pos[m.id] = { id: m.id, x: COL_X.method, y: rowY(i, t.methods.length) };
  });
  t.psps.forEach((p, i) => {
    pos[p.id] = { id: p.id, x: COL_X.psp, y: rowY(i, t.psps.length) };
  });
  t.banks.forEach((b, i) => {
    pos[b.id] = { id: b.id, x: COL_X.bank, y: rowY(i, t.banks.length) };
  });

  return pos;
}

export const LAYOUT_BOUNDS = { NODE_H, ROW_GAP };
