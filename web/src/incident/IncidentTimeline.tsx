/** The incident story as a stepped timeline driven by a useSimulate() trace.
 * States: Healthy -> Degradation -> Graph reasoning -> Attribution -> Decision
 * -> Outcome. Each step is derived from real trace fields; framer-motion is used
 * for meaningful entrance transitions (each step animates in as the story
 * unfolds), not decoration. */
import { motion } from "framer-motion";
import { Badge, Card, StatusDot, cn, inr } from "@/design/ui";
import type { SimulateResponse } from "@/lib";
import {
  deltaHealth,
  droppedPspStats,
  firstDegradationWindow,
  healthyControlStats,
  INCIDENT_META,
  prettyNodeId,
  representativeWindow,
} from "./helpers";
import { ConfidenceRing } from "./ConfidenceRing";
import { EvidencePath } from "./EvidencePath";

function Step({
  index,
  title,
  children,
  tone = "neutral",
}: {
  index: number;
  title: string;
  children: React.ReactNode;
  tone?: "neutral" | "degraded" | "down" | "healthy" | "accent";
}) {
  const dot: Record<string, string> = {
    neutral: "border-border-strong text-text-secondary",
    degraded: "border-degraded text-degraded",
    down: "border-down text-down",
    healthy: "border-healthy text-healthy",
    accent: "border-accent text-accent",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.4, delay: 0.04 * index }}
      className="relative pl-10"
    >
      <span
        className={cn(
          "absolute left-0 top-0 flex h-7 w-7 items-center justify-center rounded-full border-2 bg-bg-base text-xs font-semibold",
          dot[tone]
        )}
      >
        {index + 1}
      </span>
      <div className="pb-8">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-text-secondary">
          {title}
        </h3>
        {children}
      </div>
    </motion.div>
  );
}

export function IncidentTimeline({ res }: { res: SimulateResponse }) {
  const rep = representativeWindow(res);
  const dropped = droppedPspStats(rep);
  const healthy = healthyControlStats(rep);
  const degradeWin = firstDegradationWindow(res);
  const attr = res.attribution;
  const action = res.action;
  const meta = INCIDENT_META[res.incident.incident_type as keyof typeof INCIDENT_META];
  const negative = res.money_recovered < 0;
  const doNothing = action.kind === "do_nothing";

  return (
    <div className="relative">
      {/* vertical spine */}
      <div className="absolute bottom-0 left-[13px] top-2 w-px bg-border-subtle" />

      <div className="space-y-0">
        {/* 1. Healthy */}
        <Step index={0} title="Healthy" tone="healthy">
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <StatusDot health="healthy" />
            Baseline steady state before window {res.incident.start_window}. All
            PSPs and methods at expected success rates.
          </div>
        </Step>

        {/* 2. Degradation */}
        <Step index={1} title="Degradation detected" tone="degraded">
          <p className="mb-2 text-sm text-text-secondary">
            {degradeWin !== null ? (
              <>
                Detection triggered at{" "}
                <span className="font-mono">window {degradeWin}</span>. Affected
                nodes from{" "}
                <span className="font-mono">detection.dropped_nodes</span>:
              </>
            ) : (
              <>No detection triggered — success stayed within noise band.</>
            )}
          </p>
          <div className="flex flex-wrap gap-2">
            {rep.detection.dropped_nodes.length === 0 && (
              <Badge tone="neutral">none</Badge>
            )}
            {rep.detection.dropped_nodes.map((n) => (
              <Badge key={n} tone="down" className="font-mono">
                {prettyNodeId(n)}
              </Badge>
            ))}
          </div>
          {dropped.length > 0 && (
            <div className="mt-3 grid gap-1.5">
              {dropped.map((n) => (
                <div
                  key={n.node_id}
                  className="flex items-center justify-between rounded-md border border-border-subtle bg-bg-surface px-3 py-1.5 text-xs"
                >
                  <span className="flex items-center gap-2 font-mono text-text-secondary">
                    <StatusDot health={deltaHealth(n.delta)} />
                    {prettyNodeId(n.node_id)}
                  </span>
                  <span className="tabular text-text-muted">
                    success {(n.success_rate * 100).toFixed(1)}% (Δ
                    {(n.delta * 100).toFixed(1)}pp)
                  </span>
                </div>
              ))}
            </div>
          )}
        </Step>

        {/* 3. Graph reasoning */}
        <Step index={2} title="Graph reasoning — shared dependency" tone="accent">
          <p className="mb-2 text-sm text-text-secondary">
            ARIA walks{" "}
            <span className="font-mono">attribution.psp_causes</span> up the
            dependency graph to see whether the failing PSPs converge on a shared
            upstream.
          </p>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {attr.psp_causes.length > 0 ? (
              <>
                {attr.psp_causes.map((p, i) => (
                  <span key={p} className="flex items-center gap-2">
                    <Badge tone="down" className="font-mono">
                      {prettyNodeId(p)}
                    </Badge>
                    {i < attr.psp_causes.length - 1 && (
                      <span className="text-text-muted">+</span>
                    )}
                  </span>
                ))}
                <span className="text-text-muted">→ settle via →</span>
                <Badge
                  tone={attr.root_cause_kind === "bank" ? "accent" : "neutral"}
                  className="font-mono"
                >
                  {attr.root_cause_kind === "bank"
                    ? prettyNodeId(attr.root_cause_id)
                    : "no shared upstream"}
                </Badge>
              </>
            ) : (
              <span className="text-text-muted">
                No converging PSP failures — nothing to trace upstream.
              </span>
            )}
          </div>
          {healthy.length > 0 && (
            <p className="mt-3 text-2xs text-text-muted">
              Control (stayed healthy, rules out alternatives):{" "}
              {healthy.map((h) => prettyNodeId(h.node_id)).join(", ")}
            </p>
          )}
        </Step>

        {/* 4. Attribution */}
        <Step index={3} title="Attribution — root cause" tone="down">
          <div className="grid gap-4 sm:grid-cols-[auto_1fr] sm:items-start">
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
              <div className="mb-3">
                <span className="text-2xs uppercase tracking-wide text-text-muted">
                  Root cause
                </span>
                <div className="text-lg font-semibold text-text-primary">
                  {attr.root_cause_kind === "none"
                    ? "No single cause"
                    : prettyNodeId(attr.root_cause_id)}
                </div>
              </div>
              <EvidencePath
                steps={attr.evidence_path}
                claimType={attr.claim_type}
              />
            </div>
          </div>
        </Step>

        {/* 5. Decision */}
        <Step index={4} title="Decision — recommended action" tone="accent">
          <Card className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <Badge tone={doNothing ? "neutral" : "accent"} className="font-mono">
                  {action.kind}
                </Badge>
                {Object.keys(action.params).length > 0 && (
                  <code className="ml-2 text-xs text-text-muted">
                    {JSON.stringify(action.params)}
                  </code>
                )}
              </div>
              <div className="text-right">
                <div className="text-2xs uppercase tracking-wide text-text-muted">
                  Expected recovery (estimate)
                </div>
                <div className="text-lg font-semibold tabular text-text-primary">
                  {inr(action.expected_recovery)}
                </div>
              </div>
            </div>
            {action.evidence_path.length > 0 && (
              <div className="mt-3 border-t border-border-subtle pt-3">
                <EvidencePath
                  steps={action.evidence_path}
                  title="Action rationale"
                />
              </div>
            )}
          </Card>
        </Step>

        {/* 6. Outcome */}
        <Step
          index={5}
          title="Outcome — measured"
          tone={doNothing ? "healthy" : negative ? "down" : "healthy"}
        >
          <Card
            className={cn(
              "p-4",
              negative ? "border-down/40" : doNothing ? "border-healthy/30" : "border-healthy/30"
            )}
          >
            <div className="text-2xs uppercase tracking-wide text-text-muted">
              Money recovered (real shared-seed counterfactual)
            </div>
            <div
              className={cn(
                "mt-1 text-3xl font-semibold tabular",
                negative ? "text-down" : doNothing ? "text-text-secondary" : "text-healthy"
              )}
            >
              {inr(res.money_recovered)}
            </div>
            {doNothing ? (
              <p className="mt-2 text-sm text-healthy">
                Correct outcome: {meta?.correct ?? "do nothing"} — no false
                intervention. This is a win, not a miss.
              </p>
            ) : negative ? (
              <p className="mt-2 text-sm text-down">
                This action reduced revenue vs doing nothing. Reported honestly,
                not clipped to zero.
              </p>
            ) : (
              <p className="mt-2 text-sm text-text-secondary">
                Revenue recovered relative to doing nothing, measured by
                re-running the identical seed with the action applied.
              </p>
            )}
          </Card>
        </Step>
      </div>
    </div>
  );
}
