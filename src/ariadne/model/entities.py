"""Domain entities for the merchant payment ecosystem (adapter.md §1).

These are plain data containers. They hold NO reasoning and NO derived health;
node health is derived elsewhere (diagnosis/) from observed transactions.
"""
from __future__ import annotations

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
    """A payment company / gateway. Stable id, static attributes only."""

    psp_id: str
    name: str


@dataclass(frozen=True)
class Bank:
    """An acquiring/issuing bank. The hidden shared node; health is inferred."""

    bank_id: str
    name: str
    role: str  # "issuer" | "acquirer"


@dataclass
class Transaction:
    """The atomic observation. Records the actual path (method -> psp -> bank)
    it traversed, which is what makes bank health computable from aggregation."""

    txn_id: str
    timestamp: float
    method: Method
    psp_id: str
    bank_id: str
    amount: float
    success: bool
    failure_code: str | None  # None on success
    latency_ms: float
    cohort: str
    geography: str
