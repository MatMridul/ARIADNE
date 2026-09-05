/** Legend: decodes the graph's health colors, motion semantics and markers. */
import { Badge, StatusDot } from "@/design/ui";

export function Legend() {
  return (
    <div
      className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-lg border border-border-subtle bg-bg-surface/90 px-3 py-2.5 backdrop-blur"
      aria-label="Graph legend"
    >
      <div className="mb-1.5 text-2xs uppercase tracking-wide text-text-muted">Legend</div>
      <ul className="space-y-1 text-2xs text-text-secondary">
        <li className="flex items-center gap-2"><StatusDot health="healthy" /> Healthy — fast traffic</li>
        <li className="flex items-center gap-2"><StatusDot health="degraded" /> Degraded — slowed traffic</li>
        <li className="flex items-center gap-2"><StatusDot health="down" /> Down — traffic stopped</li>
        <li className="flex items-center gap-2"><Badge tone="info">SHARED</Badge> bank ≥2 PSPs settle through it</li>
        <li className="flex items-center gap-2"><Badge tone="accent">evidence</Badge> attribution path</li>
        <li className="flex items-center gap-2"><Badge tone="healthy">reroute →</Badge> recovery target</li>
      </ul>
    </div>
  );
}
