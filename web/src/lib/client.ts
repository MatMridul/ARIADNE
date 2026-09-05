/**
 * The SINGLE API client. No component calls fetch directly — everything goes
 * through here. Each function fetches `/api/...`, validates the JSON against the
 * Zod schema, and returns a typed object (throwing on contract drift).
 */
import {
  AuditSchema,
  EvaluationSchema,
  IncidentsSchema,
  SimulateResponseSchema,
  TopologySchema,
  type Audit,
  type Evaluation,
  type Incidents,
  type SimulateRequest,
  type SimulateResponse,
  type Topology,
} from "./schemas";

const BASE = "/api";

async function getJSON(path: string): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as any).detail || (body as any).error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function postJSON(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    throw new Error((b as any).detail || (b as any).error || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchTopology(): Promise<Topology> {
  return TopologySchema.parse(await getJSON("/topology"));
}

export async function fetchSimulate(req: SimulateRequest): Promise<SimulateResponse> {
  return SimulateResponseSchema.parse(await postJSON("/simulate", req));
}

export async function fetchEvaluation(
  seeds?: number[],
  thresholds?: number[]
): Promise<Evaluation> {
  const params = new URLSearchParams();
  if (seeds) params.set("seeds", seeds.join(","));
  if (thresholds) params.set("thresholds", thresholds.join(","));
  const q = params.toString();
  return EvaluationSchema.parse(await getJSON(`/evaluation${q ? `?${q}` : ""}`));
}

export async function fetchIncidents(): Promise<Incidents> {
  return IncidentsSchema.parse(await getJSON("/incidents"));
}

export async function fetchAudit(req: SimulateRequest): Promise<Audit> {
  const params = new URLSearchParams({
    incident_type: req.incident_type,
    seed: String(req.seed),
    intervention_threshold: String(req.intervention_threshold),
    system: req.system,
  });
  return AuditSchema.parse(await getJSON(`/audit?${params.toString()}`));
}
