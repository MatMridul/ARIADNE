/** Command Center — ARIADNE's operating instrument.
 *
 * Recomposed (emergency submission pass): NOT a card grid. The living payment
 * network is the protagonist and occupies the majority of the viewport; a right
 * intelligence rail explains it (incident → diagnosis → confidence → evidence →
 * claim), a recovery control strip presents the bounded action as an operational
 * decision, and a causal ribbon (DETECTED → DIAGNOSED → INTERVENTION → RECOVERED)
 * makes the reasoning chain legible at a glance.
 *
 * Composition only: the real <CommandTopology> graph (topology feature) is embedded
 * here, driven by the SAME /api/simulate trace that feeds the intelligence rail.
 * Every value is real API data — nothing hardcoded or fabricated.
 */
import { useState } from "react";
import { motion } from "framer-motion";
import { Badge, StatusDot, cn, inr } from "@/design/ui";
import { useSimulate, useTopology, type SimulateRequest } from "@/lib";
import { CommandTopology } from "@/topology";
import {
  ConfidenceRing,
  ErrorState,
  LoadingState,
  RecoveryConsole,
  prettyNodeId,
  representativeWindow,
  windowSuccessRate,
} from "@/incident";

// Opens on the hero / thesis scenario. Real, deterministic, reproducible.
const DEFAULT_REQ: SimulateRequest = {
  incident_type: "A_shared_bank",
  seed: 7,
  intervention_threshold: 0.7,
  system: "ariadne",
};

export function CommandCenterPage() {
  const [req] = useState<SimulateRequest>(DEFAULT_REQ);
  const topo = useTopology();
  const sim = useSimulate(req, topo.isSuccess);

  if (topo.isLoading || sim.isLoading) return <LoadingState label="Bringing the payment network online…" />;
  if (topo.error) return <ErrorState error={topo.error} onRetry={() => topo.refetch()} />;
  if (sim.error) return <ErrorState error={sim.error} onRetry={() => sim.refetch()} />;
  if (!topo.data || !sim.data) return <LoadingState label="Loading command center…" />;

  const res = sim.data;
  const rep = representativeWindow(res);
  const attr = res.attribution;
  const action = res.action;
  const doNothing = action.kind === "do_nothing";
  const negative = res.money_recovered < 0;
  const successRate = windowSuccessRate(rep);
  const incidentActive = rep.detection.dropped_nodes.length > 0;

  // claim status is SEPARATE from confidence (P: do not conflate)
  const claimLabel =
    attr.root_cause_kind === "none" ? "no cause" : `${attr.claim_type} · derived`;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* ── run context strip ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border-subtle px-5 py-2.5">
        <div className="flex items-baseline gap-3">
          <h1 className="text-sm font-semibold tracking-tight text-text-primary">Command Center</h1>
          <span className="tabular text-2xs text-text-muted">
            {res.incident.incident_type} · seed {req.seed} · τ{req.intervention_threshold.toFixed(2)} · ariadne
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="tabular text-2xs text-text-muted">
            window {rep.window}/{res.incident.n_windows}
          </span>
          <Badge tone={incidentActive ? "down" : "healthy"}>
            <StatusDot health={incidentActive ? "down" : "healthy"} pulse={incidentActive} />
            {incidentActive ? "incident active" : "nominal"}
          </Badge>
        </div>
      </div>

      {/* ── KPI ledger (a thin instrument row, not four cards) ─────────── */}
      <div className="grid grid-cols-2 border-b border-border-subtle sm:grid-cols-4">
        <Kpi label="Revenue recovered" value={inr(res.money_recovered)} tone={negative ? "down" : "healthy"} hint="measured counterfactual" />
        <Kpi label="Expected recovery" value={inr(action.expected_recovery)} tone="default" hint="estimate" divider />
        <Kpi label="Success rate" value={`${(successRate * 100).toFixed(1)}%`} tone={successRate < 0.9 ? "degraded" : "healthy"} hint={`window ${rep.window}`} divider />
        <Kpi label="Incident" value={res.incident.incident_type.split("_")[0]} tone={incidentActive ? "down" : "default"} hint={res.incident.target_id ?? "—"} divider />
      </div>

      {/* ── instrument body: graph (protagonist) + intelligence rail ──── */}
      <div className="flex min-h-0 flex-1">
        {/* PRIMARY: living payment network */}
        <section className="relative min-w-0 flex-1 border-r border-border-subtle" aria-label="Living payment network">
          <div className="absolute left-4 top-3 z-10 flex items-center gap-2">
            <span className="text-2xs uppercase tracking-widest text-text-muted">Payment network</span>
            <Badge tone="info">Bank-A shared · thesis</Badge>
          </div>
          <CommandTopology topology={topo.data} sim={res} />
        </section>

        {/* RIGHT INTELLIGENCE RAIL — explains the graph */}
        <aside className="flex w-[380px] shrink-0 flex-col overflow-y-auto bg-bg-base" aria-label="Diagnosis intelligence">
          {/* incident */}
          <RailBlock label="Incident">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-text-primary">
                {res.incident.target_id ? prettyNodeId(res.incident.target_id) : "—"} degradation
              </span>
              <Badge tone={incidentActive ? "down" : "neutral"} className="font-mono">{res.incident.incident_type.split("_")[0]}</Badge>
            </div>
            <p className="mt-1 text-2xs text-text-muted">
              windows {res.incident.start_window}–{res.incident.end_window} · {rep.detection.dropped_nodes.length} node(s) breached
            </p>
          </RailBlock>

          {/* diagnosis + confidence (SEPARATE concepts) */}
          <RailBlock label="Diagnosis">
            <div className="flex items-center gap-4">
              <ConfidenceRing value={attr.confidence} size={84} label="confidence" />
              <div className="min-w-0">
                <div className="text-2xs uppercase tracking-wide text-text-muted">root cause</div>
                <div className="truncate text-xl font-semibold text-text-primary">
                  {attr.root_cause_kind === "none" ? "No single cause" : prettyNodeId(attr.root_cause_id)}
                </div>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <Badge tone={attr.root_cause_kind === "bank" ? "down" : attr.root_cause_kind === "none" ? "neutral" : "degraded"} className="font-mono">
                    {attr.root_cause_kind}
                  </Badge>
                  {/* claim status is its own axis — not merged with confidence */}
                  <Badge tone="info">{claimLabel}</Badge>
                </div>
              </div>
            </div>
          </RailBlock>

          {/* evidence path — verbatim */}
          <RailBlock label="Evidence path">
            <ol className="space-y-1.5">
              {attr.evidence_path.map((line, i) => (
                <li key={i} className="flex gap-2 text-2xs leading-snug">
                  <span className="tabular shrink-0 text-text-muted">{i + 1}</span>
                  <span className={cn("font-mono", i === attr.evidence_path.length - 1 ? "text-text-primary" : "text-text-secondary")}>{line}</span>
                </li>
              ))}
            </ol>
          </RailBlock>

          {/* recovery — operational control, not a CTA card */}
          <div className="border-t border-border-subtle">
            <RecoveryConsole action={action} moneyRecovered={res.money_recovered} />
          </div>
        </aside>
      </div>

      {/* ── causal ribbon: DETECTED → DIAGNOSED → INTERVENTION → RECOVERED ── */}
      <CausalRibbon
        detected={incidentActive}
        diagnosed={attr.root_cause_kind !== "none"}
        intervened={!doNothing}
        recovered={res.money_recovered !== 0}
        money={res.money_recovered}
        action={action.kind}
        negative={negative}
      />
    </div>
  );
}

function Kpi({
  label,
  value,
  tone = "default",
  hint,
  divider,
}: {
  label: string;
  value: React.ReactNode;
  tone?: "healthy" | "degraded" | "down" | "default";
  hint?: string;
  divider?: boolean;
}) {
  const color =
    tone === "healthy" ? "text-healthy" : tone === "degraded" ? "text-degraded" : tone === "down" ? "text-down" : "text-text-primary";
  return (
    <div className={cn("px-5 py-3", divider && "border-l border-border-subtle")}>
      <div className="text-2xs uppercase tracking-wide text-text-muted">{label}</div>
      <div className={cn("tnum mt-0.5 text-2xl font-semibold", color)}>{value}</div>
      {hint && <div className="tabular mt-0.5 text-2xs text-text-muted">{hint}</div>}
    </div>
  );
}

function RailBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-border-subtle px-5 py-4">
      <div className="mb-2 text-2xs font-semibold uppercase tracking-widest text-text-muted">{label}</div>
      {children}
    </div>
  );
}

function CausalRibbon({
  detected,
  diagnosed,
  intervened,
  recovered,
  money,
  action,
  negative,
}: {
  detected: boolean;
  diagnosed: boolean;
  intervened: boolean;
  recovered: boolean;
  money: number;
  action: string;
  negative: boolean;
}) {
  const steps = [
    { key: "detected", label: "Detected", done: detected, detail: detected ? "degradation observed" : "monitoring" },
    { key: "diagnosed", label: "Diagnosed", done: diagnosed, detail: diagnosed ? "root cause attributed" : "—" },
    { key: "intervention", label: "Intervention", done: intervened, detail: intervened ? action : "do nothing" },
    { key: "recovered", label: "Recovered", done: recovered, detail: recovered ? inr(money) : "—", tone: negative ? "down" : "healthy" },
  ] as const;
  return (
    <div className="flex items-stretch border-t border-border-subtle bg-bg-surface">
      {steps.map((s, i) => (
        <div key={s.key} className={cn("flex flex-1 items-center gap-3 px-5 py-3", i > 0 && "border-l border-border-subtle")}>
          <motion.span
            initial={{ scale: 0.8, opacity: 0.4 }}
            animate={{ scale: s.done ? 1 : 0.8, opacity: s.done ? 1 : 0.4 }}
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full border text-2xs font-semibold",
              s.done
                ? (s as { tone?: string }).tone === "down"
                  ? "border-down text-down"
                  : "border-healthy text-healthy"
                : "border-border-strong text-text-muted"
            )}
          >
            {i + 1}
          </motion.span>
          <div className="min-w-0">
            <div className={cn("text-2xs font-semibold uppercase tracking-wide", s.done ? "text-text-secondary" : "text-text-muted")}>{s.label}</div>
            <div className={cn("tnum truncate text-xs", s.done ? "text-text-primary" : "text-text-muted")}>{s.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
