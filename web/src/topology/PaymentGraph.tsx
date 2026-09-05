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
}: {
  nodes: TopoNode[];
  edges: TopoEdge[];
}) {
  // stable references to the type maps
  const nt = useMemo(() => nodeTypes, []);
  const et = useMemo(() => edgeTypes, []);

  return (
    <div className="relative h-full w-full" aria-label="Payment dependency graph" role="img">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nt}
        edgeTypes={et}
        colorMode={"dark" as ColorMode}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll
        minZoom={0.4}
        maxZoom={1.6}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#1f2937" />
        <Controls showInteractive={false} className="!border-border-subtle !bg-bg-surface" />
        <Legend />
      </ReactFlow>
    </div>
  );
}
