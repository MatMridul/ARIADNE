<!--
CANONICAL TEMPLATE — do not edit as a decision. Copy this file to
DR-XXX-short-slug.md and fill it in.

Two-pass rule:
  Pass 1 (Proposed): fill everything DOWN TO "Strongest Argument Against".
                     Leave the sections below it marked _pending_.
                     Commit with Status: Proposed.
  Pass 2 (closed):   after independent challenge, fill External Challenge,
                     Resolution, Decision, Consequences; set final Status.

Immutability rule:
  Pass-1 sections (Question .. Strongest Argument Against) are FROZEN once the
  Proposed commit lands — append-only, never rewritten to match the outcome.
  A reversal is captured in Resolution/Decision (name what changed FROM the
  original proposal and why), NOT by editing the Proposed Decision.
  Status is never silently flipped — append every transition to Status history.
-->

# DR-XXX — [Decision title]

- **Status:** Proposed | Accepted | Rejected | Deferred | Superseded
- **Status history:** Proposed YYYY-MM-DD  (append each transition, e.g. `→ Accepted YYYY-MM-DD`)
- **Date proposed:** YYYY-MM-DD
- **Date resolved:** YYYY-MM-DD (or _pending_)
- **Supersedes / Superseded by:** DR-YYY (or —)

## Question

What are we deciding? State it as a single, answerable question.

## Context

Why does this decision exist now? What prompted it, and what constraints
(scope, deadline, prior DRs) bound it?

## Evidence

What did we actually observe? Real results from experiments, data probes, or
code — not expectations. Link to what produced the evidence so it is
reproducible. If evidence is thin, say so.

## Options

What alternatives were genuinely considered? List each with its tradeoffs.
Include the "do nothing / defer" option where relevant.

## Proposed Decision

What does Kiro currently recommend, and why does the evidence point there?

## Strongest Argument Against

The most serious case against the proposed decision that Kiro can make itself.
This must be a real attack, not a strawman — its purpose is to arm the external
challenger, not to make the proposal look safe.

---
<!-- Everything below is Pass 2: filled only after independent challenge.
     Everything ABOVE this line is FROZEN once the Proposed commit lands. -->

## External Challenge

_pending — to be filled after independent (ChatGPT / reviewer) challenge._

What did the independent review identify? Push-back, missed options, wrong
assumptions, or agreement (and why).

## Resolution

_pending._

What actually changed after the challenge? If the outcome differs from the
Proposed Decision above, state the change explicitly — **from** what **to** what,
and why the challenge moved it. Do NOT edit the frozen Proposed Decision; the
change lives here. If nothing changed, say why the proposal survived.

## Decision

_pending._ — **Accepted / Rejected / Deferred.**

## Consequences

_pending._

What does this decision constrain or enable downstream? What later decisions
does it open, close, or depend on?
