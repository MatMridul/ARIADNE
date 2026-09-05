/** Confidence ring — SVG arc that fills to `value` (0..1), tone by threshold. */
import { motion } from "framer-motion";
import { cn } from "@/design/ui";
import { confidenceHealth } from "./helpers";

const HEALTH_STROKE: Record<string, string> = {
  healthy: "#2dd4a7",
  degraded: "#f5a623",
  down: "#f45b6c",
  idle: "#3a4a5f",
};

export function ConfidenceRing({
  value,
  size = 96,
  label = "confidence",
}: {
  value: number;
  size?: number;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const health = confidenceHealth(clamped);
  const color = HEALTH_STROKE[health];

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label} ${(clamped * 100).toFixed(0)} percent`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#1f2937"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - clamped) }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn("text-xl font-semibold tabular")}
          style={{ color }}
        >
          {(clamped * 100).toFixed(0)}%
        </span>
        <span className="text-2xs uppercase tracking-wide text-text-muted">
          {label}
        </span>
      </div>
    </div>
  );
}
