/**
 * Client-side health derivation for the living payment topology.
 *
 * WHY THIS FILE EXISTS — the load-bearing "bank health is derived" rule:
 * The API (`GET /api/topology`) has NO health on nodes, and `POST /api/simulate`
 * returns per-window `NodeStats` ONLY for `psp` and `method` kinds. There is NO
 * bank NodeStats row (see web/CONTRACT.md and observe/aggregate.py). A bank is a
 * hidden upstream node — its state is INFERRED from the PSPs that settle through
 * it, exactly as the backend `attribute()` does server-side:
 *   - a bank is `down`     if ALL of its PSPs have breached (coverage == 1.0),
 *   - a bank is `degraded` if SOME (but not all) of its PSPs have breached,
 *   - a bank is `healthy`  otherwise.
 * "Breached" mirrors the backend's negative-delta threshold on success rate.
 * This is the whole ARIA thesis made visible: when Bank-A breaks, psp_1 AND
 * psp_2 both breach and converge onto one hidden node — a graph-blind monitor
 * only sees "two PSPs down", ARIA sees "one bank down".
 */
import type { Health } from "@/design/ui";
import type { NodeStat, SimWindow, Topology } from "@/lib";

/**
 * Success-rate drop (negative delta) below which a PSP/method is considered
 * "breached". A small negative band avoids treating pure sampling noise as a
 * fault, mirroring the backend detector's tolerance.
 */
export const BREACH_DELTA = -0.05;

/** True if a node's success-rate delta represents a real breach (not noise). */
export function isBreached(stat: NodeStat | undefined): boolean {
  return stat != null && stat.delta <= BREACH_DELTA;
}

/** Map a signed delta to a health band for a directly-observed node. */
export function healthFromDelta(stat: NodeStat | undefined): Health {
  if (stat == null) return "idle";
  if (stat.delta <= BREACH_DELTA * 2) return "down"; // deep drop
  if (stat.delta <= BREACH_DELTA) return "degraded"; // shallow breach
  return "healthy";
}

/** Index a window's node stats by node_id for O(1) lookup. */
export function statsById(win: SimWindow | undefined): Record<string, NodeStat> {
  const out: Record<string, NodeStat> = {};
  if (!win) return out;
  for (const s of win.nodes) out[s.node_id] = s;
  return out;
}

/**
 * Derive a bank's health from ITS OWN PSPs' deltas — never from a NodeStats row
 * (there is none). Coverage = fraction of the bank's PSPs that have breached.
 */
export function bankHealth(
  bankPspIds: string[],
  stats: Record<string, NodeStat>
): { health: Health; breachedPsps: string[]; coverage: number } {
  if (bankPspIds.length === 0) {
    return { health: "idle", breachedPsps: [], coverage: 0 };
  }
  const breachedPsps = bankPspIds.filter((id) => isBreached(stats[id]));
  const coverage = breachedPsps.length / bankPspIds.length;
  let health: Health;
  if (coverage >= 1) health = "down";
  else if (coverage > 0) health = "degraded";
  else health = "healthy";
  return { health, breachedPsps, coverage };
}

/**
 * A method's health is directly observed (method NodeStats exist), falling back
 * to the worst of the PSPs it routes to when a method stat is missing.
 */
export function methodHealth(
  methodId: string,
  routedPspIds: string[],
  stats: Record<string, NodeStat>
): Health {
  const direct = stats[methodId];
  if (direct) return healthFromDelta(direct);
  const psHealths = routedPspIds.map((id) => healthFromDelta(stats[id]));
  if (psHealths.includes("down")) return "down";
  if (psHealths.includes("degraded")) return "degraded";
  return psHealths.length ? "healthy" : "idle";
}

/** PSP ids routed to by a given method, per the topology routing table. */
export function pspsForMethod(topology: Topology, methodId: string): string[] {
  return topology.routing
    .filter((r) => r.method === methodId && r.weight > 0)
    .map((r) => r.psp_id);
}
