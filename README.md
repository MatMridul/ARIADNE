# ARIADNE

**Merchant Revenue Recovery Intelligence** — an [ATLAS-class](https://github.com/MatMridul/ATLAS) system for the merchant payment ecosystem.

> **Status: pre-spec.** Governance (decision records) is in place; the build spec,
> domain adapter, and implementation are not written yet. No application code committed.

---

## What ARIADNE is

ARIADNE models a merchant's payment ecosystem as a living dependency graph and,
when revenue is at risk, **traces the failure back through that graph to its root
cause and out to a bounded recovery action** — with per-edge evidence, confidence,
and an audit trail. The name is Ariadne's thread: a guide out of the payment labyrinth.

The core loop:

```
detect revenue-at-risk → trace the dependency graph → diagnose root cause →
select a bounded recovery intervention → measure money recovered
```

It is built for the **Razorpay AI Buildathon — Track 03 (AI Revenue Recovery)** and
evaluated on a synthetic payment-ecosystem simulator with injected, ground-truth
incidents (so detection, diagnosis, recovery, and *false-intervention cost* can all
be measured honestly).

## Relationship to ATLAS

ATLAS is the reusable *class* (the world-model architecture). ARIADNE is a concrete
*instantiation* of that class for one domain. The class blueprint and the
instantiation contract live in the ATLAS repo; ARIADNE follows its
`docs/INSTANTIATION_GUIDE.md`.

## Governance

Design decisions are recorded under [`docs/decisions/`](docs/decisions/) using the
ATLAS decision-record system (two-pass Proposed→closed, immutable history). This is
a required part of an ATLAS-class build.

## Status & license

Pre-spec. License deferred.
