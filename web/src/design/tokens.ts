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
    base: "#0a0e14",
    surface: "#111722",
    raised: "#161d2b",
    hover: "#1c2534",
  },
  border: {
    subtle: "#1f2937",
    DEFAULT: "#2a3646",
    strong: "#3a4a5f",
  },
  text: {
    primary: "#e6edf3",
    secondary: "#9aa7b8",
    muted: "#5e6b7e",
  },
  status: {
    healthy: "#2dd4a7",
    degraded: "#f5a623",
    down: "#f45b6c",
    info: "#4f9cf9",
    accent: "#6d8bff",
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
