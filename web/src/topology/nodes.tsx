/**
 * ARIA graph node language — NOT stock React Flow boxes.
 *
 * Every node reads as a domain OBJECT with an operational state:
 *  - a left STATUS SPINE (color = health) is the primary state channel,
 *  - a mono TYPE tag + object id is the identity (instrument telemetry),
 *  - object kinds have distinct silhouettes (merchant anchor, method channel,
 *    PSP infrastructure, bank dependency),
 *  - the SHARED bank is visually the heaviest node and structurally emphasized —
 *    it is the hidden dependency the whole thesis turns on.
 * Colors come from design tokens; motion is restrained (spine pulse when down).
 */
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { cn, type Health } from "@/design/ui";
import type {
  MerchantNodeData,
  MethodNodeData,
  PspNodeData,
  BankNodeData,
} from "./types";

const SPINE: Record<Health, string> = {
  healthy: "bg-healthy",
  degraded: "bg-degraded",
  down: "bg-down",
  idle: "bg-border-strong",
};

/** Shared object frame: left status spine + surface. Structure, not a rounded card. */
function ObjectFrame({
  health,
  width,
  emphasize,
  emphasizeTone = "accent",
  children,
}: {
  health: Health;
  width: number;
  emphasize?: boolean;
  emphasizeTone?: "accent" | "down";
  children: React.ReactNode;
}) {
  const down = health === "down";
  const degraded = health === "degraded";
  return (
    <div
      style={{ width }}
      className={cn(
        "relative flex overflow-hidden rounded-[3px] border bg-bg-surface/95",
        emphasize
          ? emphasizeTone === "down"
            ? "border-down/70"
            : "border-accent/70"
          : "border-border-DEFAULT",
        down && "bg-down/[0.06]",
        degraded && "bg-degraded/[0.05]"
      )}
    >
      {/* status spine */}
      <motion.span
        aria-hidden
        className={cn("w-[3px] shrink-0", SPINE[health])}
        animate={down ? { opacity: [1, 0.4, 1] } : { opacity: 1 }}
        transition={{ duration: 1.4, repeat: down ? Infinity : 0, ease: "easeInOut" }}
      />
      <div className="min-w-0 flex-1 px-2.5 py-2">{children}</div>
    </div>
  );
}

/** mono TYPE tag + object id — the instrument telemetry line. */
function TypeLine({ type, id }: { type: string; id: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-text-muted">
        {type}
      </span>
      <span className="tabular text-[9px] text-text-muted">{id}</span>
    </div>
  );
}

export function MerchantNode({ data }: NodeProps) {
  const d = data as MerchantNodeData;
  return (
    <ObjectFrame health="healthy" width={150}>
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <TypeLine type="Merchant" id="MX-01" />
      <div className="mt-0.5 text-[13px] font-semibold tracking-tight text-text-primary">
        {d.label}
      </div>
    </ObjectFrame>
  );
}

export function MethodNode({ data }: NodeProps) {
  const d = data as MethodNodeData;
  return (
    <ObjectFrame health={d.health} width={132}>
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <TypeLine type="Channel" id={d.label.toUpperCase()} />
      <div className="mt-0.5 text-[13px] font-semibold tracking-tight text-text-primary">
        {d.label}
      </div>
    </ObjectFrame>
  );
}

export function PspNode({ data }: NodeProps) {
  const d = data as PspNodeData;
  const idNum = d.label.replace(/\D/g, "");
  return (
    <ObjectFrame health={d.health} width={150} emphasize={d.onEvidencePath}>
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <TypeLine type="PSP" id={`PSP-${idNum}`} />
      <div className="mt-0.5 flex items-center justify-between">
        <span className="text-[13px] font-semibold tracking-tight text-text-primary">{d.label}</span>
        {d.onEvidencePath && (
          <span className="rounded-[2px] bg-accent/15 px-1.5 py-px text-[9px] font-semibold uppercase tracking-wide text-accent">
            evidence
          </span>
        )}
        {d.rerouteTarget && !d.onEvidencePath && (
          <span className="rounded-[2px] bg-healthy/15 px-1.5 py-px text-[9px] font-semibold uppercase tracking-wide text-healthy">
            reroute →
          </span>
        )}
      </div>
    </ObjectFrame>
  );
}

export function BankNode({ data }: NodeProps) {
  const d = data as BankNodeData;
  // Heaviest object in the graph — the hidden dependency. Shared-ness is a
  // structural motif: a doubled left edge + explicit "shared dependency" line.
  return (
    <div className="relative">
      {/* doubled edge motif for a SHARED bank: a second offset spine hints
          "multiple upstreams converge here" before you read a word */}
      {d.shared && (
        <span
          aria-hidden
          className={cn(
            "absolute -left-1 top-1 bottom-1 w-[3px] rounded-full",
            d.health === "down" ? "bg-down/50" : d.health === "degraded" ? "bg-degraded/50" : "bg-info/40"
          )}
        />
      )}
      <ObjectFrame
        health={d.health}
        width={190}
        emphasize={d.isRootCause}
        emphasizeTone="down"
      >
        <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
        <TypeLine type={`Bank · ${d.role}`} id={d.label.replace(/\s+/g, "").toUpperCase()} />
        <div className="mt-0.5 flex items-center justify-between">
          <span className="text-[13px] font-semibold tracking-tight text-text-primary">{d.label}</span>
          {d.isRootCause && (
            <span className="rounded-[2px] bg-down/15 px-1.5 py-px text-[9px] font-semibold uppercase tracking-wide text-down">
              root cause
            </span>
          )}
        </div>
        <div className="mt-1.5 flex items-center gap-1.5 border-t border-border-subtle pt-1.5">
          {d.shared ? (
            <span className="text-[9px] uppercase tracking-wide text-info">
              shared dependency · {d.pspIds.length} PSPs
            </span>
          ) : (
            <span className="text-[9px] uppercase tracking-wide text-text-muted">
              {d.pspIds.length} PSP
            </span>
          )}
          {d.coverage > 0 && (
            <span className="tabular ml-auto text-[9px] text-text-muted">
              {Math.round(d.coverage * 100)}% breached
            </span>
          )}
        </div>
      </ObjectFrame>
    </div>
  );
}

export const nodeTypes = {
  merchant: MerchantNode,
  method: MethodNode,
  psp: PspNode,
  bank: BankNode,
};
