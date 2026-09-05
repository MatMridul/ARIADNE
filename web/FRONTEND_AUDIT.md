# ARIADNE Frontend — Brutal Design Audit

> Compiled 2026-09-05 by reading every file under `web/src/**`. Judged against
> `ARIADNE_Product_and_Frontend_Vision.md`. Severity: **P0** = a judge sees it in
> the first 10 seconds / breaks the "serious product" illusion; **P1** = clearly
> cheapens it; **P2** = polish. Honest framing: the data wiring and component logic
> are genuinely good (real API, verbatim evidence, honest negative/do-nothing
> handling). The problem is **visual execution + one broken integration**, not
> architecture. Every item below has a concrete fix ready.

---

## P0 — fix before anyone sees it

### P0-1. The Command Center renders the payment graph as a dashed "graph slot" placeholder
- **Where:** `web/src/incident/CommandCenter.tsx` → `TopologySlot()` (the `data-slot="topology-graph"` dashed box, "graph slot — topology feature").
- **Why it's damning:** the landing page's centerpiece — the vision's §4 "visual signature" — is literally a dashed empty box saying "graph renders here." The topology agent built a real `<PaymentGraph>` in `web/src/topology/`, but nobody wired it in. This single thing screams "unfinished / vibe-coded."
- **Fix:** delete `TopologySlot`. Import the real graph. Because the shell's dependency rule says feature folders don't import each other, the clean move is: extract the graph-into-a-box as a small embeddable component the shell composes, OR relax the rule for this one composition and import `@/topology`'s `PaymentGraph` + `buildGraph` directly in a Command-Center-owned wrapper that runs its own `useSimulate` + `useTopology`. Give it a fixed height (e.g. `h-[360px]`), `fitView`. Ship the hero scenario (A_shared_bank, seed 7) live on the landing page.

### P0-2. Emoji as iconography
- **Where:** `web/src/topology/nodes.tsx` → `MerchantNode` renders `🏬`. (Grep the tree for any other emoji before shipping.)
- **Why:** a raw emoji in a "financial control room / premium SaaS" node is the single loudest AI-slop tell. The vision explicitly targets Linear/Stripe polish.
- **Fix:** add `lucide-react` (one dep) and use line icons — `Store`/`Building2` (merchant), `Landmark` (bank), `CreditCard`/`Smartphone`/`Banknote` (methods), `Server`/`Network` (PSP). Consistent 16px stroke icons, `text-text-muted`. No emoji anywhere in the product surface.

### P0-3. No cohesive first-impression layout — "generic cards everywhere"
- **Where:** `CommandCenter.tsx` is `Card` → 2-col grid of `Card` → 2-col grid of `Card`. `EvaluationView.tsx` is a vertical stack of full-width `Card`s. The vision explicitly lists "generic cards everywhere" as a thing to avoid.
- **Why:** uniform card-on-card with equal visual weight = template, not control room. No hierarchy, no density, no focal point.
- **Fix:** give the Command Center a real control-room grid: a slim KPI strip (denser, smaller labels, tabular numerals, sparkline per KPI), a **dominant** graph panel (2/3 width, taller), and a right rail of stacked compact intelligence cards (diagnosis, action, activity). Vary card weight — the graph and the active diagnosis are primary; activity is tertiary. Use section dividers/labels, not 6 identical rounded boxes.

---

## P1 — clearly cheapens it

### P1-1. `Metric` typography is not "control room"
- **Where:** `web/src/design/ui.tsx` → `Metric` (2xl value, generic). The `.tabular` class maps numbers to **JetBrains Mono** — mono for large KPI figures reads "terminal," not "financial SaaS."
- **Fix:** use Inter tabular-nums (not mono) for large KPI values; reserve mono for IDs/code/evidence. Tighten label tracking, add a small delta/trend chip, right-align numbers. Consider a subtle top-accent or unit affix (`₹` smaller than the figure).

### P1-2. Two different `ScenarioControls` and two different `States` — duplicated, drifting
- **Where:** `web/src/topology/ScenarioControls.tsx` AND `web/src/incident/ScenarioControls.tsx` (different `ScenarioState` shapes); `web/src/incident/States.tsx` AND `web/src/evaluation/States.tsx` (near-duplicate spinners/error cards). Parallel agents each built their own.
- **Why:** guarantees visual drift (two spinner styles, two control layouts) and is exactly the incoherence a judge feels even if they can't name it.
- **Fix:** promote ONE `ScenarioControls` and ONE set of loading/error/empty states into `web/src/design/`. Delete the duplicates. Single source → consistent everywhere. (This also fixes the topology page and incident page looking like two different apps.)

### P1-3. Loading states are generic spinners
- **Where:** `incident/States.tsx` (`animate-spin` ring), `topology/TopologyPage.tsx` (`animate-ping` dot), `evaluation` loading.
- **Why:** spinners are the default-template look; the vision calls for "strong loading/skeleton states."
- **Fix:** skeletons that mirror the final layout (ghost KPI strip, ghost graph frame, ghost table rows) with a subtle shimmer. Communicates structure while loading.

### P1-4. `JSON.stringify(action.params)` shown raw to the operator
- **Where:** `CommandCenter.tsx` and `incident/IncidentTimeline.tsx` render `{JSON.stringify(action.params)}` as the action detail.
- **Why:** raw JSON in an operator console is a developer artifact, not product copy.
- **Fix:** format it: `reroute UPI: PSP-1 → PSP-3` from `params.method/from_psp/to_psp`; `disable card`, etc. A tiny `formatActionParams(action)` helper in `design/` or `lib/`.

### P1-5. Node glows drift toward the "neon" aesthetic the vision warns against
- **Where:** `topology/nodes.tsx` → `GLOW` (18–22px colored box-shadows on degraded/down nodes).
- **Why:** big colored glows read "cyberpunk dashboard." The vision says avoid neon; prefer restrained depth.
- **Fix:** dial glows down hard (tighter radius, lower alpha) or replace with a crisp 1px status ring + a subtle inner tint. Let motion (the pulse) carry "this node is sick," not a neon halo.

### P1-6. Command Center's "Revenue at risk" is mislabeled/possibly misleading
- **Where:** `CommandCenter.tsx` KPI uses `action.expected_recovery` as "Revenue at risk."
- **Why:** `expected_recovery` is the *estimated recoverable* amount, not revenue at risk. Two different concepts; the vision demands honest semantics.
- **Fix:** relabel to "Expected recovery (est.)" or compute a genuine at-risk figure from the dropped nodes' lost success × volume × avg_amount in the window. Don't overload one number with a wrong label.

---

## P2 — polish (do if time)

- **P2-1. No command palette / global search.** Vision §12 lists it. Top bar has a static "deterministic · seeded" chip and no ⌘K. Add a lightweight palette (navigate + run scenario) if time.
- **P2-2. Top bar is thin/underused.** Hardcoded "Merchant · Acme Commerce" with no breadcrumb, no scenario context, no real actions. Give it page context + the active scenario summary.
- **P2-3. Sidebar footer** "Simulated environment" dot is good (honest); but the sidebar has no active-incident indicator or count. Add a subtle live badge.
- **P2-4. `FrontierPanel` axis labels** use `position="bottom"`/`"left"` offsets that can clip; verify no overlap at small widths. Threshold labels via a `<text>` render can collide with dots — nudge/att stagger.
- **P2-5. `ConfidenceRing`** is good, but appears at two sizes with the same label treatment across incident + command center — standardize.
- **P2-6. No responsive story below ~1024px.** The `lg:grid-cols-2` collapses but the graph + side panel (`w-[340px]` fixed) will crowd on tablet. Vision wants responsiveness. At minimum make the topology side panel collapsible.
- **P2-7. Bundle 1MB** (React Flow + Recharts, no code-split). Fine for a demo; lazy-load the Evaluation route (Recharts) and Topology route (React Flow) with `React.lazy` if you want snappier first paint.
- **P2-8. Accessibility gaps.** Graph is `role="img"` (good) but the scenario story it tells isn't in an aria-live region; number-only KPI cards lack descriptive aria labels; focus-visible styling is inconsistent between the two control variants (fixed by P1-2).
- **P2-9. `MethodNode`/`PspNode`** show a `StatusDot` AND a colored ring AND a pulse AND (soon) a glow — triple/quadruple-encoding health. Pick two channels max (ring + pulse), drop the redundant dot on nodes.
- **P2-10. Empty `motion` usage** — several `whileInView` timeline steps re-animate on scroll; fine, but the Command Center audit list staggers `delay: i*0.05` which on a long list feels slow. Cap stagger.

---

## What is actually GOOD (keep it)
- Real API wiring end-to-end; **no fabricated numbers**; not-backable fields disclosed.
- Evidence path rendered **verbatim** (SidePanel, EvidencePath) — exactly the vision's "evidence is first-class."
- Honest **negative money** and **do-nothing-is-a-win** handling (RecoveryConsole, IncidentTimeline).
- SVG `<animateMotion>` traffic particles with a **hard cap + no rAF** — the right performance-safe call for the signature animation.
- Deterministic layered graph layout; health **derived** client-side (not an API row) — matches the observed-vs-derived principle.
- Frontier chart is real, honest ("no single optimal dial"), with per-seed variance surfaced (no overclaim).

## Bottom line
This is **not** a rewrite. It is: (1) wire the real graph into the Command Center [P0-1], (2) kill emojis for a real icon set [P0-2], (3) rebuild the two main page layouts with genuine hierarchy/density [P0-3], (4) de-duplicate controls/states into the design system [P1-2], (5) a pass of typography + neon-dialdown + label-honesty [P1-1/5/6] + raw-JSON [P1-4]. That sequence gets it from "AI slop" to "serious product" with the working brain untouched.
