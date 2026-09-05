"""ARIA Web API — a THIN serialization boundary over the Python core.

Every handler calls existing functions in `ariadne.*` and reshapes their output to
the JSON in web/CONTRACT.md. NO domain logic lives here (vision §16). The core is
seed-deterministic, so identical requests return identical responses.

Run (dev):  uvicorn web.api.main:app --reload --host 127.0.0.1 --port 8000
Run (prod): build web/dist then `uvicorn web.api.main:app --host 127.0.0.1 --port 8000`
"""
from __future__ import annotations

import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ariadne.decide.actions import Action
from ariadne.decide.policy import select_action
from ariadne.diagnosis.attribute import attribute
from ariadne.diagnosis.detect import detect
from ariadne.eval.run import DETECT_THRESHOLD, run_once_trace
from ariadne.eval.sweep_cache import get_sweep
from ariadne.model.entities import Method
from ariadne.model.graph import default_graph
from ariadne.simulator.config import SimConfig
from ariadne.simulator.incidents import IncidentType, make_incident

app = FastAPI(title="ARIA API", version="1.0.0")

# CORS only matters in dev (Vite on :5173 -> API on :8000). In prod the SPA is
# served same-origin by this app, so this is harmless either way.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- canonical targets per incident type (match discrimination_result) --------
_CANONICAL_TARGET = {
    IncidentType.SHARED_BANK: ("bank_A", None),
    IncidentType.SINGLE_PSP: ("psp_1", None),
    IncidentType.METHOD: ("card", None),
    IncidentType.NONE: (None, None),
    IncidentType.COINCIDENTAL: ("psp_1", "psp_3"),
}

_METHOD_LABEL = {"upi": "UPI", "card": "Card", "netbanking": "Netbanking"}
_INCIDENT_META = {
    "A_shared_bank": ("Shared bank outage", True, "attribute to shared bank"),
    "B_single_psp": ("Single PSP outage", False, "blame one PSP, not the bank"),
    "C_method": ("Payment method fault", False, "blame the method"),
    "D_ambiguous": ("Ambiguous noise dip", False, "do nothing"),
    "E_coincidental": (
        "Coincidental dual outage",
        False,
        "blame two PSPs independently, no bank",
    ),
}


# ---- GET /api/topology --------------------------------------------------------
@app.get("/api/topology")
def get_topology() -> dict:
    g = default_graph()
    shared = g.shared_banks()
    banks = []
    for bank_id, bank in g.banks.items():
        psps = g.psps_for_bank(bank_id)
        banks.append(
            {
                "id": bank_id,
                "label": bank.name,
                "role": bank.role,
                "shared": bank_id in shared,
                "psps": psps,
            }
        )
    routing = []
    for method, rows in g.routing.items():
        for psp_id, weight in rows:
            if weight > 0.0:
                routing.append(
                    {"method": method.value, "psp_id": psp_id, "weight": weight}
                )
    return {
        "merchant": {"id": "merchant", "label": "Merchant"},
        "methods": [
            {"id": m.value, "label": _METHOD_LABEL.get(m.value, m.value)}
            for m in Method
        ],
        "psps": [
            {"id": p, "label": p.upper().replace("_", "-"), "bank_id": g.settles_via[p]}
            for p in g.psps
        ],
        "banks": banks,
        "routing": routing,
        "shared_banks": shared,
    }


# ---- POST /api/simulate -------------------------------------------------------
class SimulateRequest(BaseModel):
    incident_type: Literal[
        "A_shared_bank", "B_single_psp", "C_method", "D_ambiguous", "E_coincidental"
    ] = "A_shared_bank"
    seed: int = 7
    intervention_threshold: float = 0.70
    system: Literal["ariadne", "baseline"] = "ariadne"


def _representative_window(trace: dict) -> Optional[dict]:
    """Pick the window whose attribution best represents the incident: the
    triggered window with the highest attribution confidence; else the first
    triggered window; else None. Presentation-only selection."""
    triggered = [w for w in trace["windows"] if w["detection"]["triggered"]]
    if not triggered:
        return None
    return max(triggered, key=lambda w: w["attribution"]["confidence"])


@app.post("/api/simulate")
def post_simulate(req: SimulateRequest) -> dict:
    try:
        it = IncidentType(req.incident_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"bad incident_type {req.incident_type}")
    target, secondary = _CANONICAL_TARGET[it]
    cfg = SimConfig(seed=req.seed)
    incident = make_incident(
        it, req.seed, cfg.n_windows, target_id=target, secondary_target_id=secondary
    )

    # requested system trace (full per-window story)
    trace = run_once_trace(
        req.system, req.intervention_threshold, req.seed, incident=incident, cfg=cfg
    )
    # baseline (or ariadne) counterpart for the comparison block
    other = "baseline" if req.system == "ariadne" else "ariadne"
    other_trace = run_once_trace(
        other, req.intervention_threshold, req.seed, incident=incident, cfg=cfg
    )

    rep = _representative_window(trace)
    attribution = rep["attribution"] if rep else {
        "root_cause_id": "",
        "root_cause_kind": "none",
        "confidence": 0.0,
        "evidence_path": ["no window breached detection"],
        "claim_type": "hypothesis",
        "psp_causes": [],
    }
    # representative action: the window's action, else do_nothing
    action = rep["action"] if rep else {
        "kind": "do_nothing",
        "params": {"reason": "no detection"},
        "decision_id": "",
        "evidence_path": [],
        "confidence": 0.0,
        "expected_recovery": 0.0,
    }

    def _summary(t: dict) -> dict:
        r = _representative_window(t)
        a = r["attribution"] if r else {"root_cause_id": "", "root_cause_kind": "none", "confidence": 0.0}
        return {
            "root_cause_id": a["root_cause_id"],
            "root_cause_kind": a["root_cause_kind"],
            "confidence": a["confidence"],
            "money_recovered": t["money_recovered"],
        }

    return {
        "incident": {
            "incident_type": trace["incident"]["incident_type"],
            "target_id": trace["incident"]["target_id"],
            "secondary_target_id": trace["incident"]["secondary_target_id"],
            "start_window": trace["incident"]["start_window"],
            "end_window": trace["incident"]["end_window"],
            "n_windows": cfg.n_windows,
        },
        "windows": trace["windows"],
        "attribution": attribution,
        "action": action,
        "money_recovered": trace["money_recovered"],
        "comparison": {
            req.system: _summary(trace),
            other: _summary(other_trace),
        },
    }


# ---- GET /api/evaluation ------------------------------------------------------
@app.get("/api/evaluation")
def get_evaluation(seeds: Optional[str] = None, thresholds: Optional[str] = None) -> dict:
    seed_list = None
    if seeds:
        try:
            seed_list = [int(s) for s in seeds.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="seeds must be comma-separated ints")
    thr = (0.55, 0.70, 0.85)
    if thresholds:
        try:
            thr = tuple(float(t) for t in thresholds.split(",") if t.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="thresholds must be comma-separated floats")
    # The engine is fully deterministic, so the sweep output is memoizable. The
    # default (expensive) sweep is served from a precomputed on-disk cache of the
    # REAL run_sweep output; custom seed/threshold queries compute live. No
    # fabrication or hardcoding — the cache stores exactly what the engine produced.
    return get_sweep(seeds=seed_list, thresholds=thr)


# ---- GET /api/incidents (static catalog) --------------------------------------
@app.get("/api/incidents")
def get_incidents() -> dict:
    out = []
    for it in IncidentType:
        target, secondary = _CANONICAL_TARGET[it]
        label, is_thesis, behavior = _INCIDENT_META[it.value]
        target_str = target
        if secondary:
            target_str = f"{target} + {secondary}"
        out.append(
            {
                "id": it.value,
                "label": label,
                "target": target_str,
                "is_thesis": is_thesis,
                "expected_correct_behavior": behavior,
            }
        )
    return {"incident_types": out}


# ---- GET /api/audit (derived-from-run) ----------------------------------------
@app.get("/api/audit")
def get_audit(
    incident_type: str = "A_shared_bank",
    seed: int = 7,
    intervention_threshold: float = 0.70,
    system: str = "ariadne",
) -> dict:
    try:
        it = IncidentType(incident_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"bad incident_type {incident_type}")
    target, secondary = _CANONICAL_TARGET[it]
    cfg = SimConfig(seed=seed)
    incident = make_incident(it, seed, cfg.n_windows, target_id=target, secondary_target_id=secondary)
    trace = run_once_trace(system, intervention_threshold, seed, incident=incident, cfg=cfg)

    entries = []
    for w in trace["windows"]:
        a = w["action"]
        if a["kind"] == "do_nothing":
            continue
        audited = bool(a["decision_id"]) and len(a["evidence_path"]) > 0 and 0.0 <= a["confidence"] <= 1.0
        entries.append(
            {
                "window": w["window"],
                "decision_id": a["decision_id"],
                "action_kind": a["kind"],
                "params": a["params"],
                "confidence": a["confidence"],
                "evidence_path": a["evidence_path"],
                "audited": audited,
            }
        )
    return {
        "source": "derived-from-run",
        "scenario": {
            "incident_type": incident_type,
            "seed": seed,
            "intervention_threshold": intervention_threshold,
            "system": system,
        },
        "entries": entries,
    }


# ---- POST /api/topology/import ------------------------------------------------
class ImportRequest(BaseModel):
    manifest: dict


def _serialize_graph(g, merchant_id: str, merchant_name: str) -> dict:
    """Serialize a PaymentGraph to the SAME shape as GET /api/topology so the
    existing frontend visualization renders an imported topology unchanged."""
    shared = g.shared_banks()
    banks = []
    for bank_id, bank in g.banks.items():
        psps = g.psps_for_bank(bank_id)
        banks.append(
            {"id": bank_id, "label": bank.name, "role": bank.role,
             "shared": bank_id in shared, "psps": psps}
        )
    routing = []
    for method, rows in g.routing.items():
        for psp_id, weight in rows:
            if weight > 0.0:
                routing.append({"method": method.value, "psp_id": psp_id, "weight": weight})
    return {
        "merchant": {"id": merchant_id, "label": merchant_name},
        "methods": [
            {"id": m.value, "label": _METHOD_LABEL.get(m.value, m.value)}
            for m in Method if m in g.routing
        ],
        "psps": [
            {"id": p, "label": g.psps[p].name, "bank_id": g.settles_via.get(p, "")}
            for p in g.psps
        ],
        "banks": banks,
        "routing": routing,
        "shared_banks": shared,
    }


@app.post("/api/topology/import")
def post_topology_import(req: ImportRequest) -> dict:
    """Validate a topology manifest and normalize it into the existing PaymentGraph.
    In-memory / request-scoped only — NOT persisted. Returns the normalized topology
    (same shape as GET /api/topology), node/relationship counts, detected shared
    dependencies, and validation status."""
    from ariadne.model.manifest import TopologyValidationError, manifest_to_graph

    try:
        norm = manifest_to_graph(req.manifest)
    except TopologyValidationError as e:
        # 422: structurally invalid manifest; return every issue for the UI.
        raise HTTPException(status_code=422, detail={"valid": False, "errors": e.errors})

    topology = _serialize_graph(norm.graph, norm.merchant_id, norm.merchant_name)
    return {
        "valid": True,
        "topology": topology,
        "counts": {
            "methods": len(norm.method_ids),
            "psps": len(norm.psp_ids),
            "banks": len(norm.bank_ids),
            "routes": norm.route_count,
        },
        "shared_dependencies": norm.shared_banks,
        "note": "in-memory / request-scoped — not persisted",
    }


# ---- static SPA mount (prod only; dev uses the Vite server) -------------------
# Serve the built SPA with a proper SPA fallback: hashed assets under /assets are
# served directly; any other non-/api path returns index.html so client-side deep
# links and hard refreshes (/topology, /incidents, ...) work instead of 404ing.
# /api/* is handled by the routes above and 404s cleanly here if unmatched.
_DIST = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.isdir(_DIST):
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _ASSETS = os.path.join(_DIST, "assets")
    if os.path.isdir(_ASSETS):
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

    _INDEX = os.path.join(_DIST, "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # never swallow the API namespace
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="not found")
        # serve a real static file if one exists (favicon, etc.)
        candidate = os.path.join(_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        # otherwise hand back the SPA shell — the client router takes over
        return FileResponse(_INDEX)
