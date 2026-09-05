/** Scenario control bar — pick incident/seed/system and drive playback. */
import { Button, cn } from "@/design/ui";
import type { IncidentTypeId } from "@/lib";
import type { Playback } from "./useScenarioPlayback";

export interface ScenarioState {
  incident: IncidentTypeId;
  seed: number;
  system: "ariadne" | "baseline";
}

const INCIDENTS: { id: IncidentTypeId; label: string; thesis?: boolean }[] = [
  { id: "A_shared_bank", label: "A · Shared bank", thesis: true },
  { id: "B_single_psp", label: "B · Single PSP" },
  { id: "C_method", label: "C · Method fault" },
  { id: "D_ambiguous", label: "D · Noise dip" },
  { id: "E_coincidental", label: "E · Coincidental" },
];

export function ScenarioControls({
  state,
  onChange,
  playback,
  disabled,
  loading,
}: {
  state: ScenarioState;
  onChange: (s: ScenarioState) => void;
  playback: Playback;
  disabled?: boolean;
  loading?: boolean;
}) {
  const { index, count, playing } = playback;
  const atEnd = count > 0 && index >= count - 1;

  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border-subtle bg-bg-surface px-4 py-3">
      {/* incident selector */}
      <div role="radiogroup" aria-label="Incident scenario" className="flex flex-wrap gap-1">
        {INCIDENTS.map((inc) => {
          const active = state.incident === inc.id;
          return (
            <button
              key={inc.id}
              role="radio"
              aria-checked={active}
              aria-label={`Scenario ${inc.label}${inc.thesis ? " (thesis)" : ""}`}
              disabled={disabled}
              onClick={() => onChange({ ...state, incident: inc.id })}
              className={cn(
                "rounded-md border px-2.5 py-1 text-2xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent",
                active
                  ? "border-accent bg-accent/15 text-text-primary"
                  : "border-border-DEFAULT bg-bg-hover text-text-secondary hover:text-text-primary",
                inc.thesis && !active && "border-info/40"
              )}
            >
              {inc.label}
            </button>
          );
        })}
      </div>

      {/* system toggle */}
      <div role="radiogroup" aria-label="System" className="flex overflow-hidden rounded-md border border-border-DEFAULT">
        {(["ariadne", "baseline"] as const).map((sys) => (
          <button
            key={sys}
            role="radio"
            aria-checked={state.system === sys}
            disabled={disabled}
            onClick={() => onChange({ ...state, system: sys })}
            className={cn(
              "px-2.5 py-1 text-2xs font-medium capitalize transition-colors focus:outline-none focus:ring-2 focus:ring-accent",
              state.system === sys
                ? "bg-accent/15 text-text-primary"
                : "bg-bg-hover text-text-secondary hover:text-text-primary"
            )}
          >
            {sys}
          </button>
        ))}
      </div>

      {/* seed */}
      <label className="flex items-center gap-1.5 text-2xs text-text-muted">
        seed
        <input
          type="number"
          min={1}
          max={200}
          value={state.seed}
          disabled={disabled}
          aria-label="Random seed"
          onChange={(e) => onChange({ ...state, seed: Number(e.target.value) || 1 })}
          className="w-16 rounded-md border border-border-DEFAULT bg-bg-hover px-2 py-1 text-2xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
        />
      </label>

      <div className="ml-auto flex items-center gap-2">
        <span className="tabular text-2xs text-text-muted" aria-live="polite">
          {loading ? "running…" : count ? `window ${index + 1}/${count}` : "—"}
        </span>
        <Button variant="ghost" aria-label="Step back one window" disabled={disabled || index <= 0} onClick={() => playback.step(-1)}>◀</Button>
        <Button
          variant="secondary"
          aria-label={playing ? "Pause playback" : atEnd ? "Replay from start" : "Play scenario"}
          disabled={disabled || count === 0}
          onClick={() => (playing ? playback.pause() : playback.play())}
        >
          {playing ? "⏸ Pause" : atEnd ? "↻ Replay" : "▶ Play"}
        </Button>
        <Button variant="ghost" aria-label="Step forward one window" disabled={disabled || atEnd} onClick={() => playback.step(1)}>▶</Button>
      </div>
    </div>
  );
}
