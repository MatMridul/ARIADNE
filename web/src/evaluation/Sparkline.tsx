/**
 * A tiny inline SVG sparkline for per-seed distributions. Deliberately marks
 * points that undercut the "wins everywhere" story: values at or below a
 * `warnAtOrBelow` threshold (ties / losses) and negatives are drawn in the
 * degraded/down colours so per-seed variance is visible, not hidden.
 */
import { max, min } from "./format";

export function Sparkline({
  values,
  seeds,
  warnAtOrBelow,
  ariaLabel,
  format = (n) => n.toFixed(2),
  height = 34,
}: {
  values: number[];
  seeds?: number[];
  /** points <= this are drawn as degraded (ties/near-zero); negatives always down */
  warnAtOrBelow?: number;
  ariaLabel: string;
  format?: (n: number) => string;
  height?: number;
}) {
  if (values.length === 0) {
    return <span className="text-2xs text-text-muted">no per-seed data</span>;
  }
  const w = Math.max(values.length * 10, 60);
  const lo = Math.min(min(values), warnAtOrBelow ?? Infinity, 0);
  const hi = Math.max(max(values), 0);
  const span = hi - lo || 1;
  const pad = 4;
  const innerH = height - pad * 2;
  const x = (i: number) => (values.length === 1 ? w / 2 : (i / (values.length - 1)) * (w - pad * 2) + pad);
  const y = (v: number) => pad + innerH - ((v - lo) / span) * innerH;

  const zeroY = lo < 0 && hi > 0 ? y(0) : null;
  const path = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  const colorFor = (v: number) =>
    v < 0 ? "#f45b6c" : warnAtOrBelow !== undefined && v <= warnAtOrBelow ? "#f5a623" : "#6d8bff";

  return (
    <svg
      width={w}
      height={height}
      viewBox={`0 0 ${w} ${height}`}
      role="img"
      aria-label={ariaLabel}
      className="overflow-visible"
    >
      {zeroY !== null && (
        <line x1={0} x2={w} y1={zeroY} y2={zeroY} stroke="#2a3646" strokeWidth={1} strokeDasharray="2 2" />
      )}
      <path d={path} fill="none" stroke="#3a4a5f" strokeWidth={1.25} />
      {values.map((v, i) => (
        <circle key={i} cx={x(i)} cy={y(v)} r={2.4} fill={colorFor(v)}>
          <title>
            {seeds ? `seed ${seeds[i]}: ` : `#${i + 1}: `}
            {format(v)}
          </title>
        </circle>
      ))}
    </svg>
  );
}
