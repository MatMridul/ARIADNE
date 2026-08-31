"""Domain entities for ARIADNE (BUILD_SPEC §3.1).

Pure data, no reasoning. Enums are ``str``-backed so values serialize cleanly and
compare against plain strings. PSP and Bank are frozen (static topology nodes);
Transaction is mutable (it carries an observed outcome).
"""

from dataclasses import dataclass
from enum import Enum


class Method(str, Enum):
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"


class Health(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass(frozen=True)
class PSP:
    psp_id: str
    name: str


@dataclass(frozen=True)
class Bank:
    bank_id: str
    name: str
    role: str  # "issuer" | "acquirer"


@dataclass
class Transaction:
    txn_id: str
    timestamp: float
    method: Method
    psp_id: str
    bank_id: str
    amount: float
    success: bool
    failure_code: str | None  # None on success
    latency_ms: float
    cohort: str  # customer cohort label
    geography: str
