/**
 * Side panel — the "why" for the current window: detection state, attribution
 * (root_cause_id / kind / confidence), and the evidence_path rendered VERBATIM
 * (it is the backend's own reasoning trace; we never paraphrase it).
 */
import { Badge, Card, CardHeader, Metric, cn, inr } from "@/design/ui";
import type { Attribution, SimulateResponse, SimWindow } from "@/lib";

const KIND_TONE: Record<string, "info" | "down" | "degraded" | "neutral"> = {
  bank: "down",
  psp: "degraded",
  method: "info",
  none: "neutral",
};

function confidenceTone(c: number): "healthy" | "degraded" | "down" {
  if (c >= 0.8) return "healthy";
  if (c >= 0.5) return "degraded";
  return "down";
}

export function SidePanel({
  sim,
  win,
  attribution,
}: {
  sim?: SimulateResponse;
  win?: SimWindow;
  attribution?: Attribution;
}) {
  const detection = win?.detection;
  const attr = attribution;

  return (
    <div className="flex h-full w-[340px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-border-subtle bg-bg-base p-3">
      {/* Detection */}
      <Card>
        <CardHeader title="Detection" subtitle="current window" />
        <div className="p-4">
          {detection ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge tone={detection.triggered ? "down" : "healthy"}>
                  {detection.triggered ? "TRIGGERED" : "quiet"}
                </Badge>
                {detection.dropped_nodes.length > 0 && (
                  <span className="text-2xs text-text-muted">
                    dropped: {detection.dropped_nodes.join(", ")}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-2xs text-text-muted">Run a scenario to see detection.</p>
          )}
        </div>
      </Card>

      {/* Attribution */}
      <Card>
        <CardHeader
          title="Attribution"
          subtitle="root cause diagnosis"
          right={
            attr ? (
              <Badge tone={KIND_TONE[attr.root_cause_kind] ?? "neutral"}>
                {attr.root_cause_kind}
              </Badge>
            ) : undefined
          }
        />
        {attr ? (
          <div className="p-4">
            <div className="flex items-baseline justify-between">
              <div>
                <div className="text-2xs uppercase tracking-wide text-text-muted">root cause</div>
                <div className="font-mono text-sm font-semibold text-text-primary">
                  {attr.root_cause_id}
                </div>
              </div>
              <Metric
                label="confidence"
                value={`${Math.round(attr.confidence * 100)}%`}
                tone={confidenceTone(attr.confidence)}
              />
            </div>

            {attr.psp_causes.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {attr.psp_causes.map((p) => (
                  <Badge key={p} tone="accent">{p}</Badge>
                ))}
              </div>
            )}

            {/* evidence_path — rendered VERBATIM (backend reasoning trace) */}
            <div className="mt-3">
              <div className="mb-1 text-2xs uppercase tracking-wide text-text-muted">
                evidence path
              </div>
              <ol className="space-y-1 rounded-md border border-border-subtle bg-bg-raised p-2">
                {attr.evidence_path.map((line, i) => (
                  <li
                    key={i}
                    className={cn(
                      "font-mono text-2xs leading-snug text-text-secondary",
                      i === attr.evidence_path.length - 1 && "text-text-primary"
                    )}
                  >
                    <span className="text-text-muted">{i + 1}.</span> {line}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        ) : (
          <div className="p-4 text-2xs text-text-muted">
            Diagnosis appears once the incident window is reached.
          </div>
        )}
      </Card>

      {/* Outcome */}
      {sim && (
        <Card>
          <CardHeader title="Outcome" subtitle="counterfactual" />
          <div className="grid grid-cols-2 divide-x divide-border-subtle">
            <Metric
              label="recovered"
              value={inr(sim.money_recovered)}
              tone={sim.money_recovered >= 0 ? "healthy" : "down"}
            />
            <Metric label="action" value={sim.action.kind} />
          </div>
          <div className="border-t border-border-subtle p-3 text-2xs text-text-muted">
            decision {sim.action.decision_id}
          </div>
        </Card>
      )}
    </div>
  );
}
