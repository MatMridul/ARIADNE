/** Placeholder route pages. Feature agents build the feature folders
 * (topology/, incident/, evaluation/); the shell agent wires them in here.
 * Each page renders a labelled scaffold so the app builds and routes today. */
import type { ReactNode } from "react";
import { Card, CardHeader } from "@/design/ui";

function Scaffold({ title, note }: { title: string; note: string }) {
  return (
    <div className="mx-auto max-w-6xl">
      <Card>
        <CardHeader title={title} subtitle="Scaffold — feature implementation in progress" />
        <div className="p-6 text-sm text-text-secondary">{note}</div>
      </Card>
    </div>
  );
}

export function CommandCenterPage(): ReactNode {
  return <Scaffold title="Command Center" note="Overview: revenue at risk, topology preview, active diagnosis, recommended action, outcome." />;
}
export function TopologyPage(): ReactNode {
  return <Scaffold title="Payment Topology" note="Living payment graph: Merchant → Methods → PSPs → Banks, with the shared Bank-A dependency." />;
}
export function IncidentsPage(): ReactNode {
  return <Scaffold title="Incidents & RCA" note="Incident timeline → shared dependency → root cause → evidence → recovery action → measured outcome." />;
}
export function EvaluationPage(): ReactNode {
  return <Scaffold title="Evaluation" note="ARIA vs graph-blind baseline: discrimination result, recovery-vs-risk frontier, safety metrics." />;
}
export function AuditPage(): ReactNode {
  return <Scaffold title="Audit Log" note="Bounded, audited actions with decision_id, evidence path, and confidence (derived-from-run)." />;
}
