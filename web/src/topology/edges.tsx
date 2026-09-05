/**
 * Semantic-motion traffic edge — ARIA's visual signature.
 *
 * Traffic "particles" flow from source to target along the edge path using SVG
 * <animateMotion> (GPU-friendly, declarative, NO per-frame requestAnimationFrame
 * loop — so there is nothing to leak or run away). Speed encodes health:
 *   healthy  -> fast flow (money moving)
 *   degraded -> slow flow (payments struggling)
 *   down     -> NO particles (flow stopped)
 * Performance guardrails:
 *   - particle count is CAPPED at 2 per edge (`PARTICLES`), and 0 when down,
 *   - animation is pure declarative SVG SMIL (no JS timers/rAF),
 *   - particles are only rendered for healthy/degraded edges.
 */
import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/react";
import type { Health } from "@/design/ui";
import { HEALTH_HEX, TOKENS } from "@/design/tokens";
import type { FlowEdgeData } from "./types";

const PARTICLES = 2; // hard cap per edge

const DUR: Record<Health, number> = {
  healthy: 2.2, // seconds per traversal — brisk
  degraded: 5.5, // sluggish
  down: 0, // stopped
  idle: 3.5,
};

const STROKE: Record<Health, string> = HEALTH_HEX;

export function FlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const d = (data ?? {}) as FlowEdgeData;
  const health: Health = d.health ?? "idle";
  const highlighted = !!d.highlighted;
  const reroute = !!d.reroute;
  const dur = DUR[health];
  const showParticles = dur > 0;

  const baseColor = highlighted
    ? TOKENS.status.accent
    : reroute
    ? TOKENS.status.healthy
    : STROKE[health];
  const width = highlighted || reroute ? 2.5 : health === "down" ? 1 : 1.5;
  const opacity = health === "down" ? 0.35 : 0.8;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: baseColor,
          strokeWidth: width,
          opacity,
          strokeDasharray: health === "down" ? "4 4" : undefined,
          transition: "stroke 0.4s ease, opacity 0.4s ease",
        }}
      />
      {showParticles &&
        Array.from({ length: PARTICLES }).map((_, i) => (
          <circle
            key={`${id}-p${i}`}
            r={highlighted || reroute ? 3 : 2.2}
            fill={baseColor}
            opacity={0.95}
          >
            <animateMotion
              dur={`${dur}s`}
              begin={`${(dur / PARTICLES) * i}s`}
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
        ))}
    </>
  );
}

export const edgeTypes = { flow: FlowEdge };
