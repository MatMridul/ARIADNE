/** Shared loading / error / empty states for the incident surfaces. */
import { Button, Card } from "@/design/ui";

export function LoadingState({ label = "Running simulation…" }: { label?: string }) {
  return (
    <Card className="flex flex-col items-center justify-center gap-3 p-10">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-border-DEFAULT border-t-accent" />
      <p className="text-sm text-text-secondary">{label}</p>
    </Card>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const message =
    error instanceof Error ? error.message : "Something went wrong.";
  return (
    <Card className="flex flex-col items-start gap-3 border-down/40 p-6">
      <div>
        <h3 className="text-sm font-semibold text-down">Simulation failed</h3>
        <p className="mt-1 text-sm text-text-secondary">{message}</p>
        <p className="mt-2 text-2xs text-text-muted">
          The backend must be running (uvicorn web.api.main:app). All numbers on
          these surfaces come from the live core — nothing is mocked.
        </p>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Card>
  );
}

export function EmptyState({ label }: { label: string }) {
  return (
    <Card className="p-8 text-center text-sm text-text-muted">{label}</Card>
  );
}

/** Small banner reminding the operator these are simulated scenarios (vision §20). */
export function SimulatedDisclosure({ className }: { className?: string }) {
  return (
    <p className={className ?? "text-2xs text-text-muted"}>
      Simulated scenario — deterministic per (type, seed, threshold). Actions are
      bounded &amp; auditable; money figures are real shared-seed counterfactuals,
      not a production incident stream.
    </p>
  );
}
