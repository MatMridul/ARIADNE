/** Command Center — ARIA's operating instrument.
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
import { cn, inr } from "@/design/ui";
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

  return (
    <div className="flex h-full flex-col bg-bg-base">
      {/* ── quiet global header ───────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border-subtle px-6 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-[13px] font-semibold uppercase tracking-[0.14em] text-text-secondary">
            Command
          </h1>
          <span className="tabular text-[11px] text-text-muted">
            {res.incident.incident_type} · seed {req.seed} · τ{req.intervention_threshold.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="tabular text-[11px] text-text-muted">
            window {rep.window}/{res.incident.n_windows}
          </span>
          <span className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", incidentActive ? "bg-down" : "bg-healthy")} />
            <span className="text-[11px] font-medium text-text-secondary">
              {incidentActive ? "incident active" : "nominal"}
            </span>
          </span>
        </div>
      </div>

      {/* ── metric readout (baseline-aligned figures, NOT tiles) ──────── */}
      <div className="flex items-stretch gap-8 border-b border-border-subtle px-6 py-3">
        <Kpi label="Recovered" value={inr(res.money_recovered)} tone={negative ? "down" : "healthy"} sub="counterfactual" />
        <Kpi label="Expected" value={inr(action.expected_recovery)} sub="estimate" />
        <Kpi label="Success" value={`${(successRate * 100).toFixed(1)}%`} tone={successRate < 0.9 ? "degraded" : "default"} sub={`window ${rep.window}`} />
        <Kpi label="Incident" value={res.incident.incident_type.split("_")[0]} tone={incidentActive ? "down" : "default"} sub={res.incident.target_id ?? "—"} />
      </div>

      {/* ── instrument body: network (protagonist) + reasoning rail ───── */}
      <div className="flex min-h-0 flex-1">
        {/* PRIMARY: living payment network */}
        <section className="relative min-w-0 flex-1" aria-label="Living payment network">
          <div className="pointer-events-none absolute left-5 top-4 z-10 flex items-center gap-2.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
              Payment network
            </span>
            <span className="h-3 w-px bg-border-strong" />
            <span className="text-[10px] uppercase tracking-wide text-info">Bank-A · shared dependency</span>
          </div>
          <CommandTopology topology={topo.data} sim={res} />
        </section>

        {/* RIGHT REASONING RAIL — an operational readout, hairline-divided ── */}
        <aside className="flex w-[360px] shrink-0 flex-col overflow-y-auto border-l border-border-subtle bg-bg-inset" aria-label="Diagnosis readout">
          <RailBlock label="Incident">
            <div className="flex items-center justify-between">
              <span className="text-[15px] font-semibold tracking-tight text-text-primary">
                {res.incident.target_id ? prettyNodeId(res.incident.target_id) : "—"} degradation
              </span>
              <span className="tabular text-[11px] text-down">{res.incident.incident_type.split("_")[0]}</span>
            </div>
            <p className="tabular mt-1 text-[11px] text-text-muted">
              windows {res.incident.start_window}–{res.incident.end_window} · {rep.detection.dropped_nodes.length} node(s) breached
            </p>
          </RailBlock>

          <RailBlock label="Diagnosis">
            <div className="flex items-center gap-4">
              <ConfidenceRing value={attr.confidence} size={72} label="conf" />
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wide text-text-muted">root cause</div>
                <div className="truncate text-xl font-semibold tracking-tight text-text-primary">
                  {attr.root_cause_kind === "none" ? "No single cause" : prettyNodeId(attr.root_cause_id)}
                </div>
                <div className="mt-1.5 flex items-center gap-2 text-[11px]">
                  <span className="text-text-muted">kind</span>
                  <span className={cn("tabular font-medium", attr.root_cause_kind === "bank" ? "text-down" : "text-text-secondary")}>
                    {attr.root_cause_kind}
                  </span>
                  <span className="text-border-strong">·</span>
                  <span className="text-text-muted">claim</span>
                  <span className="tabular font-medium text-info">{attr.claim_type}</span>
                </div>
              </div>
            </div>
          </RailBlock>

          <RailBlock label="Evidence">
            <ol className="space-y-1.5">
              {attr.evidence_path.map((line, i) => (
                <li key={i} className="flex gap-2 text-[11px] leading-snug">
                  <span className="tabular shrink-0 text-text-muted">{String(i + 1).padStart(2, "0")}</span>
                  <span className={cn("tabular", i === attr.evidence_path.length - 1 ? "text-text-primary" : "text-text-secondary")}>{line}</span>
                </li>
              ))}
            </ol>
          </RailBlock>

          <div className="flex-1 border-t border-border-subtle">
            <RecoveryConsole action={action} moneyRecovered={res.money_recovered} />
          </div>
        </aside>
      </div>

      {/* ── causal sequence: DETECTED → DIAGNOSED → INTERVENTION → RECOVERED ── */}
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
  sub,
}: {
  label: string;
  value: React.ReactNode;
  tone?: "healthy" | "degraded" | "down" | "default";
  sub?: string;
}) {
  const color =
    tone === "healthy" ? "text-healthy" : tone === "degraded" ? "text-degraded" : tone === "down" ? "text-down" : "text-text-primary";
  return (
    <div className="flex flex-col justify-center">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-text-muted">{label}</div>
      <div className={cn("tnum text-[19px] font-semibold leading-tight tracking-tight", color)}>{value}</div>
      {sub && <div className="tabular text-[10px] text-text-muted">{sub}</div>}
    </div>
  );
}

function RailBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-border-subtle px-5 py-4">
      <div className="mb-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">{label}</div>
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
