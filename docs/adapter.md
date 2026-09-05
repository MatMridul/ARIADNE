# ATLAS Domain Adapter — ARIA (Merchant Revenue Recovery Intelligence)

> This is the filled instantiation of `adapters/TEMPLATE.md` from the ATLAS class
> repo, for the **merchant payment ecosystem** domain. It is the spine of the
> build. The microscopic build spec (`docs/BUILD_SPEC.md`) implements what this
> adapter defines. Where a section makes a real design choice, it is (or will be)
> recorded as a Decision Record in `docs/decisions/`.

- **Domain:** One online merchant's payment ecosystem — the chain each payment
  travels (method → payment company → bank), modeled as a dependency graph.
- **Primary user & problem:** A merchant (or their payments/ops team) losing
  revenue to payment failures they cannot see the *cause* of. A drop in success
  rate is visible; *which shared piece of plumbing is actually failing* is not.
- **Does this app act, or only explain/predict?** **Acts** — but only inside the
  simulator. ARIA selects a bounded recovery action; the simulator produces the
  post-intervention transactions so realized money-recovered is measurable. No real
  payment system is ever touched.

---

## 0. The thesis this adapter exists to test

> **Does explicitly modeling the interconnected payment ecosystem let an AI system
> diagnose and recover revenue more effectively than treating every payment
> component independently?**

The **shared-bank scenario** is the falsifiable test of that thesis. ARIA is
compared against a *fair* non-relational baseline (see §7) that sees the same
observations but does not know the dependency graph. If the graph does not
measurably beat the baseline on the shared-dependency case, the thesis fails —
and we report that honestly.

**Both outcomes are valid engineering results:**

- **If ARIA wins** on the shared-bank case → the map mattered; modeling the
  relationships enabled a diagnosis and recovery the baseline could not reach.
- **If ARIA does not win** → we learned the map did not add enough information
  to justify its complexity. That is genuine, publishable engineering knowledge,
  not a failure to hide.

The evaluation is therefore written *before* we know which outcome occurs, and is
never tuned to force a win. This is the disciplining principle for the whole
build:

> **Do not build the graph because graphs are cool. Build it because we can
> demonstrate the specific decisions that become possible *only because the
> relationships exist*.** Every graph feature must earn a decision. A feature that
> enables no decision the baseline couldn't already make is cut.

---

## 1. Entity types

| Entity | Stable id | Key attributes | State / lifecycle | Provenance needs |
|--------|-----------|----------------|-------------------|------------------|
| Merchant | `merchant_id` | name, business category | active | low — it's the root, single merchant in v1 |
| PaymentMethod | `method_id` (e.g. `upi`, `card`, `netbanking`) | display name, enabled/disabled | enabled → disabled (a recovery action can flip this) | required — action can change state |
| PaymentCompany (PSP/Gateway) | `psp_id` | name, routing weight per method | healthy → degraded → down (as observed, not injected) | required — health is *derived* from observations, must be evidenced |
| Bank (acquiring / issuer) | `bank_id` | name, role (issuer/acquirer) | healthy → degraded → down (derived) | required — the hidden shared node; its health is inferred, never observed directly |
| Transaction | `txn_id` | amount, method, psp, bank, status (success/fail), failure_code, latency_ms, timestamp, customer_cohort, geography | terminal (success \| fail) | required — the atomic observation; carries the full path it took |

> A `Transaction` records the **actual path** it traversed (method → psp → bank).
> That per-transaction path is what makes the graph computable rather than
> decorative: the bank's health is never observed directly, only *inferred* by
> aggregating the transactions that passed through it.

## 2. Relationship types (typed, directional)

| Relationship | Source → Target | Meaning | Directionality | Temporal behavior | Confidence/provenance |
|--------------|-----------------|---------|----------------|-------------------|-----------------------|
| `offers_method` | Merchant → PaymentMethod | merchant accepts this method | directed | stable | n/a |
| `routed_through` | PaymentMethod → PaymentCompany | a method's traffic is sent to one or more PSPs (with a routing weight) | directed | **can change per window** (rerouting is a recovery action) | required |
| `settles_via` | PaymentCompany → Bank | a PSP hands the transaction to a bank/issuer to approve | directed | stable within a run | required |
| `shares_bank_with` | PaymentCompany ↔ PaymentCompany | two PSPs settle via the **same** bank (derived, not stored input) | undirected (derived) | derived per graph | derived — this is the edge the baseline cannot see |

> `settles_via` is the load-bearing relationship. Because several PSPs can
> `settles_via` the **same** Bank, a single bank fault appears as correlated
> failures across *multiple* PSPs. Only a system that holds this edge can say
> "the bank is down" instead of "three PSPs independently degraded."

## 3. Event / observation types

| Event | Timestamp | Source | Affected entities | State change | Evidence |
|-------|-----------|--------|-------------------|--------------|----------|
| TransactionOutcome | yes | simulator | Transaction (+ its method/psp/bank by path) | none directly — it's the raw signal | the transaction record itself (status, failure_code, latency) |
| WindowSnapshot (derived) | window end | ARIA aggregator | PaymentMethod, PaymentCompany, Bank | updates derived health/success-rate per node | the set of TransactionOutcomes in the window |
| RecoveryActionApplied | yes | ARIA | PaymentMethod / `routed_through` edge | flips method enabled/disabled, or reweights routing | the decision + its evidence path |
| OutcomeObserved (post-action) | yes | simulator | Transaction | new transactions under the changed config | post-intervention transaction set |

> ARIA ingests only `TransactionOutcome`s. Everything about node health is
> **derived** — this keeps observed vs. inferred cleanly separated (DESIGN_PRINCIPLES §4).

## 4. Query intents

| Question the system must answer | Query class |
|---------------------------------|-------------|
| "What is each node's success rate right now?" | state |
| "Did success rate drop vs. its historical baseline, and where?" | historical |
| "Which PSPs / methods sit downstream of bank X?" | trace |
| "Which single upstream node best explains the observed spread of failures?" | **attribution** (the core query) |
| "If bank X is the cause, which methods/PSPs are affected?" | impact |
| "If we reroute method M away from PSP P, what recovery do we expect?" | counterfactual |
| "Given current confidence, should we act — and which action?" | decision |

## 5. Reasoning strategies

| Query intent | Method | Why this method |
|--------------|--------|-----------------|
| state / historical | deterministic aggregation + threshold vs. rolling baseline | simple, transparent, no ML needed — detects *that* something dropped |
| trace / impact | graph traversal over `routed_through` / `settles_via` | this is the relationship reasoning; walking the graph is the whole point |
| **attribution** | **shared-cause scoring over the graph**: for each candidate upstream node, measure how well "this node is unhealthy" explains the *pattern* of observed failures across all its downstream paths, vs. explaining them as independent per-node faults | deterministic and explainable; distinguishes "one shared bank" from "several independent PSPs" — the exact discrimination the baseline cannot make |
| counterfactual | replay expected traffic under the proposed routing/method change against observed healthy-path success rates | gives an expected-recovery estimate to compare actions |
| decision | pick the action with best expected recovery whose attribution confidence clears the **intervention threshold**; else `do_nothing` | ties the risk-appetite dial (§6) directly to whether we act |

> **No LLM, no graph DB, no ML framework in v1.** Attribution is a deterministic
> scoring function over the graph. If a later DR proves a probabilistic method
> earns its place, it is added then — not preemptively (DESIGN_PRINCIPLES §10).
> Every reasoning result carries `claim_type` (observed/derived/hypothesis/
> prediction/decision), an evidence path, and a confidence — per
> `schemas/atlas-concepts.yaml` `reasoning_results`.

## 6. Action policies

ARIA acts inside the simulator. The **intervention threshold** is not a fixed
number — it is an explicit **risk-appetite dial** swept by the evaluation (§7).

| Action | Required confidence | Authorization | Max scope/impact | Stopping rule | Rollback | Audit fields |
|--------|--------------------|--------------|-------------------|---------------|----------|--------------|
| `reroute_traffic(method, from_psp, to_psp)` | ≥ threshold | auto (simulated) | one method's routing weights; cannot send to a PSP the graph shows is also degraded | if target PSP is not healthier, abort | restore prior routing weights | decision_id, evidence_path, from/to, expected_recovery, confidence |
| `disable_method_temporarily(method)` | ≥ threshold (higher tier) | auto (simulated) | one method; never disable the *last* working method | if it would disable all methods, abort | re-enable method | decision_id, evidence_path, method, confidence |
| `retry_with_fallback(policy)` | ≥ threshold | auto (simulated) | bounded retry count; only for retriable failure codes | max N retries | n/a (additive) | decision_id, policy, retries, confidence |
| `do_nothing` | — (default when below threshold) | n/a | none | this *is* the stopping rule | n/a | decision_id, reason="confidence below threshold", confidence |

> `do_nothing` is a first-class action, not the absence of one. Choosing it
> correctly on the ambiguous/no-cause incident (§7 incident D) is scored as a win.
> The reasoning engine can never widen an action's scope beyond this table
> (ACTION_MODEL required controls).

## 7. Evaluation protocol

- **Ground truth source:** a **payment-ecosystem simulator** that generates
  transactions (amount, method, psp, bank, status, failure_code, latency, cohort,
  geography, volume) and **injects known causal incidents** so root cause is
  labeled. **Honest-adversary requirements:** the diagnoser (ARIA) never reads
  the simulator's injected ground-truth parameters; the simulator adds realistic
  noise, base-rate variation, and overlapping/ambiguous failures; and it includes
  incidents ARIA should *not* get a clean shot at (incident D). "Unknown >
  fabricated" — the simulator never hands the reasoner a coefficient.

- **The four injected incident types:**
  - **A — shared-bank degradation** (the hero / thesis test): one bank's approval
    rate drops; failures surface across *every* PSP that settles via it.
  - **B — single-PSP outage** (control): one PSP fails alone; tests that ARIA
    does **not** over-attribute to the bank.
  - **C — method-level fault**: e.g. UPI collect timeouts spike independently.
  - **D — ambiguous / no real cause**: a random noise dip with no injected
    incident; the correct answer is `do_nothing`.

- **The fair non-relational baseline (hard requirement):** an "independent
  monitoring" system that receives the **same observations** as ARIA —
  per-PSP metrics, per-method metrics, historical baselines, current failure
  rates, latency, transaction volume — and monitors each component
  independently. The **only** thing it lacks is the dependency graph. This makes
  the comparison a clean controlled experiment: same eyes, different reasoning
  (relational vs. independent). The baseline must be the *strongest reasonable
  non-relational alternative*, not a strawman.

- **Shared Dependency Discrimination Test (the thesis, made falsifiable):**
  ARIA must demonstrate **measurable improvement over the fair baseline on
  incident A specifically** — where multiple observable failures share a hidden
  upstream dependency. On incident B it must match the baseline (not regress). If
  ARIA does not beat the baseline on A, the relational thesis is not supported,
  and that is reported plainly. *(This principle is proposed for promotion into
  the ATLAS class eval principles — see DR-002 below.)*

- **Detection metrics:** precision / recall of "an incident is happening",
  detection latency, false-alarm rate.
- **Diagnosis / attribution metrics:** root-cause accuracy (did it name the right
  node?), path accuracy, calibration (does stated confidence match hit rate?).
- **Decision / outcome metrics:** money recovered across a **batch** of incidents
  (Track 03's bar), expected vs. realized recovery, regret vs. an oracle.
- **Safety metrics (reported as loudly as recovery):** false-intervention cost
  (money/lost trust from acting when it shouldn't have), unsafe-action rate,
  rollback success, audit completeness. **Incident D's do-nothing rate is a
  headline safety number.**
- **The risk-appetite frontier (headline result):** run the whole eval suite
  across a sweep of intervention thresholds (e.g. 0.55 / 0.70 / 0.85) and plot
  **recovery vs. false-intervention cost**. The product claim is not "we chose the
  optimal threshold" but "here is the frontier; the merchant chooses how
  aggressive ARIA should be."

## 8. Open questions / UNKNOWNs

> **Status note (updated after DR-001 + hostile review).** Questions 1–3 below were
> RESOLVED during the decision-record and hardening work; they are recorded here as
> closed with pointers, so this section stays honest rather than stale. Only 4 and 5
> remain open, and both are build-time *tuning* choices (pick sensible values,
> document them) — neither is an architecture decision that should stall the build.

1. **Attribution scoring function — exact form. RESOLVED (ARIA DR-001, Accepted;
   BUILD_SPEC §3.8).** Pinned to `confidence = coverage × specificity`, blame the
   bank when `coverage == 1.0` and `specificity ≥ S_MIN` (start 0.8), else
   independent PSPs / method / none. This is what separates incident A from the
   coincidental incident E.
2. **Baseline's own decision rule. RESOLVED (ARIA DR-001, decision C1).** The
   baseline also *acts*, using the same action menu driven by its per-node view, so
   money-recovered is an apples-to-apples head-to-head. It receives identical raw
   observations; it only lacks the graph.
3. **How many PSPs / banks / methods in v1. RESOLVED (ARIA DR-001, decision
   A1).** 3 methods, 3 PSPs, 2 banks — bank_A shared by PSP-1 & PSP-2, bank_B on
   PSP-3. Residual-risk note (in DR-001): if this proves too small to make the win
   non-trivial once measured, revisit via a new superseding DR.
4. **Batch size & incident mix for the headline "money recovered across a batch"
   number. OPEN — build-time tuning.** Pick a reproducible batch that exercises all
   five incident types (A/B/C/D/E) plus clean windows; document the chosen counts.
   Not architecture — no DR needed unless the choice changes what is being proven.
5. **Simulator noise model specifics** (base success rates per method, noise
   distribution, severity/onset ranges). **OPEN — build-time tuning.** Choose
   realistic values with severities overlapping the noise band (per BUILD_SPEC
   §3.5), and document them so runs reproduce. Not architecture — no DR needed.
