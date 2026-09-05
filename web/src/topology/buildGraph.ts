/**
 * Build React Flow nodes + edges from the static topology and the CURRENT
 * simulation window. Node/edge health is derived every window (see
 * deriveHealth.ts) so the graph animates the incident story frame by frame.
 */
import type { Health } from "@/design/ui";
import type { Attribution, SimWindow, Topology } from "@/lib";
import {
  bankHealth,
  healthFromDelta,
  methodHealth,
  pspsForMethod,
  statsById,
} from "./deriveHealth";
import { layoutPositions } from "./layout";
import type {
  BankNodeData,
  FlowEdgeData,
  MethodNodeData,
  PspNodeData,
  TopoEdge,
  TopoNode,
} from "./types";

/** Worse of two healths (down > degraded > healthy > idle). */
function worse(a: Health, b: Health): Health {
  const rank: Record<Health, number> = { idle: 0, healthy: 1, degraded: 2, down: 3 };
  return rank[a] >= rank[b] ? a : b;
}

export interface BuiltGraph {
  nodes: TopoNode[];
  edges: TopoEdge[];
}

export interface BuildInput {
  topology: Topology;
  /** current window (undefined => all-healthy baseline view) */
  win?: SimWindow;
  /** attribution to highlight once the incident is diagnosed (undefined => none) */
  attribution?: Attribution;
  /** reroute target PSP id, if a recovery action moved traffic (undefined => none) */
  rerouteToPsp?: string;
}

export function buildGraph({
  topology,
  win,
  attribution,
  rerouteToPsp,
}: BuildInput): BuiltGraph {
  const pos = layoutPositions(topology);
  const stats = statsById(win);

  const evidencePsps = new Set(attribution?.psp_causes ?? []);
  const rootBankId =
    attribution?.root_cause_kind === "bank" ? attribution.root_cause_id : undefined;

  // ---- nodes ---------------------------------------------------------------
  const nodes: TopoNode[] = [];

  nodes.push({
    id: topology.merchant.id,
    type: "merchant",
    position: { x: pos[topology.merchant.id].x, y: pos[topology.merchant.id].y },
    data: { label: topology.merchant.label },
  });

  for (const m of topology.methods) {
    const routed = pspsForMethod(topology, m.id);
    const data: MethodNodeData = {
      label: m.label,
      health: methodHealth(m.id, routed, stats),
    };
    nodes.push({ id: m.id, type: "method", position: { x: pos[m.id].x, y: pos[m.id].y }, data });
  }

  for (const p of topology.psps) {
    const data: PspNodeData = {
      label: p.label,
      bankId: p.bank_id,
      health: healthFromDelta(stats[p.id]),
      onEvidencePath: evidencePsps.has(p.id),
      rerouteTarget: rerouteToPsp === p.id,
    };
    nodes.push({ id: p.id, type: "psp", position: { x: pos[p.id].x, y: pos[p.id].y }, data });
  }

  for (const b of topology.banks) {
    const bh = bankHealth(b.psps, stats);
    const data: BankNodeData = {
      label: b.label,
      role: b.role,
      shared: b.shared,
      pspIds: b.psps,
      health: bh.health,
      coverage: bh.coverage,
      isRootCause: rootBankId === b.id,
    };
    nodes.push({ id: b.id, type: "bank", position: { x: pos[b.id].x, y: pos[b.id].y }, data });
  }

  // ---- edges ---------------------------------------------------------------
  const edges: TopoEdge[] = [];
  const nodeHealth = new Map<string, Health>();
  for (const n of nodes) nodeHealth.set(n.id, (n.data as { health?: Health }).health ?? "healthy");

  function edgeData(from: string, to: string, opts?: Partial<FlowEdgeData>): FlowEdgeData {
    const h = worse(nodeHealth.get(from) ?? "healthy", nodeHealth.get(to) ?? "healthy");
    return { health: h, highlighted: false, reroute: false, ...opts };
  }

  // Merchant -> Method
  for (const m of topology.methods) {
    edges.push({
      id: `e-merchant-${m.id}`,
      source: topology.merchant.id,
      target: m.id,
      type: "flow",
      data: edgeData(topology.merchant.id, m.id),
    });
  }

  // Method -> PSP (per routing row)
  for (const r of topology.routing) {
    if (r.weight <= 0) continue;
    const isReroute = rerouteToPsp === r.psp_id;
    edges.push({
      id: `e-${r.method}-${r.psp_id}`,
      source: r.method,
      target: r.psp_id,
      type: "flow",
      data: edgeData(r.method, r.psp_id, { reroute: isReroute }),
    });
  }

  // PSP -> Bank (settlement). Highlight edges on the evidence path converging
  // onto the shared root-cause bank — the visual crux of the thesis.
  for (const p of topology.psps) {
    const highlighted = evidencePsps.has(p.id) && rootBankId === p.bank_id;
    edges.push({
      id: `e-${p.id}-${p.bank_id}`,
      source: p.id,
      target: p.bank_id,
      type: "flow",
      data: edgeData(p.id, p.bank_id, { highlighted }),
    });
  }

  return { nodes, edges };
}
