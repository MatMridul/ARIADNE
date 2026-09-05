/**
 * The engineering-credibility surface. Wires useEvaluation() to the four panels:
 * discrimination headline, recovery-vs-risk frontier, safety metrics, and the
 * per-seed honesty distributions. Shows ONLY real data from the sweep.
 */
import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { useEvaluation } from "@/lib";
import { DiscriminationPanel } from "./DiscriminationPanel";
import { FrontierPanel } from "./FrontierPanel";
import { SafetyPanel } from "./SafetyPanel";
import { SeedVariancePanel } from "./SeedVariancePanel";
import { EmptyState, ErrorState, LoadingState } from "./States";

function Section({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

export function EvaluationView() {
  const { data, isPending, isError, error, refetch } = useEvaluation();

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-lg font-semibold text-text-primary">Evaluation</h1>
        <p className="mt-1 max-w-3xl text-2xs text-text-muted">
          ARIADNE vs a fair graph-blind baseline. The baseline sees every per-entity metric but not the
          dependency graph, so only relational reasoning is varied. All figures are measured across the
          seed batch — nothing on this page is fabricated.
        </p>
      </header>

      {isPending && <LoadingState />}

      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : "Unknown error contacting /api/evaluation"}
          onRetry={() => refetch()}
        />
      )}

      {!isPending && !isError && data && data.seeds.length === 0 && (
        <EmptyState>No seeds in the sweep — nothing to evaluate.</EmptyState>
      )}

      {!isPending && !isError && data && data.seeds.length > 0 && (
        <>
          <div className="text-2xs text-text-muted">
            Sweep over {data.seeds.length} seed(s) ({data.seeds[0]}–{data.seeds[data.seeds.length - 1]}) ·
            thresholds {data.thresholds.map((t) => t.toFixed(2)).join(" / ")}
          </div>
          <Section>
            <DiscriminationPanel d={data.discrimination} />
          </Section>
          <Section delay={0.05}>
            <FrontierPanel frontier={data.frontier} />
          </Section>
          <Section delay={0.1}>
            <SafetyPanel frontier={data.frontier} />
          </Section>
          <Section delay={0.15}>
            <SeedVariancePanel d={data.discrimination} seeds={data.seeds} />
          </Section>
        </>
      )}
    </div>
  );
}
