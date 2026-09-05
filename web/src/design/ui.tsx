/**
 * ARIA design-system primitives. Pure UI, no data, no API imports.
 * Feature folders compose these; they do not restyle from scratch.
 */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ReactNode, HTMLAttributes, ButtonHTMLAttributes } from "react";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type Health = "healthy" | "degraded" | "down" | "idle";

const HEALTH_COLOR: Record<Health, string> = {
  healthy: "bg-healthy",
  degraded: "bg-degraded",
  down: "bg-down",
  idle: "bg-border-strong",
};

export function StatusDot({ health, pulse }: { health: Health; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {pulse && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
            HEALTH_COLOR[health]
          )}
        />
      )}
      <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", HEALTH_COLOR[health])} />
    </span>
  );
}

export function Card({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border-subtle bg-bg-surface shadow-[0_1px_0_rgba(255,255,255,0.02)_inset]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  right,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between border-b border-border-subtle px-4 py-3">
      <div>
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        {subtitle && <p className="mt-0.5 text-2xs text-text-muted">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: "neutral" | "healthy" | "degraded" | "down" | "info" | "accent";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-bg-hover text-text-secondary border-border-DEFAULT",
    healthy: "bg-healthy/10 text-healthy border-healthy/30",
    degraded: "bg-degraded/10 text-degraded border-degraded/30",
    down: "bg-down/10 text-down border-down/30",
    info: "bg-info/10 text-info border-info/30",
    accent: "bg-accent/10 text-accent border-accent/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-2xs font-medium",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  const variants: Record<string, string> = {
    primary: "bg-accent text-white hover:bg-accent/90",
    secondary: "bg-bg-hover text-text-primary border border-border-DEFAULT hover:border-border-strong",
    ghost: "text-text-secondary hover:bg-bg-hover hover:text-text-primary",
    danger: "bg-down text-white hover:bg-down/90",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Metric({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: ReactNode;
  tone?: "healthy" | "degraded" | "down" | "default";
  hint?: string;
}) {
  const toneColor =
    tone === "healthy"
      ? "text-healthy"
      : tone === "degraded"
      ? "text-degraded"
      : tone === "down"
      ? "text-down"
      : "text-text-primary";
  return (
    <div className="px-4 py-3">
      <div className="text-2xs uppercase tracking-wide text-text-muted">{label}</div>
      <div className={cn("mt-1 text-2xl font-semibold tabular", toneColor)}>{value}</div>
      {hint && <div className="mt-0.5 text-2xs text-text-muted">{hint}</div>}
    </div>
  );
}

export function inr(n: number): string {
  const sign = n < 0 ? "-" : "";
  const a = Math.abs(Math.round(n));
  return `${sign}₹${a.toLocaleString("en-IN")}`;
}
