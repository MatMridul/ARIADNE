/**
 * SINGLE source of truth for raw color values used OUTSIDE Tailwind classes —
 * i.e. anywhere we must pass a literal hex (SVG strokes/fills, React Flow, Recharts,
 * canvas). These MUST mirror `tailwind.config.js`; importing from here stops the
 * documented token drift where each viz file re-typed the palette as raw strings.
 *
 * Rule: components style with Tailwind classes; only low-level SVG/chart props that
 * cannot take a class read from `TOKENS`.
 */
export const TOKENS = {
  bg: {
    base: "#080a0f",
    surface: "#0d1017",
    raised: "#12161f",
    hover: "#1a1f2b",
    inset: "#05070b",
  },
  border: {
    subtle: "#171b24",
    DEFAULT: "#232a36",
    strong: "#333d4e",
  },
  text: {
    primary: "#eef2f6",
    secondary: "#8b96a6",
    muted: "#59626f",
  },
  status: {
    healthy: "#3ad19a",
    degraded: "#f2a33c",
    down: "#f65e6e",
    info: "#5aa2f0",
    accent: "#4db6c9",
  },
} as const;

import type { Health } from "./ui";

/** Health -> canonical hex, for SVG/chart literals only. */
export const HEALTH_HEX: Record<Health, string> = {
  healthy: TOKENS.status.healthy,
  degraded: TOKENS.status.degraded,
  down: TOKENS.status.down,
  idle: TOKENS.border.strong,
};
