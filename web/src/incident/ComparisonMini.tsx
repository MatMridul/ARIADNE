/** Baseline-vs-ARIADNE mini comparison, from SimulateResponse.comparison.
 * Shows what the graph-blind baseline concluded vs what ARIADNE concluded on
 * the SAME seed — the load-bearing thesis contrast. */
import { Badge, Card, cn, inr } from "@/design/ui";
import type { SimulateResponse } from "@/lib";
import { prettyNodeId } from "./helpers";

function Side({
  name,
  data,
  accent,
}: {
  name: string;
  data: { root_cause_id: string; root_cause_kind: string; confidence: number; money_recovered: number } | undefined;
  accent: boolean;
}) {
  if (!data) {
    return (
      <div className="flex-1 p-4 text-sm text-text-muted">
        {name}: not returned
      </div>
    );
  }
  const negative = data.money_recovered < 0;
  return (
    <div
      className={cn(
        "flex-1 p-4",
        accent && "bg-accent/5"
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-text-primary">{name}</span>
        {accent && <Badge tone="accent">graph-aware</Badge>}
        {!accent && <Badge tone="neutral">graph-blind</Badge>}
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-text-muted">Root cause</dt>
          <dd className="font-mono text-text-secondary">
            {prettyNodeId(data.root_cause_id)}{" "}
            <span className="text-text-muted">({data.root_cause_kind})</span>
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-text-muted">Confidence</dt>
          <dd className="tabular text-text-secondary">
            {(data.confidence * 100).toFixed(0)}%
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-text-muted">Money recovered</dt>
          <dd
            className={cn(
              "font-semibold tabular",
              negative ? "text-down" : "text-healthy"
            )}
          >
            {inr(data.money_recovered)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function ComparisonMini({ res }: { res: SimulateResponse }) {
  const ariadne = res.comparison["ariadne"];
  const baseline = res.comparison["baseline"];
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-border-subtle px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">
          ARIADNE vs graph-blind baseline
        </h3>
        <p className="mt-0.5 text-2xs text-text-muted">
          Same seed, same observations — only the dependency graph differs.
        </p>
      </div>
      <div className="flex flex-col divide-y divide-border-subtle sm:flex-row sm:divide-x sm:divide-y-0">
        <Side name="ARIADNE" data={ariadne} accent />
        <Side name="Baseline" data={baseline} accent={false} />
      </div>
    </Card>
  );
}
