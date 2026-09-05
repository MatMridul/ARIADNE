/**
 * ARIADNE API contract — Zod schemas + inferred TypeScript types.
 *
 * SINGLE source of truth for the API shape (web/CONTRACT.md). Every feature folder
 * imports types + hooks from `@/lib` and NOTHING defines API types or calls fetch
 * elsewhere. Schemas mirror the verified FastAPI responses in web/api/main.py.
 */
import { z } from "zod";

// ---- topology ----------------------------------------------------------------
export const NodeKind = z.enum(["psp", "method", "bank"]);

export const TopologySchema = z.object({
  merchant: z.object({ id: z.string(), label: z.string() }),
  methods: z.array(z.object({ id: z.string(), label: z.string() })),
  psps: z.array(
    z.object({ id: z.string(), label: z.string(), bank_id: z.string() })
  ),
  banks: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      role: z.string(),
      shared: z.boolean(),
      psps: z.array(z.string()),
    })
  ),
  routing: z.array(
    z.object({ method: z.string(), psp_id: z.string(), weight: z.number() })
  ),
  shared_banks: z.record(z.string(), z.array(z.string())),
});
export type Topology = z.infer<typeof TopologySchema>;

// ---- simulate ----------------------------------------------------------------
export const IncidentTypeEnum = z.enum([
  "A_shared_bank",
  "B_single_psp",
  "C_method",
  "D_ambiguous",
  "E_coincidental",
]);
export type IncidentTypeId = z.infer<typeof IncidentTypeEnum>;

export const NodeStatSchema = z.object({
  node_id: z.string(),
  node_kind: z.string(),
  success_rate: z.number(),
  baseline_rate: z.number(),
  delta: z.number(),
  volume: z.number(),
  avg_latency_ms: z.number(),
});
export type NodeStat = z.infer<typeof NodeStatSchema>;

export const AttributionSchema = z.object({
  root_cause_id: z.string(),
  root_cause_kind: z.enum(["bank", "psp", "method", "none"]),
  confidence: z.number(),
  evidence_path: z.array(z.string()),
  claim_type: z.string(),
  psp_causes: z.array(z.string()),
});
export type Attribution = z.infer<typeof AttributionSchema>;

export const ActionSchema = z.object({
  kind: z.enum(["reroute", "disable_method", "retry_fallback", "do_nothing"]),
  params: z.record(z.string(), z.any()),
  decision_id: z.string(),
  evidence_path: z.array(z.string()),
  confidence: z.number(),
  expected_recovery: z.number(),
});
export type Action = z.infer<typeof ActionSchema>;

export const WindowSchema = z.object({
  window: z.number(),
  detection: z.object({
    triggered: z.boolean(),
    dropped_nodes: z.array(z.string()),
  }),
  nodes: z.array(NodeStatSchema),
  attribution: AttributionSchema,
  action: ActionSchema,
});
export type SimWindow = z.infer<typeof WindowSchema>;

const ComparisonSideSchema = z.object({
  root_cause_id: z.string(),
  root_cause_kind: z.string(),
  confidence: z.number(),
  money_recovered: z.number(),
});

export const SimulateResponseSchema = z.object({
  incident: z.object({
    incident_type: z.string(),
    target_id: z.string().nullable(),
    secondary_target_id: z.string().nullable(),
    start_window: z.number(),
    end_window: z.number(),
    n_windows: z.number(),
  }),
  windows: z.array(WindowSchema),
  attribution: AttributionSchema,
  action: ActionSchema,
  money_recovered: z.number(),
  comparison: z.record(z.string(), ComparisonSideSchema),
});
export type SimulateResponse = z.infer<typeof SimulateResponseSchema>;

export interface SimulateRequest {
  incident_type: IncidentTypeId;
  seed: number;
  intervention_threshold: number;
  system: "ariadne" | "baseline";
}

// ---- evaluation --------------------------------------------------------------
const EvalSideSchema = z.object({
  root_cause_accuracy: z.number(),
  root_cause_accuracy_conditional: z.number(),
  root_cause_accuracy_unconditional: z.number(),
  rca_unconditional_per_seed: z.array(z.number()),
  money_recovered: z.number(),
  money_per_seed: z.array(z.number()),
});

const IncidentComparisonSchema = z.object({
  ariadne: EvalSideSchema,
  baseline: EvalSideSchema,
});

const FrontierPointSchema = z.object({
  threshold: z.number(),
  money_recovered: z.number(),
  money_per_seed: z.array(z.number()),
  false_intervention_cost: z.number(),
  false_interventions_total: z.number(),
  unsafe_action_rate: z.number(),
  executed_actions: z.number(),
  unaudited_actions: z.number(),
  do_nothing_correct_rate: z.number(),
  do_nothing_scored: z.number(),
  do_nothing_misses: z.number(),
});
export type FrontierPoint = z.infer<typeof FrontierPointSchema>;

export const EvaluationSchema = z.object({
  seeds: z.array(z.number()),
  thresholds: z.array(z.number()),
  discrimination: z.object({
    incident_A_shared_bank: IncidentComparisonSchema,
    incident_B_single_psp: IncidentComparisonSchema,
    incident_E_coincidental: IncidentComparisonSchema,
    A_ariadne_beats_baseline_rca: z.boolean(),
    A_ariadne_beats_baseline_money: z.boolean(),
    B_no_regression: z.boolean(),
    E_ariadne_not_over_attributes: z.boolean(),
  }),
  frontier: z.object({
    ariadne: z.array(FrontierPointSchema),
    baseline: z.array(FrontierPointSchema),
  }),
});
export type Evaluation = z.infer<typeof EvaluationSchema>;

// ---- incidents catalog -------------------------------------------------------
export const IncidentsSchema = z.object({
  incident_types: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      target: z.string().nullable(),
      is_thesis: z.boolean(),
      expected_correct_behavior: z.string(),
    })
  ),
});
export type Incidents = z.infer<typeof IncidentsSchema>;

// ---- audit -------------------------------------------------------------------
export const AuditSchema = z.object({
  source: z.string(),
  scenario: z.object({
    incident_type: z.string(),
    seed: z.number(),
    intervention_threshold: z.number(),
    system: z.string(),
  }),
  entries: z.array(
    z.object({
      window: z.number(),
      decision_id: z.string(),
      action_kind: z.string(),
      params: z.record(z.string(), z.any()),
      confidence: z.number(),
      evidence_path: z.array(z.string()),
      audited: z.boolean(),
    })
  ),
});
export type Audit = z.infer<typeof AuditSchema>;
