/** Incident / RCA / Recovery experience (F3+F5).
 * The incident story as a stepped timeline driven by a live useSimulate() trace,
 * with a recovery console and a baseline-vs-ARIA comparison. The operator
 * picks incident type + seed + intervention threshold and re-runs. */
import { useMemo, useState } from "react";
import { Badge, Card, CardHeader } from "@/design/ui";
import { useSimulate, type SimulateRequest } from "@/lib";
import { INCIDENT_META } from "./helpers";
import { ScenarioControls, type ScenarioState } from "./ScenarioControls";
import { IncidentTimeline } from "./IncidentTimeline";
import { RecoveryConsole } from "./RecoveryConsole";
import { ComparisonMini } from "./ComparisonMini";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SimulatedDisclosure,
} from "./States";

export function IncidentExperience() {
  const [scenario, setScenario] = useState<ScenarioState>({
    incident_type: "A_shared_bank",
    seed: 7,
    intervention_threshold: 0.7,
  });

  const req: SimulateRequest = useMemo(
    () => ({ ...scenario, system: "ariadne" }),
    [scenario]
  );

  const { data, isLoading, isFetching, error, refetch } = useSimulate(req);
  const meta = INCIDENT_META[scenario.incident_type];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Card>
        <CardHeader
          title="Incident · Root cause · Recovery"
          subtitle="The full story: what happened, why, what to do, and what happened after — every number from the live core."
          right={meta.isThesis ? <Badge tone="accent">★ thesis scenario</Badge> : undefined}
        />
        <div className="space-y-3 p-4">
          <ScenarioControls
            value={scenario}
            onChange={setScenario}
            isFetching={isFetching && !isLoading}
          />
          <div className="rounded-lg border border-border-subtle bg-bg-base px-3 py-2">
            <span className="text-2xs font-semibold uppercase tracking-wide text-text-muted">
              Expected correct behaviour
            </span>
            <p className="mt-0.5 text-sm text-text-secondary">{meta.correct}</p>
          </div>
          <SimulatedDisclosure />
        </div>
      </Card>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data ? (
        <EmptyState label="No trace yet — pick a scenario to simulate." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <Card className="p-6">
            <IncidentTimeline res={data} />
          </Card>
          <div className="space-y-6">
            <RecoveryConsole
              action={data.action}
              moneyRecovered={data.money_recovered}
            />
            <ComparisonMini res={data} />
          </div>
        </div>
      )}
    </div>
  );
}
