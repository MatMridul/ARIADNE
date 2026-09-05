# ATLAS Decision Records

This directory is the **durable record** of every significant decision made
while building ATLAS. Chat conversations are not the record — these files are.
If a decision isn't captured here with its reasoning and its challenge, it
effectively didn't happen.

## Why this exists

ATLAS is built by a human prompting directly, deliberately. A prompt is a
**hypothesis**, not a specification — a misunderstanding in a prompt must not
silently become the system. Decisions are therefore forced through an explicit
loop and written down, so that neither the human, the implementing model
(Kiro), nor a future reviewer has to trust anyone's memory or authority.

## The build loop

```
YOUR UNDERSTANDING
       ↓
     PROMPT              (a hypothesis, not an order)
       ↓
     KIRO
       ↓
 experiment / implementation
       ↓
   RAW RESULTS
       ↓
 PROPOSED CONCLUSION      (Kiro's recommendation + its own strongest counter-argument)
       ↓
   CHATGPT CHALLENGE      (independent, adversarial review)
       ↓
     DECISION
       ↓
   DOCUMENTATION          (this directory)
```

Two guards on the loop:

1. **No design decision may live only where it cannot be verified against
   ATLAS's real data.** (Design must be grounded in things we can execute.)
2. **No design decision may live only in the model that ran the experiment.**
   (The model that produced the evidence is compromised as the sole judge of
   what it means — hence the external challenge.)

## How a Decision Record is written (two passes)

A DR is filled in **two stages**, because the challenge sections cannot exist
until an independent review has actually happened.

- **Pass 1 — `Proposed`:** Kiro fills Question, Context, Evidence, Options,
  Proposed Decision, and Strongest Argument Against. The DR is committed with
  status `Proposed` and the External Challenge / Resolution / Decision /
  Consequences sections marked _pending_. This makes "awaiting external
  challenge" a visible, honest state in the repo.
- **Pass 2 — closed out:** After the human takes the `Proposed` DR to ChatGPT
  (or another independent reviewer), the External Challenge, Resolution,
  Decision, and Consequences sections are filled, and the status is updated to
  `Accepted`, `Rejected`, or `Deferred`. The note should say what the challenge
  actually changed (or why it didn't).

A decision is **never** ratified by a single model alone — neither Kiro's "the
data says X" nor ChatGPT's challenge is trusted without the other.

## Immutability rule (the record must show how belief evolved)

The point of a DR is to preserve **what we believed before the challenge**, not
just the final answer. Therefore:

- **Pass-1 sections are frozen once committed.** Question, Context, Evidence,
  Options, Proposed Decision, and Strongest Argument Against are **append-only**
  after the `Proposed` commit — they are never edited or deleted to match a
  later outcome. (Fixing a typo is fine; rewriting the substance is not.)
- **A reversal is recorded, not overwritten.** If the challenge changes the
  outcome (e.g. proposed *PostgreSQL* → resolved *relational core + graph
  abstraction*), the original Proposed Decision stays exactly as written, and
  the new outcome — plus *what changed the mind and why* — goes in the
  **Resolution** and **Decision** sections. A reader must be able to see, in one
  file, "we believed X → here was our own doubt → here's what the challenge
  argued → we changed to Y because …".
- **Status is never silently flipped.** Every status change is appended to a
  **Status history** line in the header (e.g. `Proposed 2026-08-29 → Accepted
  2026-08-31`), so the transition itself is on the record.

Git history is a backstop, not the mechanism: the evolution must be **readable
in the file itself**, not something a reader has to reconstruct with `git diff`.

## Reversal vs. supersession (which mechanism when)

The organizing principle: **everything inside a decision's own challenge cycle
stays in one DR; anything that disturbs an already-`Accepted` decision from
outside that cycle spawns a new DR.**

- **Reversal during a decision's own challenge cycle → same DR.** The proposal
  and its challenge-driven change are the *same decision evolving*. Keep them in
  one file (frozen proposal + Resolution telling the change story). This is the
  common case.
- **Overturning an already-`Accepted` decision later (new evidence, months on)
  → a new DR that supersedes the old one.** The settled decision and its later
  undoing are two distinct decisions in time; link them via the
  `Supersedes / Superseded by` header and set the old DR's status to
  `Superseded`.

| Situation                                                  | What happens                          |
| ---------------------------------------------------------- | ------------------------------------- |
| Kiro proposes X → external challenge **rejects** X         | **Same DR** (status → Rejected)       |
| Kiro proposes X → external challenge **modifies** X        | **Same DR** (change → Resolution)     |
| Kiro proposes X → external challenge **confirms** X        | **Same DR** (status → Accepted)       |
| Accepted X → new evidence later **invalidates** X          | **New DR supersedes old DR**          |
| Accepted X → requirements/context **materially change**    | **New DR**                            |
| Accepted X → implementation reveals an **assumption was wrong** | **New DR** if the assumption was load-bearing; **same DR** (note in Consequences) if it's a mere implementation correction |
| Proposed X → more investigation needed **before** review   | **Same DR remains `Proposed`**        |

**The implementation-assumption test:** did the finding break the decision's
*foundation* (the reasoning/evidence it rested on) or just a *detail*? Foundation
broken → new DR supersedes. Detail wrong but the decision still holds for the
same reasons → same DR, noted in Consequences.

## Status lifecycle

| Status     | Meaning                                                        |
|------------|----------------------------------------------------------------|
| `Proposed` | Kiro's pass done; awaiting independent challenge.              |
| `Accepted` | Survived challenge; this is the decision.                      |
| `Rejected` | Challenge (or new evidence) defeated the proposal.            |
| `Deferred` | Not decidable yet; blocked on something noted in the record.  |
| `Superseded` | Replaced by a later DR (link it).                           |

## Naming and numbering

- Files: `DR-XXX-short-slug.md`, zero-padded 3-digit number, incrementing.
- `DR-000-template.md` is the canonical template — copy it for each new DR.
- Once a DR number is used it is never reused.
- A challenge-driven reversal stays in the *same* DR (see Reversal vs.
  supersession above). Only the later overturning of an already-`Accepted`
  decision creates a new DR that supersedes the old one (marking the old one
  `Superseded`).

## Index

| DR   | Title | Status |
|------|-------|--------|
| 000  | Template (not a decision) | — |
| 001  | ARIADNE core design: graph size, attribution scoring, acting baseline | Accepted |
| 002  | Attribution branch disambiguation (shared-dep / independent-PSP / method) | Accepted |

_Update this table whenever a DR is added or its status changes._
