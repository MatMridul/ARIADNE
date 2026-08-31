# ARIADNE — The Thesis You Are Testing (steering)

Keep this in mind while building. ARIADNE is not a payment dashboard; it is an
experiment with a falsifiable claim.

## The claim

> Does explicitly modeling the interconnected payment ecosystem let an AI system
> diagnose and recover revenue more effectively than treating every payment
> component independently?

## The falsifiable test — Shared Dependency Discrimination

The **shared-bank scenario** is the concrete test:

- Two payment companies (PSPs) secretly settle through the **same bank**.
- When that bank degrades, failures appear across **both** PSPs at once.
- **ARIADNE** (knows the graph) should diagnose "the bank is down" — one cause.
- The **baseline** (same data, no graph) can only see "two PSPs dropped" — and
  will blame each PSP independently.

ARIADNE must show **measurable improvement over the baseline on this scenario**,
and must **not regress** on the single-PSP control scenario (where blaming the one
PSP is correct and inventing a shared cause would be wrong).

**The anti-cheat control — coincidental failures (incident E).** Two PSPs on
*different* banks can drop at the same time by pure chance. The correct answer then
is two *independent* faults, NOT a shared cause. A system that merely counts
correlated failures would wrongly cry "shared cause"; only real topology reasoning
gets both the shared-bank case (A) and the coincidental case (E) right. ARIADNE
must NOT over-attribute to a bank on E. The A-vs-E contrast is what proves the
graph reasons rather than counts.

## Both outcomes are wins for engineering knowledge

- **ARIADNE beats the baseline on the shared-bank case** → the map mattered.
- **ARIADNE does not beat it** → we learned the map didn't add enough information
  to justify its complexity. That is real, honest engineering knowledge.

So: never rig the experiment to make the graph win. Write the eval first, run it
straight, report what happens. The credibility of the whole submission rests on
this being an honest test, not a demo tuned to look brilliant.

## What this means for your code

Every time you add something to the graph or the attribution logic, ask: *"What
decision does this enable that the baseline cannot make?"* If you can name it
(e.g. "distinguish a shared-bank outage from independent PSP faults"), keep it. If
you can't, cut it.
