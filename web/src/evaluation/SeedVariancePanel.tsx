/**
 * Seed-aware honesty. The single most important anti-overclaim surface: it shows
 * rca_unconditional_per_seed and money_per_seed as small distributions so the
 * per-seed variance is visible. It explicitly does NOT imply ARIA wins every
 * seed — ties, near-zero seeds, and negative recoveries are called out.
 */
import type { Evaluation } from "@/lib";
import { Card, CardHeader, Badge } from "@/design/ui";
import { Sparkline } from "./Sparkline";
import { countAtOrBelow, countNegative, inr, mean, min } from "./format";

type Side = Evaluation["discrimination"]["incident_A_shared_bank"]["ariadne"];

function SeedRow({
  label,
  seeds,
  ariadne,
  baseline,
  tieExpected,
}: {
  label: string;
  seeds: number[];
  ariadne: Side;
  baseline: Side;
  tieExpected?: boolean;
}) {
  const negSeeds = countNegative(ariadne.money_per_seed);
  const lowRca = countAtOrBelow(ariadne.rca_unconditional_per_seed, 0.5);
  const worstMoney = min(ariadne.money_per_seed);

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-raised p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-text-primary">{label}</span>
        {tieExpected && <Badge tone="degraded">tie expected</Badge>}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <div className="mb-1 flex items-center justify-between text-2xs text-text-muted">
            <span>RCA per seed (unconditional)</span>
            <span className="tabular">mean {mean(ariadne.rca_unconditional_per_seed).toFixed(3)}</span>
          </div>
          <Sparkline
            values={ariadne.rca_unconditional_per_seed}
            seeds={seeds}
            warnAtOrBelow={0.5}
            ariaLabel={`${label} ARIA root-cause accuracy per seed`}
            format={(n) => n.toFixed(3)}
          />
          {lowRca > 0 && (
            <div className="mt-1 text-2xs text-degraded">
              {lowRca} seed(s) at or below 0.5 — shown, not hidden
            </div>
          )}
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-2xs text-text-muted">
            <span>Money recovered per seed</span>
            <span className="tabular">worst {inr(worstMoney)}</span>
          </div>
          <Sparkline
            values={ariadne.money_per_seed}
            seeds={seeds}
            warnAtOrBelow={0}
            ariaLabel={`${label} ARIA money recovered per seed`}
            format={(n) => inr(n)}
          />
          {negSeeds > 0 && (
            <div className="mt-1 text-2xs text-down">
              {negSeeds} seed(s) with NEGATIVE recovery — reported honestly, not clipped
            </div>
          )}
        </div>
      </div>
      <div className="mt-2 border-t border-border-subtle pt-2 text-2xs text-text-muted">
        Baseline mean RCA {mean(baseline.rca_unconditional_per_seed).toFixed(3)} · money {inr(baseline.money_recovered)}/seed
      </div>
    </div>
  );
}

export function SeedVariancePanel({ d, seeds }: { d: Evaluation["discrimination"]; seeds: number[] }) {
  return (
    <Card>
      <CardHeader
        title="Per-seed honesty"
        subtitle="Distribution across every seed — ARIA does not win every seed, and this shows it"
      />
      <div className="space-y-3 p-4">
        <SeedRow label="Incident A — shared bank" seeds={seeds} ariadne={d.incident_A_shared_bank.ariadne} baseline={d.incident_A_shared_bank.baseline} />
        <SeedRow label="Incident B — single PSP" seeds={seeds} ariadne={d.incident_B_single_psp.ariadne} baseline={d.incident_B_single_psp.baseline} />
        <SeedRow label="Incident E — coincidental" seeds={seeds} ariadne={d.incident_E_coincidental.ariadne} baseline={d.incident_E_coincidental.baseline} tieExpected />
        <p className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-2xs leading-relaxed text-text-secondary">
          <strong className="text-text-primary">Honest read:</strong> ARIA&apos;s decisive edge is on
          incident A (shared bank) specifically — that is where relational reasoning reaches a cause the
          baseline structurally cannot. Incident E is an <em>intentional tie</em>: matching the baseline
          there is the correct, non-over-attributing behaviour. Individual seeds vary, and any negative
          or tie above is shown rather than smoothed away.
        </p>
      </div>
    </Card>
  );
}
