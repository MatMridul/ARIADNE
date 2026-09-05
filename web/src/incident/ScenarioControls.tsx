/** Scenario controls — pick incident type, seed, intervention threshold, re-run.
 * A controlled component; the page owns the SimulateRequest state. */
import { Badge, Button, cn } from "@/design/ui";
import type { IncidentTypeId } from "@/lib";
import { INCIDENT_META, INCIDENT_ORDER, THRESHOLD_OPTIONS } from "./helpers";

export interface ScenarioState {
  incident_type: IncidentTypeId;
  seed: number;
  intervention_threshold: number;
}

export function ScenarioControls({
  value,
  onChange,
  isFetching,
}: {
  value: ScenarioState;
  onChange: (next: ScenarioState) => void;
  isFetching?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      {/* Incident type */}
      <div>
        <label className="mb-1.5 block text-2xs font-semibold uppercase tracking-wide text-text-muted">
          Incident type
        </label>
        <div className="flex flex-wrap gap-1.5">
          {INCIDENT_ORDER.map((id) => {
            const active = value.incident_type === id;
            return (
              <button
                key={id}
                type="button"
                aria-pressed={active}
                onClick={() => onChange({ ...value, incident_type: id })}
                className={cn(
                  "rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent/60",
                  active
                    ? "border-accent bg-accent/10 text-text-primary"
                    : "border-border-DEFAULT bg-bg-surface text-text-secondary hover:border-border-strong"
                )}
                title={INCIDENT_META[id].label}
              >
                <span className="font-mono">{id.split("_")[0]}</span>
                <span className="ml-1 hidden sm:inline">
                  {INCIDENT_META[id].label}
                </span>
                {INCIDENT_META[id].isThesis && (
                  <span className="ml-1 text-accent">★</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Seed */}
      <div>
        <label
          htmlFor="scenario-seed"
          className="mb-1.5 block text-2xs font-semibold uppercase tracking-wide text-text-muted"
        >
          Seed
        </label>
        <input
          id="scenario-seed"
          type="number"
          min={1}
          value={value.seed}
          onChange={(e) =>
            onChange({
              ...value,
              seed: Math.max(1, Number(e.target.value) || 1),
            })
          }
          className="w-20 rounded-lg border border-border-DEFAULT bg-bg-surface px-2.5 py-1.5 text-sm text-text-primary tabular focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60"
        />
      </div>

      {/* Intervention threshold */}
      <div>
        <label className="mb-1.5 block text-2xs font-semibold uppercase tracking-wide text-text-muted">
          Risk dial (intervention threshold)
        </label>
        <div className="flex gap-1.5">
          {THRESHOLD_OPTIONS.map((t) => {
            const active = Math.abs(value.intervention_threshold - t) < 1e-6;
            return (
              <button
                key={t}
                type="button"
                aria-pressed={active}
                onClick={() =>
                  onChange({ ...value, intervention_threshold: t })
                }
                className={cn(
                  "rounded-lg border px-2.5 py-1.5 text-xs font-medium tabular transition-colors focus:outline-none focus:ring-2 focus:ring-accent/60",
                  active
                    ? "border-accent bg-accent/10 text-text-primary"
                    : "border-border-DEFAULT bg-bg-surface text-text-secondary hover:border-border-strong"
                )}
              >
                {t.toFixed(2)}
              </button>
            );
          })}
        </div>
      </div>

      {isFetching && (
        <Badge tone="info" className="mb-1.5 animate-pulse">
          re-running…
        </Badge>
      )}
    </div>
  );
}
