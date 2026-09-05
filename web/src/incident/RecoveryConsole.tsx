/** Recovery console — the operator decision surface.
 * EXECUTE reveals the measured money_recovered from the counterfactual;
 * DO NOTHING shows the safe default (₹0, no risk). Both are SIMULATED and
 * clearly labelled; money_recovered is a real shared-seed counterfactual and
 * MAY be negative (rendered honestly in red). */
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Badge, Button, Card, cn, inr } from "@/design/ui";
import type { Action } from "@/lib";
import { isDoNothing } from "./helpers";

type Choice = "execute" | "do_nothing" | null;

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

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-border-subtle px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">
            Recovery console
          </h3>
          <Badge tone="neutral">bounded &amp; auditable · simulated</Badge>
        </div>
        <p className="mt-1 text-2xs text-text-muted">
          Recommended action:{" "}
          <span className="font-mono text-text-secondary">{action.kind}</span>
          {" · decision "}
          <span className="font-mono text-text-secondary">
            {action.decision_id}
          </span>
        </p>
      </div>

      <div className="grid gap-3 p-4 sm:grid-cols-2">
        <Button
          variant={recommendedDoNothing ? "secondary" : "primary"}
          onClick={() => setChoice("execute")}
          aria-pressed={choice === "execute"}
          disabled={recommendedDoNothing}
          className="justify-center"
        >
          Execute {action.kind}
        </Button>
        <Button
          variant={recommendedDoNothing ? "primary" : "secondary"}
          onClick={() => setChoice("do_nothing")}
          aria-pressed={choice === "do_nothing"}
          className="justify-center"
        >
          Do nothing (safe default)
        </Button>
      </div>

      {recommendedDoNothing && (
        <p className="px-4 pb-2 text-2xs text-degraded">
          For this scenario the correct decision is to do nothing — Execute is
          disabled because there is no real cause to intervene on.
        </p>
      )}

      <AnimatePresence mode="wait">
        {choice === "execute" && (
          <motion.div
            key="execute"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border-subtle px-4 py-4"
          >
            <div className="text-2xs uppercase tracking-wide text-text-muted">
              Measured outcome (shared-seed counterfactual)
            </div>
            <div
              className={cn(
                "mt-1 text-3xl font-semibold tabular",
                negative ? "text-down" : "text-healthy"
              )}
            >
              {inr(moneyRecovered)}
            </div>
            <p className="mt-1 text-2xs text-text-muted">
              {negative
                ? "This action HURT revenue vs doing nothing — reported honestly, not clipped."
                : "Revenue recovered vs doing nothing, measured by re-running the same seed with the action applied."}
            </p>
          </motion.div>
        )}
        {choice === "do_nothing" && (
          <motion.div
            key="do_nothing"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border-subtle px-4 py-4"
          >
            <div className="text-2xs uppercase tracking-wide text-text-muted">
              Safe default
            </div>
            <div className="mt-1 text-3xl font-semibold tabular text-text-secondary">
              {inr(0)}
            </div>
            <p className="mt-1 text-2xs text-text-muted">
              No intervention, no risk of a false-positive action.
              {recommendedDoNothing
                ? " This is the correct choice here."
                : " ARIADNE would forgo the recovery above."}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
