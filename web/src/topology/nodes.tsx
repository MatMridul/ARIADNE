/**
 * Custom React Flow node components for the payment topology.
 * All styling uses the frozen design tokens (bg.surface/raised, healthy/degraded/
 * down, text.*). Each node shows a status ring whose color encodes health.
 * The Bank node makes the SHARED dependency visually obvious.
 */
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { Badge, StatusDot, cn, type Health } from "@/design/ui";
import type {
  MerchantNodeData,
  MethodNodeData,
  PspNodeData,
  BankNodeData,
} from "./types";

const RING: Record<Health, string> = {
  healthy: "ring-healthy/40",
  degraded: "ring-degraded/70",
  down: "ring-down/80",
  idle: "ring-border-strong/30",
};

// Restrained depth — a thin status-tinted edge, not a neon halo (P1-5).
const GLOW: Record<Health, string> = {
  healthy: "",
  degraded: "shadow-[0_0_0_1px_rgba(245,166,35,0.35)]",
  down: "shadow-[0_0_0_1px_rgba(244,91,108,0.45)]",
  idle: "",
};

function Shell({
  health,
  pulse,
  emphasize,
  children,
  className,
}: {
  health: Health;
  pulse?: boolean;
  emphasize?: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  const unhealthy = health === "degraded" || health === "down";
  return (
    <motion.div
      // pulsing only when unhealthy — a tasteful breathing, not a strobe
      animate={
        pulse && unhealthy
          ? { scale: [1, 1.035, 1] }
          : { scale: 1 }
      }
      transition={{ duration: 1.6, repeat: pulse && unhealthy ? Infinity : 0, ease: "easeInOut" }}
      className={cn(
        "rounded-xl border border-border-subtle bg-bg-surface px-3 py-2.5 ring-2 ring-offset-0",
        RING[health],
        GLOW[health],
        emphasize && "border-accent/60 ring-accent/70",
        className
      )}
    >
      {children}
    </motion.div>
  );
}

export function MerchantNode({ data }: NodeProps) {
  const d = data as MerchantNodeData;
  return (
    <Shell health="healthy" className="w-[150px]">
      <Handle type="source" position={Position.Right} className="!bg-border-strong" />
      <div className="flex items-center gap-2.5">
        <span
          className="flex h-6 w-6 items-center justify-center rounded-md border border-border-strong bg-bg-raised text-[10px] font-semibold tracking-tight text-text-secondary"
          aria-hidden
        >
          MX
        </span>
        <div>
          <div className="text-2xs uppercase tracking-wide text-text-muted">Merchant</div>
          <div className="text-sm font-semibold text-text-primary">{d.label}</div>
        </div>
      </div>
    </Shell>
  );
}

export function MethodNode({ data }: NodeProps) {
  const d = data as MethodNodeData;
  return (
    <Shell health={d.health} pulse className="w-[140px]">
      <Handle type="target" position={Position.Left} className="!bg-border-strong" />
      <Handle type="source" position={Position.Right} className="!bg-border-strong" />
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xs uppercase tracking-wide text-text-muted">Method</div>
          <div className="text-sm font-semibold text-text-primary">{d.label}</div>
        </div>
        <StatusDot health={d.health} pulse={d.health !== "healthy"} />
      </div>
    </Shell>
  );
}

export function PspNode({ data }: NodeProps) {
  const d = data as PspNodeData;
  return (
    <Shell
      health={d.health}
      pulse
      emphasize={d.onEvidencePath}
      className="w-[150px]"
    >
      <Handle type="target" position={Position.Left} className="!bg-border-strong" />
      <Handle type="source" position={Position.Right} className="!bg-border-strong" />
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xs uppercase tracking-wide text-text-muted">PSP</div>
          <div className="text-sm font-semibold text-text-primary">{d.label}</div>
        </div>
        <StatusDot health={d.health} pulse={d.health !== "healthy"} />
      </div>
      {(d.onEvidencePath || d.rerouteTarget) && (
        <div className="mt-1.5">
          {d.onEvidencePath && <Badge tone="accent">evidence</Badge>}
          {d.rerouteTarget && <Badge tone="healthy">reroute →</Badge>}
        </div>
      )}
    </Shell>
  );
}

export function BankNode({ data }: NodeProps) {
  const d = data as BankNodeData;
  // The shared bank is the whole thesis: make the shared-ness impossible to miss.
  return (
    <Shell
      health={d.health}
      pulse
      emphasize={d.isRootCause}
      className={cn("w-[172px]", d.shared && "border-info/50")}
    >
      <Handle type="target" position={Position.Left} className="!bg-border-strong" />
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-2xs uppercase tracking-wide text-text-muted">
            Bank · {d.role}
          </div>
          <div className="text-sm font-semibold text-text-primary">{d.label}</div>
        </div>
        <StatusDot health={d.health} pulse={d.health !== "healthy"} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1">
        {d.shared ? (
          <Badge tone="info">SHARED · {d.pspIds.length} PSPs</Badge>
        ) : (
          <Badge tone="neutral">{d.pspIds.length} PSP</Badge>
        )}
        {d.isRootCause && <Badge tone="down">ROOT CAUSE</Badge>}
      </div>
      {d.shared && d.coverage > 0 && (
        <div className="mt-1 text-2xs text-text-muted">
          {Math.round(d.coverage * 100)}% of its PSPs breached
        </div>
      )}
    </Shell>
  );
}

export const nodeTypes = {
  merchant: MerchantNode,
  method: MethodNode,
  psp: PspNode,
  bank: BankNode,
};
