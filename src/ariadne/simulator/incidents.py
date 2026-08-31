"""Injected causal incidents + ground truth (BUILD_SPEC §3.4, adapter §7).

Five incident types. GroundTruth is returned SEPARATELY by the engine and may be
read ONLY by the eval harness -- never by diagnosis/ or baseline/.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ariadne.model.entities import Method


class IncidentType(str, Enum):
    SHARED_BANK = "A_shared_bank"    # hero / thesis test: one bank, many PSPs
    SINGLE_PSP = "B_single_psp"      # control: no over-attribution to bank
    METHOD = "C_method"              # method-level fault
    NONE = "D_ambiguous"             # noise dip, NO real cause
    COINCIDENTAL = "E_coincidental"  # TWO PSPs on DIFFERENT banks drop by chance


@dataclass
class Incident:
    incident_type: IncidentType
    target_id: str | None  # bank_id / psp_id / method value / None for D
    secondary_target_id: str | None = None  # second independent PSP (E only)
    start_window: int = 0
    end_window: int = 0
    severity: float = 0.0  # success-rate drop on affected paths (A/B/C/E)
    # E draws two independent faults; the secondary carries its own window/severity
    secondary_start_window: int = 0
    secondary_end_window: int = 0
    secondary_severity: float = 0.0


@dataclass
class GroundTruth:
    """ONLY the eval harness may read this. diagnosis/ and baseline/ must not."""

    incident: Incident
    affected_psps: list[str]
    affected_methods: list[Method]
    # true root cause(s): one node for A/B/C; TWO independent PSPs for E; none for D
    true_causes: list[str]


# --- incident factory: onset/duration/severity randomised per seed -----------
# Bounded ranges (build-time tuning, adapter Q5). Severity range deliberately
# overlaps the noise band's low end for a fraction of cases so some incidents are
# genuinely ambiguous and the honest answer is low-confidence / do_nothing.
import hashlib as _hashlib
import struct as _struct

_SEV_MIN = 0.02   # overlaps noise band (noise_std ~0.01) -> ambiguous low end
_SEV_MAX = 0.35   # a clear, severe drop at the high end
_MIN_DURATION = 2
_MAX_DURATION = 5


def _draw(seed: int, *parts: object) -> float:
    key = ("|".join([str(seed)] + [str(p) for p in parts])).encode("utf-8")
    (n,) = _struct.unpack("<Q", _hashlib.blake2b(key, digest_size=8).digest())
    return n / 2**64


def _window_span(seed: int, n_windows: int, tag: str) -> tuple[int, int]:
    duration = _MIN_DURATION + int(
        _draw(seed, tag, "dur") * (_MAX_DURATION - _MIN_DURATION + 1)
    )
    duration = min(duration, n_windows)
    latest_start = max(0, n_windows - duration)
    start = int(_draw(seed, tag, "start") * (latest_start + 1))
    return start, start + duration - 1


def _severity(seed: int, tag: str) -> float:
    return _SEV_MIN + _draw(seed, tag, "sev") * (_SEV_MAX - _SEV_MIN)


def make_incident(
    incident_type: IncidentType,
    seed: int,
    n_windows: int,
    *,
    target_id: str | None = None,
    secondary_target_id: str | None = None,
) -> Incident:
    """Build an incident with onset/duration/severity randomised deterministically
    from (seed, incident_type). No fixed schedule -> no learnable tell."""
    if incident_type == IncidentType.NONE:
        return Incident(incident_type=IncidentType.NONE, target_id=None)

    start, end = _window_span(seed, n_windows, incident_type.value + str(target_id))
    severity = _severity(seed, incident_type.value + str(target_id))
    inc = Incident(
        incident_type=incident_type,
        target_id=target_id,
        start_window=start,
        end_window=end,
        severity=severity,
    )
    if incident_type == IncidentType.COINCIDENTAL:
        # second fault drawn INDEPENDENTLY (own onset/severity) so the two are not
        # secretly synchronised in a way a correlation counter could exploit.
        s2, e2 = _window_span(seed, n_windows, "E2" + str(secondary_target_id))
        inc.secondary_target_id = secondary_target_id
        inc.secondary_start_window = s2
        inc.secondary_end_window = e2
        inc.secondary_severity = _severity(seed, "E2" + str(secondary_target_id))
    return inc
