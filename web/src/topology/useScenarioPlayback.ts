/**
 * Playback state machine over a simulation's per-window trace.
 * Advances the current window index on a fixed interval when playing; exposes
 * play / pause / step / reset / seek. A single setInterval (cleared on unmount
 * and when not playing) — no rAF, no leak.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const STEP_MS = 900; // one window per ~0.9s when playing

export interface Playback {
  index: number;
  playing: boolean;
  count: number;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  step: (dir: 1 | -1) => void;
  reset: () => void;
  seek: (i: number) => void;
}

export function useScenarioPlayback(count: number): Playback {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clamp / reset the index whenever the trace length changes (new scenario).
  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [count]);

  useEffect(() => {
    if (!playing || count === 0) return;
    timer.current = setInterval(() => {
      setIndex((i) => {
        if (i >= count - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, STEP_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
    };
  }, [playing, count]);

  const play = useCallback(() => {
    setIndex((i) => (count > 0 && i >= count - 1 ? 0 : i)); // restart if at end
    setPlaying(count > 0);
  }, [count]);
  const pause = useCallback(() => setPlaying(false), []);
  const toggle = useCallback(() => setPlaying((p) => !p && count > 0), [count]);
  const step = useCallback(
    (dir: 1 | -1) => {
      setPlaying(false);
      setIndex((i) => Math.min(count - 1, Math.max(0, i + dir)));
    },
    [count]
  );
  const reset = useCallback(() => {
    setPlaying(false);
    setIndex(0);
  }, []);
  const seek = useCallback(
    (i: number) => {
      setPlaying(false);
      setIndex(Math.min(count - 1, Math.max(0, i)));
    },
    [count]
  );

  return { index, playing, count, play, pause, toggle, step, reset, seek };
}
