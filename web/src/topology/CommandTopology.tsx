/**
 * <CommandTopology> — the living payment graph as an EMBEDDABLE instrument for the
 * Command Center. Unlike the full TopologyPage (which owns scenario controls + a
 * side panel), this renders just the graph, driven from a SimulateResponse passed
 * in by the composing page. It runs its own window playback and — critically —
 * opens on the DIAGNOSED frame (the representative window where the thesis is
 * visible), then lets the operator play/scrub. Pure composition of existing
 * topology building blocks; no new data logic, no fabrication.
 */
import { useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Button, cn } from "@/design/ui";
import type { SimulateResponse, Topology } from "@/lib";
import { PaymentGraph } from "./PaymentGraph";
import { buildGraph } from "./buildGraph";
import { useScenarioPlayback } from "./useScenarioPlayback";

/** Index of the representative (strongest-detection) window — where the story reads. */
function representativeIndex(res: SimulateResponse): number {
  let best = -1;
  let bestDropped = -1;
  res.windows.forEach((w, i) => {
    if (w.detection.triggered && w.detection.dropped_nodes.length > bestDropped) {
      best = i;
      bestDropped = w.detection.dropped_nodes.length;
    }
  });
  if (best >= 0) return best;
  const mid = Math.floor((res.incident.start_window + res.incident.end_window) / 2);
  const byWin = res.windows.findIndex((w) => w.window === mid);
  return byWin >= 0 ? byWin : Math.min(res.windows.length - 1, 0);
}

export function CommandTopology({
  topology,
  sim,
}: {
  topology: Topology;
  sim: SimulateResponse;
}) {
  const windows = sim.windows;
  const playback = useScenarioPlayback(windows.length);
  const repIdx = useMemo(() => representativeIndex(sim), [sim]);

  // Open on the diagnosed frame so the thesis is visible immediately (P1-8),
  // not the all-healthy window 0. Runs once per new simulation.
  useEffect(() => {
    playback.seek(repIdx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repIdx]);

  const win = windows[playback.index];

  // Reveal attribution once detection has fired at/through the current window.
  const diagnosed = useMemo(() => {
    for (let i = 0; i <= playback.index && i < windows.length; i++) {
      if (windows[i]?.detection.triggered) return true;
    }
    return false;
  }, [windows, playback.index]);

  const attribution = diagnosed ? sim.attribution : undefined;

  const rerouteToPsp = useMemo(() => {
    if (!diagnosed || sim.action.kind !== "reroute") return undefined;
    const past = playback.index >= Math.floor((windows.length * 2) / 3);
    if (!past) return undefined;
    const to = sim.action.params["to_psp"];
    return typeof to === "string" ? to : undefined;
  }, [diagnosed, sim.action, playback.index, windows.length]);

  const graph = useMemo(
    () => buildGraph({ topology, win, attribution, rerouteToPsp }),
    [topology, win, attribution, rerouteToPsp]
  );

  const atEnd = playback.count > 0 && playback.index >= playback.count - 1;

  return (
    <div className="relative flex h-full w-full flex-col">
      <div className="relative min-h-0 flex-1">
        <PaymentGraph nodes={graph.nodes} edges={graph.edges} showLegend={false} />
        {/* scrub control — floats bottom-center, unobtrusive */}
        <div className="pointer-events-none absolute inset-x-0 bottom-3 flex justify-center">
          <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-border-subtle bg-bg-surface/90 px-3 py-1.5 backdrop-blur">
            <Button
              variant="ghost"
              aria-label="Step back one window"
              disabled={playback.index <= 0}
              onClick={() => playback.step(-1)}
            >
              ◀
            </Button>
            <button
              onClick={() => (playback.playing ? playback.pause() : playback.play())}
              className="min-w-[92px] rounded-full bg-accent px-3 py-1 text-2xs font-semibold text-white transition-colors hover:bg-accent/90"
              aria-label={playback.playing ? "Pause" : atEnd ? "Replay" : "Play"}
            >
              {playback.playing ? "⏸ Pause" : atEnd ? "↻ Replay" : "▶ Play"}
            </button>
            <Button
              variant="ghost"
              aria-label="Step forward one window"
              disabled={atEnd}
              onClick={() => playback.step(1)}
            >
              ▶
            </Button>
            <span className="tabular ml-1 text-2xs text-text-muted" aria-live="polite">
              window {playback.index + 1}/{playback.count}
            </span>
          </div>
        </div>
      </div>
      {/* stage caption — narrates the current frame's meaning */}
      <StageCaption diagnosed={diagnosed} sim={sim} />
    </div>
  );
}

function StageCaption({ diagnosed, sim }: { diagnosed: boolean; sim: SimulateResponse }) {
  const kind = sim.attribution.root_cause_kind;
  const label = diagnosed
    ? kind === "bank"
      ? "Shared dependency identified — failures converge on one hidden bank"
      : kind === "psp"
      ? "Independent PSP faults — no shared upstream cause"
      : kind === "method"
      ? "Method-level fault across PSPs"
      : "Within noise — no action warranted"
    : "Observing traffic — watching for degradation";
  return (
    <motion.div
      key={label}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        "border-t border-border-subtle px-4 py-2 text-2xs",
        diagnosed && kind === "bank" ? "text-text-secondary" : "text-text-muted"
      )}
    >
      <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full align-middle"
        style={{ background: diagnosed ? "var(--tw-accent, #6d8bff)" : "#5e6b7e" }} />
      {label}
    </motion.div>
  );
}
