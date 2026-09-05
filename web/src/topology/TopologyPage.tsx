/**
 * <TopologyPage> — the default topology surface: the living payment graph +
 * scenario controls + a diagnosis side panel.
 *
 * Story staging over the incident window span (drives what the graph shows):
 *   before detection triggers          -> healthy graph, traffic flowing
 *   during the incident, once detected -> affected PSPs degrade/pulse, and the
 *                                         attribution highlights the evidence
 *                                         path converging onto the shared bank
 *   after diagnosis, if action=reroute -> the reroute target PSP + its edges
 *                                         light up (traffic moved to health)
 * Node/edge health for every window is DERIVED client-side (see deriveHealth.ts);
 * bank health in particular is inferred from its PSPs' deltas, never an API row.
 */
import { useMemo, useState } from "react";
import { Badge, Button, Card, CardHeader } from "@/design/ui";
import { useSimulate, useTopology, type IncidentTypeId } from "@/lib";
import { PaymentGraph } from "./PaymentGraph";
import { ScenarioControls, type ScenarioState } from "./ScenarioControls";
import { SidePanel } from "./SidePanel";
import { buildGraph } from "./buildGraph";
import { useScenarioPlayback } from "./useScenarioPlayback";

const DEFAULT_SCENARIO: ScenarioState = {
  incident: "A_shared_bank" as IncidentTypeId,
  seed: 7,
  system: "ariadne",
};
const THRESHOLD = 0.7;

function CenterCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="grid h-full place-items-center p-8">
      <Card className="max-w-md">
        <CardHeader title={title} />
        <div className="p-6 text-sm text-text-secondary">{children}</div>
      </Card>
    </div>
  );
}

export function TopologyPage() {
  const [scenario, setScenario] = useState<ScenarioState>(DEFAULT_SCENARIO);

  const topo = useTopology();
  const sim = useSimulate(
    {
      incident_type: scenario.incident,
      seed: scenario.seed,
      intervention_threshold: THRESHOLD,
      system: scenario.system,
    },
    // only fetch once the topology exists
    topo.isSuccess
  );

  const windows = sim.data?.windows ?? [];
  const playback = useScenarioPlayback(windows.length);
  const win = windows[playback.index];

  // Has the incident been diagnosed at/through the current window?
  // We reveal attribution once detection has triggered on this or an earlier
  // window (the story "converges" as you scrub forward).
  const diagnosed = useMemo(() => {
    if (!sim.data) return false;
    for (let i = 0; i <= playback.index && i < windows.length; i++) {
      if (windows[i]?.detection.triggered) return true;
    }
    return false;
  }, [sim.data, windows, playback.index]);

  const attribution = diagnosed ? sim.data?.attribution : undefined;

  // Reroute target only appears in the last third of the trace (post-recovery),
  // and only when the chosen action actually rerouted traffic.
  const rerouteToPsp = useMemo(() => {
    if (!sim.data || !diagnosed) return undefined;
    const act = sim.data.action;
    if (act.kind !== "reroute") return undefined;
    const past2of3 = playback.index >= Math.floor((windows.length * 2) / 3);
    if (!past2of3) return undefined;
    const to = act.params["to_psp"];
    return typeof to === "string" ? to : undefined;
  }, [sim.data, diagnosed, playback.index, windows.length]);

  const graph = useMemo(() => {
    if (!topo.data) return { nodes: [], edges: [] };
    return buildGraph({
      topology: topo.data,
      win,
      attribution,
      rerouteToPsp,
    });
  }, [topo.data, win, attribution, rerouteToPsp]);

  // ---- loading / error states for the topology query ------------------------
  if (topo.isLoading) {
    return (
      <CenterCard title="Loading topology…">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-ping rounded-full bg-accent" />
          Fetching the payment dependency graph.
        </div>
      </CenterCard>
    );
  }
  if (topo.isError) {
    return (
      <CenterCard title="Could not load topology">
        <p className="text-down">{(topo.error as Error)?.message ?? "Unknown error."}</p>
        <Button variant="secondary" className="mt-4" onClick={() => topo.refetch()}>
          Retry
        </Button>
      </CenterCard>
    );
  }
  if (!topo.data || topo.data.psps.length === 0) {
    return <CenterCard title="No topology">The graph is empty — nothing to render.</CenterCard>;
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <ScenarioControls
        state={scenario}
        onChange={setScenario}
        playback={playback}
        loading={sim.isFetching}
      />

      {/* thesis banner for the hero scenario */}
      {scenario.incident === "A_shared_bank" && (
        <div className="flex items-center gap-2 border-b border-border-subtle bg-bg-surface/60 px-4 py-1.5 text-2xs text-text-muted">
          <Badge tone="info">thesis</Badge>
          When <span className="text-text-secondary">Bank-A</span> fails, PSP-1 and PSP-2 both
          breach and converge on one hidden node — ARIA sees{" "}
          <span className="text-text-primary">one bank down</span>, a graph-blind monitor sees two
          independent PSP faults.
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <div className="relative min-w-0 flex-1">
          {sim.isError && (
            <div className="absolute inset-x-0 top-0 z-20 bg-down/15 px-4 py-2 text-2xs text-down">
              Simulation failed: {(sim.error as Error)?.message ?? "unknown error"} — the graph
              shows the static topology.
            </div>
          )}
          <PaymentGraph nodes={graph.nodes} edges={graph.edges} />
        </div>
        <SidePanel sim={sim.data} win={win} attribution={attribution} />
      </div>
    </div>
  );
}
