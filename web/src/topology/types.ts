/** Internal typed data carried on React Flow nodes/edges for the topology graph. */
import type { Node, Edge } from "@xyflow/react";
import type { Health } from "@/design/ui";

export interface MerchantNodeData extends Record<string, unknown> {
  label: string;
}
export interface MethodNodeData extends Record<string, unknown> {
  label: string;
  health: Health;
}
export interface PspNodeData extends Record<string, unknown> {
  label: string;
  bankId: string;
  health: Health;
  /** part of the highlighted attribution evidence path */
  onEvidencePath: boolean;
  /** a healthy reroute target during recovery */
  rerouteTarget: boolean;
}
export interface BankNodeData extends Record<string, unknown> {
  label: string;
  role: string;
  shared: boolean;
  pspIds: string[];
  health: Health;
  /** fraction of this bank's PSPs currently breached (0..1) */
  coverage: number;
  /** this bank is the attributed root cause of the active incident */
  isRootCause: boolean;
}

export type TopoNode =
  | Node<MerchantNodeData, "merchant">
  | Node<MethodNodeData, "method">
  | Node<PspNodeData, "psp">
  | Node<BankNodeData, "bank">;

export interface FlowEdgeData extends Record<string, unknown> {
  /** edge health drives particle speed: healthy=fast, degraded=slow, down=stopped */
  health: Health;
  /** on the highlighted attribution evidence path */
  highlighted: boolean;
  /** this edge is a live reroute (traffic moved here) */
  reroute: boolean;
}

export type TopoEdge = Edge<FlowEdgeData>;
