/** Recommended intervention — an operational decision surface, NOT a CTA card.
 * Reads like an ops console: the intervention spec (kind + routing), expected
 * recovery, bounded-risk indicator, and two restrained operator controls.
 * EXECUTE reveals the REAL shared-seed money_recovered (may be negative, shown
 * honestly); DO NOTHING is the safe default. Everything simulated + labelled. */
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn, inr } from "@/design/ui";
import type { Action } from "@/lib";
import { isDoNothing } from "./helpers";

type Choice = "execute" | "do_nothing" | null;

function prettyPsp(id: unknown): string {
  return typeof id === "string" && id.startsWith("psp_") ? `PSP-${id.slice(4)}` : String(id ?? "");
}

export function RecoveryConsole({
  action,
  moneyRecovered,
}: {
  action: Action;
  moneyRecovered: number;
}) {
  const [choice, setChoice] = useState<Choice>(null);
  const recommendedDoNothing = isDoNothing(action.kind);
  const negative = moneyRecovered < 0;

  const method = typeof action.params["method"] === "string" ? (action.params["method"] as string).toUpperCase() : null;
  const from = prettyPsp(action.params["from_psp"]);
  const to = prettyPsp(action.params["to_psp"]);

  return (
    <div className="px-5 py-4">
      <div className="mb-2.5 flex items-center justify-between">
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
          Recommended intervention
        </div>
        <span className="tabular text-[9px] uppercase tracking-wide text-text-muted">bounded · auditable</span>
      </div>

      {/* intervention spec — instrument readout, not a button */}
      <div className="flex items-baseline gap-3">
        <span className="text-lg font-semibold uppercase tracking-tight text-text-primary">
          {action.kind === "do_nothing" ? "Hold" : action.kind}
        </span>
        {method && to && (
          <span className="tabular text-[12px] text-text-secondary">
            {method} · {from} <span className="text-accent">→</span> {to}
          </span>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border-subtle pt-3">
        <Field label="Expected recovery" value={inr(action.expected_recovery)} />
        <Field label="Risk" value="bounded" tone="healthy" />
        <Field label="Decision" value={action.decision_id || "—"} mono />
        <Field label="Confidence" value={`${Math.round(action.confidence * 100)}%`} />
      </div>

      {/* operator controls — restrained, framed, not CTAs */}
      <div className="mt-3 flex overflow-hidden rounded-[3px] border border-border-DEFAULT">
        <button
          onClick={() => setChoice("execute")}
          disabled={recommendedDoNothing}
          aria-pressed={choice === "execute"}
          className={cn(
            "flex-1 px-3 py-2 text-[12px] font-medium transition-colors focus:outline-none focus:ring-1 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-40",
            choice === "execute"
              ? "bg-accent/15 text-accent"
              : "bg-bg-hover text-text-secondary hover:text-text-primary"
          )}
        >
          Execute
        </button>
        <button
          onClick={() => setChoice("do_nothing")}
          aria-pressed={choice === "do_nothing"}
          className={cn(
            "flex-1 border-l border-border-DEFAULT px-3 py-2 text-[12px] font-medium transition-colors focus:outline-none focus:ring-1 focus:ring-accent",
            choice === "do_nothing"
              ? "bg-bg-hover text-text-primary"
              : "bg-bg-inset text-text-secondary hover:text-text-primary"
          )}
        >
          Do nothing
        </button>
      </div>

      {recommendedDoNothing && (
        <p className="mt-2 text-[10px] text-degraded">
          Correct call here is to do nothing — no real cause to intervene on. Execute disabled.
        </p>
      )}

      <AnimatePresence mode="wait">
        {choice === "execute" && (
          <motion.div
            key="x"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="mt-3 border-t border-border-subtle pt-3"
          >
            <div className="text-[10px] uppercase tracking-wide text-text-muted">measured outcome · counterfactual</div>
            <div className={cn("tnum mt-0.5 text-2xl font-semibold", negative ? "text-down" : "text-healthy")}>
              {inr(moneyRecovered)}
            </div>
            <p className="mt-1 text-[10px] text-text-muted">
              {negative
                ? "action reduced revenue vs holding — reported honestly, not clipped."
                : "revenue vs holding, from re-running the same seed with the action applied."}
            </p>
          </motion.div>
        )}
        {choice === "do_nothing" && (
          <motion.div
            key="d"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="mt-3 border-t border-border-subtle pt-3"
          >
            <div className="text-[10px] uppercase tracking-wide text-text-muted">safe default</div>
            <div className="tnum mt-0.5 text-2xl font-semibold text-text-secondary">{inr(0)}</div>
            <p className="mt-1 text-[10px] text-text-muted">
              no intervention, no false-positive risk.
              {recommendedDoNothing ? " correct here." : " forgoes the recovery above."}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Field({
  label,
  value,
  tone,
  mono,
}: {
  label: string;
  value: string;
  tone?: "healthy";
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-wide text-text-muted">{label}</div>
      <div
        className={cn(
          "truncate text-[12px] font-medium",
          mono && "tabular",
          tone === "healthy" ? "text-healthy" : "text-text-primary"
        )}
      >
        {value}
      </div>
    </div>
  );
}
