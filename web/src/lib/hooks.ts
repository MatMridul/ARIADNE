/** TanStack Query hooks — the typed data seam feature folders consume. */
import { useQuery } from "@tanstack/react-query";
import {
  fetchAudit,
  fetchEvaluation,
  fetchIncidents,
  fetchSimulate,
  fetchTopology,
} from "./client";
import type { SimulateRequest } from "./schemas";

export function useTopology() {
  return useQuery({ queryKey: ["topology"], queryFn: fetchTopology, staleTime: Infinity });
}

export function useSimulate(req: SimulateRequest, enabled = true) {
  return useQuery({
    queryKey: ["simulate", req],
    queryFn: () => fetchSimulate(req),
    enabled,
    staleTime: Infinity, // deterministic per (type,seed,threshold,system)
  });
}

export function useEvaluation(seeds?: number[], thresholds?: number[]) {
  return useQuery({
    queryKey: ["evaluation", seeds, thresholds],
    queryFn: () => fetchEvaluation(seeds, thresholds),
    staleTime: Infinity,
  });
}

export function useIncidents() {
  return useQuery({ queryKey: ["incidents"], queryFn: fetchIncidents, staleTime: Infinity });
}

export function useAudit(req: SimulateRequest, enabled = true) {
  return useQuery({
    queryKey: ["audit", req],
    queryFn: () => fetchAudit(req),
    enabled,
    staleTime: Infinity,
  });
}
