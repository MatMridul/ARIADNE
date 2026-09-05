/**
 * Evaluation-local formatting + tiny stats helpers. Pure functions, no data/API
 * imports. `inr` is re-exported from the design system so this feature has one
 * money formatter and does not redefine currency logic.
 */
import { inr } from "@/design/ui";

export { inr };

/** A ratio rendered at full precision (the honesty discipline: no rounding away
 * a 0.9988 into a misleading 1.00). Clamped display of up to 4 decimals. */
export function pct(n: number, decimals = 1): string {
  return `${(n * 100).toFixed(decimals)}%`;
}

/** Full-precision ratio, e.g. 0.9988 — used where rounding would hide misses. */
export function ratio(n: number, decimals = 4): string {
  return n.toFixed(decimals);
}

export function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

export function min(xs: number[]): number {
  return xs.length ? Math.min(...xs) : 0;
}

export function max(xs: number[]): number {
  return xs.length ? Math.max(...xs) : 0;
}

/** Count seeds at-or-below a threshold — used to surface losing/tie seeds. */
export function countAtOrBelow(xs: number[], t: number): number {
  return xs.filter((x) => x <= t).length;
}

export function countNegative(xs: number[]): number {
  return xs.filter((x) => x < 0).length;
}
