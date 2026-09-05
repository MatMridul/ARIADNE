/** Command Center overview (F3).
 * Answers: What is happening? Why? What should I do? What happened after?
 * Composes a KPI row, a clearly-marked TOPOLOGY SLOT (the graph is owned by the
 * topology agent and embedded by the shell later — we render a compact status
 * summary here), an active-diagnosis card, a recommended-action card, and a
 * recent-activity list from useAudit(). Every number is real from the API. */
import { motion } from "framer-motion";
import {
  Badge,
  Card,
  CardHeader,
  Metric,
  StatusDot,
  cn,
  inr,
} from "@/design/ui";
import { useAudit, useSimulate, type SimulateRequest } from "@/lib";
import {
  confidenceHealth,
  droppedPspStats,
  prettyNodeId,
  representativeWindow,
  windowSuccessRate,
} from "./helpers";
import { ConfidenceRing } from "./ConfidenceRing";
import { EvidencePath } from "./EvidencePath";
import { ErrorState, LoadingState } from "./States";

// The Command Center opens on the hero / thesis scenario.
const DEFAULT_REQ: SimulateRequest = {
  incident_type: "A_shared_bank",
  seed: 7,
  intervention_threshold: 0.7,
  system: "ariadne",
};

/** Clearly-marked placeholder where the topology agent's graph gets embedded. */
function TopologySlot({
  droppedNodes,
  rootCauseId,
}: {
  droppedNodes: string[];
  rootCauseId: string;
}) {
  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="Payment topology"
        subtitle="Live dependency graph — embedded here by the topology agent"
      />
      {/* TOPOLOGY-GRAPH-SLOT: the shell mounts the topology feature's living
          graph into this container. Until then we show a compact status
          summary derived from the same trace so the overview is never empty. */}
      <div
        data-slot="topology-graph"
        className="flex min-h-[220px] flex-col items-center justify-center gap-3 border-2 border-dashed border-border-subtle p-6 text-center"
      >
        <Badge tone="neutral">graph slot — topology feature</Badge>
        <p className="max-w-sm text-xs text-text-muted">
          Merchant → Method → PSP → Bank living graph renders here. Compact status
          from the current trace:
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {droppedNodes.length === 0 ? (
            <Badge tone="healthy">all nodes healthy</Badge>
          ) : (
            droppedNodes.map((n) => (
              <Badge key={n} tone="down" className="font-mono">
                {prettyNodeId(n)} down
              </Badge>
            ))
          )}
          {rootCauseId && (
            <Badge tone="accent" className="font-mono">
              root: {prettyNodeId(rootCauseId)}
            </Badge>
          )}
        </div>
      </div>
    </Card>
  );
}

export function CommandCenter() {
  const sim = useSimulate(DEFAULT_REQ);
  const audit = useAudit(DEFAULT_REQ);

  if (sim.isLoading) return <LoadingState label="Loading command center…" />;
  if (sim.error)
    return <ErrorState error={sim.error} onRetry={() => sim.refetch()} />;
  if (!sim.data) return <LoadingState label="Loading command center…" />;

  const res = sim.data;
  const rep = representativeWindow(res);
  const attr = res.attribution;
  const action = res.action;
  const dropped = droppedPspStats(rep);
  const successRate = windowSuccessRate(rep);
  const negative = res.money_recovered < 0;
  const doNothing = action.kind === "do_nothing";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">
            Command Center
          </h1>
          <p className="text-2xs text-text-muted">
            Hero scenario: shared-bank outage · seed {DEFAULT_REQ.seed} · risk
            dial {DEFAULT_REQ.intervention_threshold.toFixed(2)} · simulated
          </p>
        </div>
        <Badge tone={dropped.length ? "down" : "healthy"}>
          <StatusDot health={dropped.length ? "down" : "healthy"} pulse={!!dropped.length} />
          {dropped.length ? "active incident" : "nominal"}
        </Badge>
      </div>

      {/* KPI row */}
      <Card>
        <div className="grid grid-cols-2 divide-x divide-border-subtle sm:grid-cols-4">
          <Metric
            label="Revenue at risk"
            value={inr(Math.max(0, action.expected_recovery))}
            tone={action.expected_recovery > 0 ? "degraded" : "default"}
            hint="expected_recovery — estimate"
          />
          <Metric
            label="Recovered revenue"
            value={inr(res.money_recovered)}
            tone={negative ? "down" : "healthy"}
            hint="measured counterfactual"
          />
          <Metric
            label="Success rate"
            value={`${(successRate * 100).toFixed(1)}%`}
            tone={successRate < 0.9 ? "degraded" : "healthy"}
            hint={`window ${rep.window}`}
          />
          <Metric
            label="Active incident"
            value={res.incident.incident_type.split("_")[0]}
            hint={res.incident.incident_type}
          />
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <TopologySlot
          droppedNodes={rep.detection.dropped_nodes}
          rootCauseId={attr.root_cause_id}
        />

        {/* Active diagnosis */}
        <Card>
          <CardHeader
            title="Active diagnosis"
            subtitle="Root cause + confidence + evidence path (verbatim)"
          />
          <div className="grid gap-4 p-4 sm:grid-cols-[auto_1fr]">
            <div className="flex flex-col items-center gap-2">
              <ConfidenceRing value={attr.confidence} />
              <Badge
                tone={attr.root_cause_kind === "none" ? "neutral" : "down"}
                className="font-mono"
              >
                {attr.root_cause_kind}
              </Badge>
            </div>
            <div>
              <span className="text-2xs uppercase tracking-wide text-text-muted">
                Root cause
              </span>
              <div className="mb-3 text-lg font-semibold text-text-primary">
                {attr.root_cause_kind === "none"
                  ? "No single cause"
                  : prettyNodeId(attr.root_cause_id)}
              </div>
              <EvidencePath steps={attr.evidence_path} claimType={attr.claim_type} />
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recommended action */}
        <Card>
          <CardHeader
            title="Recommended action"
            subtitle="What should the operator do?"
            right={
              <Badge tone={confidenceHealth(action.confidence) === "healthy" ? "accent" : "degraded"}>
                {(action.confidence * 100).toFixed(0)}% conf
              </Badge>
            }
          />
          <div className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Badge tone={doNothing ? "neutral" : "accent"} className="font-mono text-sm">
                {action.kind}
              </Badge>
              <div className="text-right">
                <div className="text-2xs uppercase tracking-wide text-text-muted">
                  Expected recovery
                </div>
                <div className="text-lg font-semibold tabular text-text-primary">
                  {inr(action.expected_recovery)}
                </div>
              </div>
            </div>
            {Object.keys(action.params).length > 0 && (
              <code className="mt-2 block text-xs text-text-muted">
                {JSON.stringify(action.params)}
              </code>
            )}
            <div className="mt-3 border-t border-border-subtle pt-3">
              <EvidencePath steps={action.evidence_path} title="Action rationale" />
            </div>
            <p className="mt-3 text-2xs text-text-muted">
              decision_id{" "}
              <span className="font-mono text-text-secondary">
                {action.decision_id}
              </span>{" "}
              · bounded &amp; auditable · simulated
            </p>
          </div>
        </Card>

        {/* Recent activity from audit */}
        <Card>
          <CardHeader
            title="Recent activity"
            subtitle="Audited decisions from this run (derived-from-run, window index not clock time)"
          />
          <div className="p-2">
            {audit.isLoading ? (
              <div className="p-4 text-sm text-text-muted">Loading audit…</div>
            ) : audit.error ? (
              <div className="p-4 text-sm text-down">
                {audit.error instanceof Error
                  ? audit.error.message
                  : "Audit unavailable."}
              </div>
            ) : !audit.data || audit.data.entries.length === 0 ? (
              <div className="p-4 text-sm text-text-muted">
                No audited actions in this run.
              </div>
            ) : (
              <ul className="divide-y divide-border-subtle">
                {audit.data.entries.map((e, i) => (
                  <motion.li
                    key={e.decision_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center justify-between gap-3 px-3 py-2.5"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge
                          tone={e.action_kind === "do_nothing" ? "neutral" : "accent"}
                          className="font-mono"
                        >
                          {e.action_kind}
                        </Badge>
                        <span className="truncate text-2xs font-mono text-text-muted">
                          {e.decision_id}
                        </span>
                      </div>
                      <span className="text-2xs text-text-muted">
                        window {e.window} · {(e.confidence * 100).toFixed(0)}% conf
                      </span>
                    </div>
                    <span
                      className={cn(
                        "text-2xs",
                        e.audited ? "text-healthy" : "text-down"
                      )}
                    >
                      {e.audited ? "✓ audited" : "⚠ unaudited"}
                    </span>
                  </motion.li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
