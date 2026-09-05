/**
 * Audit log — derived from a single simulated run, honestly disclosed. The user
 * picks an incident type + seed (+ system + threshold); useAudit re-runs that one
 * scenario and returns the audit entries for the actions it produced. There is NO
 * persisted ledger and NO wall-clock time: the "window" column is a simulation
 * window index, and a banner states the source is derived-from-run.
 */
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useAudit, type IncidentTypeId, type SimulateRequest } from "@/lib";
import { Card, CardHeader, Badge, StatusDot } from "@/design/ui";
import { EmptyState, ErrorState, LoadingState } from "./States";

const INCIDENT_OPTIONS: { id: IncidentTypeId; label: string }[] = [
  { id: "A_shared_bank", label: "A — shared bank" },
  { id: "B_single_psp", label: "B — single PSP" },
  { id: "C_method", label: "C — method fault" },
  { id: "D_ambiguous", label: "D — ambiguous noise" },
  { id: "E_coincidental", label: "E — coincidental" },
];
const SEEDS = Array.from({ length: 20 }, (_, i) => i + 1);
const THRESHOLDS = [0.55, 0.7, 0.85];

function Disclosure() {
  return (
    <div
      role="note"
      className="flex items-start gap-2 rounded-lg border border-degraded/30 bg-degraded/10 px-3 py-2 text-2xs text-text-secondary"
    >
      <span className="mt-0.5">
        <StatusDot health="degraded" />
      </span>
      <p>
        <strong className="text-text-primary">derived-from-run.</strong> This reflects the current
        simulated run, not a persisted ledger. There is no stored history, no operator identity, and no
        wall-clock time — the <span className="font-mono">window</span> column is a simulation window
        index. Re-running the same (incident, seed, threshold, system) reproduces it exactly.
      </p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-2xs">
      <span className="uppercase tracking-wide text-text-muted">{label}</span>
      {children}
    </label>
  );
}

const selectCls =
  "rounded-lg border border-border-DEFAULT bg-bg-raised px-2.5 py-1.5 text-sm text-text-primary focus:border-accent focus:outline-none";

export function AuditView() {
  const [incidentType, setIncidentType] = useState<IncidentTypeId>("A_shared_bank");
  const [seed, setSeed] = useState(7);
  const [threshold, setThreshold] = useState(0.7);
  const [system, setSystem] = useState<"ariadne" | "baseline">("ariadne");

  const req: SimulateRequest = useMemo(
    () => ({ incident_type: incidentType, seed, intervention_threshold: threshold, system }),
    [incidentType, seed, threshold, system]
  );

  const { data, isPending, isError, error, refetch } = useAudit(req);

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <h1 className="text-lg font-semibold text-text-primary">Audit Log</h1>
        <p className="mt-1 max-w-3xl text-2xs text-text-muted">
          Every action ARIA takes is bounded and audited — it carries a decision id, the evidence
          path that justified it, and a confidence. Pick a scenario to see the audited actions that run
          produced.
        </p>
      </header>

      <Disclosure />

      <Card>
        <CardHeader title="Scenario" subtitle="Choose the run to audit — deterministic per selection" />
        <div className="flex flex-wrap items-end gap-3 p-4">
          <Field label="Incident type">
            <select className={selectCls} value={incidentType} onChange={(e) => setIncidentType(e.target.value as IncidentTypeId)}>
              {INCIDENT_OPTIONS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Seed">
            <select className={selectCls} value={seed} onChange={(e) => setSeed(Number(e.target.value))}>
              {SEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Threshold τ">
            <select className={selectCls} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}>
              {THRESHOLDS.map((t) => (
                <option key={t} value={t}>
                  {t.toFixed(2)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="System">
            <select className={selectCls} value={system} onChange={(e) => setSystem(e.target.value as "ariadne" | "baseline")}>
              <option value="ariadne">ariadne</option>
              <option value="baseline">baseline</option>
            </select>
          </Field>
        </div>
      </Card>

      {isPending && <LoadingState label="Deriving audit entries from the run…" />}

      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : "Unknown error contacting /api/audit"}
          onRetry={() => refetch()}
        />
      )}

      {!isPending && !isError && data && data.entries.length === 0 && (
        <EmptyState>
          This scenario produced no audited actions — for an ambiguous/noise incident the correct
          behaviour is often to do nothing, so there may be nothing to record.
        </EmptyState>
      )}

      {!isPending && !isError && data && data.entries.length > 0 && (
        <Card>
          <CardHeader
            title="Audited actions"
            subtitle={`${data.entries.length} action(s) · source: ${data.source}`}
            right={<Badge tone="info">{data.scenario.system}</Badge>}
          />
          <ul className="divide-y divide-border-subtle">
            {data.entries.map((e, i) => (
              <motion.li
                key={e.decision_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
                className="p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="neutral">window {e.window}</Badge>
                  <Badge tone="accent">{e.action_kind}</Badge>
                  <span className="font-mono text-2xs text-text-muted">{e.decision_id}</span>
                  <span className="ml-auto flex items-center gap-2">
                    <Badge tone={e.audited ? "healthy" : "down"}>{e.audited ? "audited" : "UNAUDITED"}</Badge>
                    <span className="tabular text-2xs text-text-secondary">conf {e.confidence.toFixed(2)}</span>
                  </span>
                </div>

                {Object.keys(e.params).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {Object.entries(e.params).map(([k, v]) => (
                      <span key={k} className="rounded border border-border-subtle bg-bg-raised px-1.5 py-0.5 font-mono text-2xs text-text-secondary">
                        {k}={String(v)}
                      </span>
                    ))}
                  </div>
                )}

                {e.evidence_path.length > 0 && (
                  <ol className="mt-2 space-y-0.5 border-l border-border-subtle pl-3">
                    {e.evidence_path.map((step, j) => (
                      <li key={j} className="font-mono text-2xs text-text-muted">
                        {step}
                      </li>
                    ))}
                  </ol>
                )}
              </motion.li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
