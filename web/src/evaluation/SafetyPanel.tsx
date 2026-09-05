/**
 * Safety metrics, measured — not asserted. unsafe_action_rate is presented as a
 * rate over the executed-action denominator (a hard 0.0 means "0 of N executed
 * actions were unsafe", shown with N). do_nothing_correct_rate is rendered at
 * full precision alongside its miss count so a 0.9988 does not read as a perfect
 * 1.00. Shown per intervention threshold.
 */
import type { Evaluation, FrontierPoint } from "@/lib";
import { Card, CardHeader, Badge } from "@/design/ui";
import { ratio, inr } from "./format";

function SafetyRow({ p }: { p: FrontierPoint }) {
  const unsafeSafe = p.unsafe_action_rate === 0;
  const perfectDoNothing = p.do_nothing_misses === 0;
  return (
    <tr className="border-t border-border-subtle">
      <td className="px-3 py-2 font-mono text-2xs text-text-primary">τ={p.threshold.toFixed(2)}</td>
      <td className="px-3 py-2 text-right">
        <span className="tabular text-text-primary">{ratio(p.unsafe_action_rate)}</span>
        <div className="text-2xs text-text-muted">
          {Math.round(p.unsafe_action_rate * p.executed_actions)} / {p.executed_actions} executed
        </div>
      </td>
      <td className="px-3 py-2 text-right">
        <span className="tabular text-text-primary">{ratio(p.do_nothing_correct_rate)}</span>
        <div className="text-2xs text-text-muted">of {p.do_nothing_scored} do-nothing windows</div>
      </td>
      <td className="px-3 py-2 text-right">
        <span className={`tabular ${perfectDoNothing ? "text-text-secondary" : "text-degraded"}`}>
          {p.do_nothing_misses}
        </span>
      </td>
      <td className="px-3 py-2 text-right">
        <span className="tabular text-text-secondary">{p.false_interventions_total}</span>
        <div className="text-2xs text-text-muted">{inr(p.false_intervention_cost)} cost</div>
      </td>
      <td className="px-3 py-2 text-right">
        <Badge tone={unsafeSafe ? "healthy" : "down"}>{unsafeSafe ? "SAFE" : "UNSAFE"}</Badge>
      </td>
    </tr>
  );
}

export function SafetyPanel({ frontier }: { frontier: Evaluation["frontier"] }) {
  const rows = [...frontier.ariadne].sort((a, b) => a.threshold - b.threshold);
  return (
    <Card>
      <CardHeader
        title="Safety metrics (ARIADNE)"
        subtitle="Measured from executed actions — unsafe rate is a rate over a real denominator, not an assertion"
      />
      <div className="overflow-x-auto p-1">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="text-left text-2xs uppercase tracking-wide text-text-muted">
              <th className="px-3 py-2 font-medium">Threshold</th>
              <th className="px-3 py-2 text-right font-medium">Unsafe-action rate</th>
              <th className="px-3 py-2 text-right font-medium">Do-nothing correct</th>
              <th className="px-3 py-2 text-right font-medium">Do-nothing misses</th>
              <th className="px-3 py-2 text-right font-medium">False interventions</th>
              <th className="px-3 py-2 text-right font-medium">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <SafetyRow key={p.threshold} p={p} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-4 pb-4 text-2xs text-text-muted">
        Rates are shown at full precision on purpose: a do-nothing-correct of 0.9988 is not 1.00, and
        its miss count is displayed so a near-perfect score never masks a real miss.
      </p>
    </Card>
  );
}
