/**
 * The Shared Dependency Discrimination headline: ARIA vs the graph-blind
 * baseline on the three decisive incidents, plus the four boolean checks as
 * pass/fail chips. Incident A (shared bank) is the hero — baseline ~0.0 there.
 */
import type { Evaluation } from "@/lib";
import { Card, CardHeader, Badge } from "@/design/ui";
import { pct, inr } from "./format";

type Discrimination = Evaluation["discrimination"];

function CheckChip({ label, ok, hint }: { label: string; ok: boolean; hint: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-border-subtle bg-bg-raised px-3 py-2">
      <Badge tone={ok ? "healthy" : "down"} className="mt-0.5">
        {ok ? "PASS" : "FAIL"}
      </Badge>
      <div className="min-w-0">
        <div className="font-mono text-2xs text-text-primary">{label}</div>
        <div className="text-2xs text-text-muted">{hint}</div>
      </div>
    </div>
  );
}

/** A horizontal RCA comparison bar: ARIA (accent) over baseline (muted). */
function RcaBars({
  ariadne,
  baseline,
}: {
  ariadne: number;
  baseline: number;
}) {
  const row = (label: string, v: number, tone: string) => (
    <div className="flex items-center gap-3">
      <span className="w-16 shrink-0 text-2xs text-text-secondary">{label}</span>
      <div className="relative h-5 flex-1 overflow-hidden rounded bg-bg-raised">
        <div
          className={`h-full ${tone}`}
          style={{ width: `${Math.max(v * 100, v > 0 ? 2 : 0)}%` }}
        />
      </div>
      <span className="tabular w-14 shrink-0 text-right text-2xs text-text-primary">{pct(v)}</span>
    </div>
  );
  return (
    <div className="space-y-1.5">
      {row("ARIA", ariadne, "bg-accent")}
      {row("Baseline", baseline, "bg-border-strong")}
    </div>
  );
}

function IncidentCard({
  title,
  subtitle,
  hero,
  ariadneRca,
  baselineRca,
  ariadneMoney,
  baselineMoney,
  caption,
}: {
  title: string;
  subtitle: string;
  hero?: boolean;
  ariadneRca: number;
  baselineRca: number;
  ariadneMoney: number;
  baselineMoney: number;
  caption: string;
}) {
  return (
    <Card className={hero ? "ring-1 ring-accent/40" : ""}>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            {title}
            {hero && <Badge tone="accent">HERO · thesis</Badge>}
          </span>
        }
        subtitle={subtitle}
      />
      <div className="space-y-3 p-4">
        <div>
          <div className="mb-1 text-2xs uppercase tracking-wide text-text-muted">
            Root-cause accuracy (unconditional)
          </div>
          <RcaBars ariadne={ariadneRca} baseline={baselineRca} />
        </div>
        <div className="flex items-center justify-between border-t border-border-subtle pt-2 text-2xs">
          <span className="text-text-muted">Mean money recovered / seed</span>
          <span className="tabular text-text-secondary">
            <span className="text-accent">{inr(ariadneMoney)}</span>
            <span className="mx-1 text-text-muted">vs</span>
            {inr(baselineMoney)}
          </span>
        </div>
        <p className="text-2xs leading-relaxed text-text-muted">{caption}</p>
      </div>
    </Card>
  );
}

export function DiscriminationPanel({ d }: { d: Discrimination }) {
  const A = d.incident_A_shared_bank;
  const B = d.incident_B_single_psp;
  const E = d.incident_E_coincidental;

  return (
    <section aria-labelledby="discrimination-heading" className="space-y-4">
      <div>
        <h2 id="discrimination-heading" className="text-base font-semibold text-text-primary">
          Shared Dependency Discrimination
        </h2>
        <p className="mt-0.5 max-w-3xl text-2xs text-text-muted">
          The falsifiable test of ARIA&apos;s thesis: when two PSPs share one hidden bank, does
          relational reasoning name the bank where a graph-blind baseline sees only two independent
          PSP faults? Every number is measured across the seed batch — no fabricated values.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <IncidentCard
          title="Incident A — shared bank"
          subtitle="Bank-A down → PSP-1 & PSP-2 affected"
          hero
          ariadneRca={A.ariadne.root_cause_accuracy_unconditional}
          baselineRca={A.baseline.root_cause_accuracy_unconditional}
          ariadneMoney={A.ariadne.money_recovered}
          baselineMoney={A.baseline.money_recovered}
          caption="The decisive case. The baseline knows every per-PSP metric but not the dependency graph, so it cannot reach the shared bank — its accuracy here is ~0. This gap is the whole point."
        />
        <IncidentCard
          title="Incident B — single PSP"
          subtitle="One PSP down → control, no over-reach"
          ariadneRca={B.ariadne.root_cause_accuracy_unconditional}
          baselineRca={B.baseline.root_cause_accuracy_unconditional}
          ariadneMoney={B.ariadne.money_recovered}
          baselineMoney={B.baseline.money_recovered}
          caption="Regression guard: when the honest answer is a single PSP, ARIA must not do worse than the baseline. Both should blame the one PSP."
        />
        <IncidentCard
          title="Incident E — coincidental"
          subtitle="Two PSPs, different banks, drop by chance"
          ariadneRca={E.ariadne.root_cause_accuracy_unconditional}
          baselineRca={E.baseline.root_cause_accuracy_unconditional}
          ariadneMoney={E.ariadne.money_recovered}
          baselineMoney={E.baseline.money_recovered}
          caption="Anti-triviality control. A tie here is the CORRECT signature: ARIA must resist over-attributing to a bank when the two failures merely coincide. Winning E would mean it invents false shared causes."
        />
      </div>

      <Card>
        <CardHeader title="Discrimination checks" subtitle="Boolean pass/fail on the four thesis conditions" />
        <div className="grid gap-2 p-4 sm:grid-cols-2">
          <CheckChip
            label="A_ariadne_beats_baseline_rca"
            ok={d.A_ariadne_beats_baseline_rca}
            hint="On the shared-bank case, ARIA's root-cause accuracy exceeds the baseline's."
          />
          <CheckChip
            label="A_ariadne_beats_baseline_money"
            ok={d.A_ariadne_beats_baseline_money}
            hint="On the shared-bank case, ARIA recovers more money than the baseline."
          />
          <CheckChip
            label="B_no_regression"
            ok={d.B_no_regression}
            hint="On the single-PSP control, ARIA does not regress against the baseline."
          />
          <CheckChip
            label="E_ariadne_not_over_attributes"
            ok={d.E_ariadne_not_over_attributes}
            hint="On the coincidental case, ARIA does NOT over-attribute to a shared bank."
          />
        </div>
      </Card>
    </section>
  );
}
