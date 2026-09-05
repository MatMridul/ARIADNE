/** Evidence path — the "why", rendered verbatim as an ordered causal chain.
 * Never summarised or paraphrased; each string comes straight from the core. */
import { motion } from "framer-motion";
import { Badge } from "@/design/ui";

export function EvidencePath({
  steps,
  claimType,
  title = "Why — evidence path",
}: {
  steps: string[];
  claimType?: string;
  title?: string;
}) {
  if (steps.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        No evidence path produced for this window.
      </p>
    );
  }
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-2xs font-semibold uppercase tracking-wide text-text-muted">
          {title}
        </span>
        {claimType && (
          <Badge tone="info" className="font-mono">
            claim: {claimType}
          </Badge>
        )}
      </div>
      <ol className="space-y-2">
        {steps.map((step, i) => (
          <motion.li
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08, duration: 0.3 }}
            className="flex gap-3"
          >
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border-DEFAULT bg-bg-hover text-2xs font-semibold text-text-secondary">
              {i + 1}
            </span>
            <code className="text-xs leading-5 text-text-secondary">
              {step}
            </code>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
