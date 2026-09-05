/**
 * <PaymentGraph> — the living payment topology rendered with React Flow.
 * Pure presentation: it receives already-built nodes/edges (see buildGraph.ts)
 * and the custom node/edge type maps. Non-interactive graph editing is disabled
 * (nodes are not draggable/connectable) — this is a visualization, not an editor.
 */
import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  type ColorMode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { nodeTypes } from "./nodes";
import { edgeTypes } from "./edges";
import { Legend } from "./Legend";
import type { TopoEdge, TopoNode } from "./types";

export function PaymentGraph({
  nodes,
  edges,
  showLegend = true,
}: {
  nodes: TopoNode[];
  edges: TopoEdge[];
  showLegend?: boolean;
}) {
  // stable references to the type maps
  const nt = useMemo(() => nodeTypes, []);
  const et = useMemo(() => edgeTypes, []);

  return (
    <div className="instrument-grid relative h-full w-full" aria-label="Payment dependency graph" role="img">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nt}
        edgeTypes={et}
        colorMode={"dark" as ColorMode}
        fitView
        fitViewOptions={{ padding: 0.24 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll
        minZoom={0.4}
        maxZoom={1.6}
      >
        <Background variant={BackgroundVariant.Dots} gap={40} size={0} color="transparent" />
        <Controls showInteractive={false} className="!border-border-subtle !bg-bg-surface" />
        {showLegend && <Legend />}
      </ReactFlow>
      <div className="instrument-vignette pointer-events-none absolute inset-0" />
    </div>
  );
}
