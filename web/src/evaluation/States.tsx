/**
 * Shared loading / error / empty states for the evaluation + audit surfaces.
 * Accessible (role + aria-live) and consistent with the design system.
 */
import type { ReactNode } from "react";
import { Card, Button } from "@/design/ui";

export function LoadingState({ label = "Running evaluation sweep…" }: { label?: string }) {
  return (
    <Card
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center gap-3 p-10 text-center"
    >
      <span
        className="h-6 w-6 animate-spin rounded-full border-2 border-border-strong border-t-accent"
        aria-hidden="true"
      />
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="text-2xs text-text-muted">Deterministic per (seeds, thresholds) — cached after first run.</p>
    </Card>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card role="alert" className="flex flex-col items-center justify-center gap-3 p-10 text-center">
      <div className="text-sm font-semibold text-down">Could not load evaluation data</div>
      <p className="max-w-md text-2xs text-text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Card>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <Card className="flex items-center justify-center p-10 text-center">
      <p className="text-sm text-text-muted">{children}</p>
    </Card>
  );
}
