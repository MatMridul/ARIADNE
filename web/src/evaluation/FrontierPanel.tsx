/**
 * Recovery-vs-false-intervention-cost frontier. x = false_intervention_cost,
 * y = money_recovered; one line per system (ariadne / baseline), one point per
 * intervention threshold (0.55 / 0.70 / 0.85). This is the "merchant chooses
 * aggressiveness" story: the product ships the frontier, not one tuned dial.
 */
import type { Evaluation, FrontierPoint } from "@/lib";
import {
  CartesianGrid,
  Label,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardHeader } from "@/design/ui";
import { inr } from "./format";

type Row = FrontierPoint & { system: "ARIA" | "Baseline" };

function toRows(points: FrontierPoint[], system: Row["system"]): Row[] {
  return [...points]
    .sort((a, b) => a.false_intervention_cost - b.false_intervention_cost)
    .map((p) => ({ ...p, system }));
}

function ThresholdTick(props: any) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null) return null;
  return (
    <text x={cx} y={cy - 10} textAnchor="middle" fontSize={10} fill="#9aa7b8" fontFamily="JetBrains Mono">
      τ={payload?.threshold?.toFixed(2)}
    </text>
  );
}

function FrontierTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const p: Row = payload[0].payload;
  return (
    <div className="rounded-lg border border-border-DEFAULT bg-bg-raised p-2.5 text-2xs shadow-lg">
      <div className="mb-1 font-semibold text-text-primary">
        {p.system} · threshold {p.threshold.toFixed(2)}
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-text-secondary">
        <dt>Money recovered</dt>
        <dd className="tabular text-right text-text-primary">{inr(p.money_recovered)}</dd>
        <dt>False-intervention cost</dt>
        <dd className="tabular text-right text-text-primary">{inr(p.false_intervention_cost)}</dd>
        <dt>False interventions</dt>
        <dd className="tabular text-right">{p.false_interventions_total}</dd>
        <dt>Executed actions</dt>
        <dd className="tabular text-right">{p.executed_actions}</dd>
        <dt>Unsafe-action rate</dt>
        <dd className="tabular text-right">{p.unsafe_action_rate.toFixed(4)}</dd>
      </dl>
    </div>
  );
}

export function FrontierPanel({ frontier }: { frontier: Evaluation["frontier"] }) {
  const ariadne = toRows(frontier.ariadne, "ARIA");
  const baseline = toRows(frontier.baseline, "Baseline");

  return (
    <Card>
      <CardHeader
        title="Recovery vs false-intervention-cost frontier"
        subtitle="One point per intervention threshold (τ) — the merchant chooses aggressiveness along the curve"
      />
      <div className="p-4">
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{ top: 24, right: 24, bottom: 32, left: 24 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="false_intervention_cost"
                stroke="#5e6b7e"
                tick={{ fontSize: 11, fill: "#9aa7b8" }}
                tickFormatter={(v) => inr(v)}
              >
                <Label value="False-intervention cost (₹) →" position="bottom" offset={12} fill="#5e6b7e" fontSize={11} />
              </XAxis>
              <YAxis
                type="number"
                dataKey="money_recovered"
                stroke="#5e6b7e"
                tick={{ fontSize: 11, fill: "#9aa7b8" }}
                tickFormatter={(v) => inr(v)}
              >
                <Label value="Money recovered (₹) →" angle={-90} position="left" offset={4} fill="#5e6b7e" fontSize={11} />
              </YAxis>
              <Tooltip content={<FrontierTooltip />} cursor={{ stroke: "#3a4a5f" }} />
              <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12 }} />
              <Line
                data={ariadne}
                dataKey="money_recovered"
                name="ARIA"
                stroke="#6d8bff"
                strokeWidth={2}
                dot={{ r: 4, fill: "#6d8bff" }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
                label={<ThresholdTick />}
              />
              <Line
                data={baseline}
                dataKey="money_recovered"
                name="Baseline"
                stroke="#5e6b7e"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 4, fill: "#5e6b7e" }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
              />
              {/* invisible scatter to guarantee both axes span all points */}
              <Scatter data={[...ariadne, ...baseline]} fill="transparent" legendType="none" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-2xs text-text-muted">
          Up-and-left is better: more money recovered for less false-intervention cost. Each ARIA
          point is labelled with its threshold τ. The frontier is the honest product claim — there is
          no single &quot;optimal&quot; dial baked in.
        </p>
      </div>
    </Card>
  );
}
