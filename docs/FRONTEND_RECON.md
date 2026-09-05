# ARIA Frontend Reconnaissance

> **Purpose:** repository truth-gathering for a separate design/spec phase. This is
> **read-only recon** — no redesign, no features, no backend/eval/API/dependency
> changes. It builds on `web/FRONTEND_AUDIT.md` (prior brutal audit) and
> `web/CONTRACT.md` (the frozen API contract), **verifying each finding against the
> LIVE render** at `http://127.0.0.1:8000` rather than repeating them from code.
>
> Compiled 2026-09-05 on branch `release/sept5` @ `b4239de`. Server verified up
> (FastAPI serving `/api` + the built SPA on one origin). Every finding below was
> either read from source or observed in a live Playwright screenshot (screenshots
> under `artifacts/frontend-recon/`).
>
> **Two live-only discoveries the prior code audit could not have seen** (both P0 for
> a live demo, both documented in §F and §H):
> 1. `GET /api/evaluation` with default params **does not complete within 10 minutes** —
>    the Evaluation route shows an infinite spinner. Not a hang; the synchronous sweep
>    is simply far too expensive to run per-request (measured 9.2s for 1 seed × 1
>    threshold; default is 20 seeds × 3 thresholds × 2 systems).
> 2. Hard-navigating to any sub-route (e.g. `/topology`) returns **HTTP 404** — the
>    FastAPI `StaticFiles` mount has no SPA fallback. A refresh or bookmark breaks the app.

---

## A. CURRENT STACK

### `web/package.json` — runtime dependencies (exact ranges)
| Package | Version | Role |
|---|---|---|
| `react` / `react-dom` | `^18.3.1` | UI runtime |
| `react-router-dom` | `^6.27.0` | client routing (`createBrowserRouter`) |
| `@tanstack/react-query` | `^5.59.0` | data fetching / caching seam (`useQuery`, `staleTime: Infinity`) |
| `@xyflow/react` | `^12.3.5` | React Flow — the payment topology graph |
| `recharts` | `^2.13.0` | the recovery-vs-risk frontier chart |
| `framer-motion` | `^11.11.0` | entrance/pulse motion |
| `zod` | `^3.23.8` | runtime API-response validation (single source of API types) |
| `zustand` | `^5.0.0` | **declared but UNUSED** — no `create`/store found in `src/**` (dead dependency) |
| `clsx` | `^2.1.1` | className composition |
| `tailwind-merge` | `^2.5.4` | `cn()` helper (merge Tailwind classes) |

### devDependencies
`typescript ^5.6.3`, `vite ^5.4.9`, `@vitejs/plugin-react ^4.3.2`,
`tailwindcss ^3.4.14`, `autoprefixer ^10.4.20`, `postcss ^8.4.47`,
`@types/react ^18.3.11`, `@types/react-dom ^18.3.1`.

**No icon library** (`lucide-react` etc.) — icons are emoji + hand-drawn SVG (see §F P0).
**No test runner** (no vitest / testing-library) in the web workspace.

### Config files
- `vite.config.ts` — `@` alias → `src/`; dev server `127.0.0.1:5173` proxies `/api` → `:8000`.
- `tailwind.config.js` — the full design-token palette (see §E).
- `tsconfig.json` + `tsconfig.tsbuildinfo` (strict build, `tsc -b && vite build`).
- `postcss.config.js` (tailwind + autoprefixer), `index.html` (loads Inter + JetBrains Mono from Google Fonts).
- `scripts`: `dev` = vite, `build` = `tsc -b && vite build`, `preview`, `lint` = `tsc -b --noEmit`.

---

## B. ARCHITECTURE

```
web/
├─ api/main.py            FastAPI — thin serialization boundary over ariadne.* core
├─ index.html             loads Inter + JetBrains Mono, mounts #root
├─ vite.config.ts / tailwind.config.js / postcss.config.js / tsconfig.json
└─ src/
   ├─ main.tsx            entry: QueryClientProvider + createBrowserRouter, 5 routes under <AppShell>
   ├─ shell/AppShell.tsx  sidebar (5 nav links) + top bar + <Outlet/>
   ├─ design/             DESIGN SYSTEM (frozen shared seam)
   │   ├─ ui.tsx          cn, StatusDot, Card, CardHeader, Badge, Button, Metric, inr()
   │   └─ globals.css     tailwind layers, dark color-scheme, .tabular (→ mono), scrollbars
   ├─ lib/                DATA SEAM (frozen shared seam)
   │   ├─ schemas.ts      Zod schemas + inferred TS types (single source of API shape)
   │   ├─ client.ts       the ONLY fetch layer (getJSON/postJSON, Zod-validates every response)
   │   ├─ hooks.ts        TanStack hooks: useTopology/useSimulate/useEvaluation/useIncidents/useAudit
   │   └─ index.ts        re-exports
   ├─ pages/              route-level pages (thin) — compose feature components
   │   ├─ CommandCenterPage → @/incident CommandCenter
   │   ├─ TopologyPage      → @/topology/TopologyPage (re-export)
   │   ├─ IncidentsPage     → @/incident IncidentExperience
   │   ├─ EvaluationPage    → @/evaluation EvaluationView
   │   ├─ AuditPage         → @/evaluation AuditView
   │   └─ placeholders.tsx  DEAD CODE — scaffold Cards no longer routed (see §F)
   ├─ topology/            FEATURE (11 files) — the living payment graph
   ├─ incident/            FEATURE (11 files) — command center + RCA timeline + recovery
   └─ evaluation/          FEATURE (10 files) — evaluation sweep + audit surfaces
```

**Import rule (observed, holds):** feature folders import only from `@/lib` + `@/design`,
never from each other; `pages/*` compose one feature each. The rule is what forced the
Command Center's graph placeholder — see §F P0-1.

- **Entry points:** `index.html` → `src/main.tsx` → `<RouterProvider>` with `<AppShell>` as the layout route.
- **Shell:** `shell/AppShell.tsx` — fixed 240px (`w-60`) sidebar + 56px (`h-14`) top bar + scrollable `<main>`.
- **Routes:** `/` (Command Center), `/topology`, `/incidents`, `/evaluation`, `/audit` — all children of `/` under `<AppShell>`. **No `errorElement`, no catch-all `*` route** (contributes to the hard-nav story, though the 404 is actually served by FastAPI, not the router — see §H).
- **Token files:** `tailwind.config.js` (palette + fonts + `2xs`), `design/globals.css` (base layer + `.tabular`).
- **API / client files:** `lib/client.ts` (fetch), `lib/hooks.ts` (query), `lib/schemas.ts` (types).
- **Viz / animation files:** `topology/PaymentGraph.tsx` (React Flow), `topology/nodes.tsx` (custom nodes), `topology/edges.tsx` (SVG `animateMotion` traffic particles), `topology/layout.ts` (layered positions), `topology/useScenarioPlayback.ts` (window playback state machine), `incident/ConfidenceRing.tsx` (SVG arc), `evaluation/FrontierPanel.tsx` (Recharts), `evaluation/Sparkline.tsx` (inline SVG).

---

## C. DATA CONTRACT MAP

The single client is `lib/client.ts`; every feature consumes it only through `lib/hooks.ts`.
All five endpoints are Zod-validated in `client.ts` (contract drift throws). Provenance flags
are lifted from `web/CONTRACT.md` and confirmed against `web/api/main.py`.

### `GET /api/topology` → `fetchTopology` / `useTopology`
- **Consumers:** `topology/TopologyPage.tsx` (+ `buildGraph.ts`, `deriveHealth.ts`).
- **Response:** `{merchant, methods[], psps[]{id,label,bank_id}, banks[]{id,label,role,shared,psps[]}, routing[]{method,psp_id,weight}, shared_banks{}}`.
- **Provenance:** all **observed** from `default_graph()` EXCEPT `merchant` = **DERIVED presentation node** (label only, no metric — the core has no Merchant entity). Nothing fabricated.

### `POST /api/simulate` → `fetchSimulate` / `useSimulate`
- **Request:** `{incident_type, seed, intervention_threshold, system}`.
- **Consumers:** `incident/CommandCenter.tsx`, `incident/IncidentExperience.tsx` (→ `IncidentTimeline`, `RecoveryConsole`, `ComparisonMini`), `topology/TopologyPage.tsx`.
- **Response fields & provenance:**
  | Field | Provenance |
  |---|---|
  | `incident.*` (type, target, windows, n_windows) | **observed** from `make_incident` |
  | `windows[].detection` (triggered, dropped_nodes) | **observed** per-window `Detection` |
  | `windows[].nodes[]` (success_rate, baseline_rate, delta, volume, avg_latency_ms) | **observed** `NodeStats` — **only `psp` + `method` kinds exist; NO bank row** |
  | `windows[].attribution` (root_cause_id/kind, confidence, evidence_path, claim_type, psp_causes) | **observed** `Attribution` — `evidence_path` rendered verbatim |
  | `windows[].action` (kind, params, decision_id, evidence_path, confidence, expected_recovery) | **observed** `Action`; `expected_recovery` is an ESTIMATE (labeled) |
  | `money_recovered` | **observed** real shared-seed counterfactual, **may be negative** (rendered honestly) |
  | `comparison.{ariadne,baseline}` | **observed** two real runs, same seed, system swapped |
- **Bank node health:** **DERIVED client-side** in `deriveHealth.ts` from the bank's PSP deltas (there is no bank NodeStat). Correct per contract.
- **Nothing fabricated.** The only synthesized fields are labels (`merchant`, incident glosses).

### `GET /api/evaluation` → `fetchEvaluation` / `useEvaluation`
- **Query:** `?seeds=`, `?thresholds=` (defaults 1..20 / 0.55,0.70,0.85).
- **Consumers:** `evaluation/EvaluationView.tsx` → `DiscriminationPanel`, `FrontierPanel`, `SafetyPanel`, `SeedVariancePanel`.
- **Response:** `{seeds[], thresholds[], discrimination{incident_A/B/E{ariadne,baseline}, 4 booleans}, frontier{ariadne[],baseline[]}}` — every field a direct pass-through of `run_sweep`.
- **Provenance:** all **observed / measured**, nothing fabricated. **⚠️ but the default query does not return in a usable time — see §F P0-EVAL.**

### `GET /api/incidents` → `fetchIncidents` / `useIncidents`
- **Consumers:** hook exists; **no component currently calls `useIncidents`** (the enum catalog is hardcoded inside `incident/helpers.ts INCIDENT_META` and `evaluation/AuditView.tsx INCIDENT_OPTIONS` instead). So this endpoint is **live but unconsumed** — a duplicated source of truth (see §F).
- **Provenance:** `id`/`target` observed; `label` + `expected_correct_behavior` = **DERIVED** presentation strings. Static catalog, not a live feed.

### `GET /api/audit` → `fetchAudit` / `useAudit`
- **Query:** `{incident_type, seed, intervention_threshold, system}`.
- **Consumers:** `evaluation/AuditView.tsx`, `incident/CommandCenter.tsx` (Recent activity list).
- **Response:** `{source:"derived-from-run", scenario{}, entries[]{window, decision_id, action_kind, params, confidence, evidence_path, audited}}`.
- **Provenance:** action fields **observed**; `audited` **derived** (`is_action_audited`); `window` = simulation window index. **⚠️ NOT-BACKABLE (correctly omitted):** wall-clock time, operator identity, cross-session history, executed-vs-proposed status. UI discloses `source: derived-from-run` and that `window` is not clock time. **No fabrication.**

**Summary:** every rendered number traces to a real core producer. The only synthesized
values are non-metric labels. The honesty discipline the vision demands is intact in the data layer.

---

## D. SCREEN INVENTORY

Viewport captured at **1440×900**. In-app navigation used (sidebar links) because hard-nav 404s (see §H). Screenshots in `artifacts/frontend-recon/`.

### `/` — Command Center — `incident/CommandCenter.tsx` → screenshot `01-command-center.png`
- **Layout:** centered `max-w-6xl` stack. Header (title + "active incident" badge) → 4-up KPI strip (one `Card`, `divide-x`) → 2-col grid [Payment topology slot | Active diagnosis] → 2-col grid [Recommended action | Recent activity].
- **Regions/components:** `Metric` ×4 (Revenue at risk / Recovered revenue / Success rate / Active incident), `TopologySlot` (**dashed placeholder** — see §F P0-1), `ConfidenceRing` (100%), `EvidencePath` (verbatim 4-step), action `Badge` + raw `JSON.stringify` params, audit `<ul>` with framer-motion stagger.
- **Charts/graph/motion:** ConfidenceRing SVG arc animates; audit list staggers in. **No real graph on this page.**
- **Interaction:** none (static hero scenario A_shared_bank / seed 7 / τ0.70, hardcoded `DEFAULT_REQ`).
- **Loading/empty/error:** `LoadingState` spinner / `ErrorState` card (from `incident/States.tsx`).
- **a11y:** headings present; KPI cards number-only (no descriptive aria); "✓ audited / ⚠ unaudited" uses emoji glyphs.
- **Live observation:** dashed "graph slot — topology feature" box is prominent center-left; KPI numbers render in **mono** (terminal look); "REVENUE AT RISK ₹1,11,561" uses `expected_recovery` (mislabel per audit P1-6).

### `/topology` — Payment Topology — `topology/TopologyPage.tsx` → `02-topology.png`
- **Layout:** full-height column: `ScenarioControls` bar → thesis banner (A only) → [React Flow graph (flex-1) | 340px right `SidePanel`].
- **Regions/components:** `ScenarioControls` (incident radios, ariadne/baseline toggle, seed input, playback ◀ ▶ / Play), thesis banner, `PaymentGraph` (React Flow: MerchantNode/MethodNode/PspNode/BankNode + FlowEdge), `Legend` (bottom-left overlay), `SidePanel` (Detection / Attribution / Outcome cards).
- **Graph/motion:** live layered graph Merchant→Method→PSP→Bank; SVG `animateMotion` traffic particles (speed = health); node pulse when unhealthy; bank glow shadows. React Flow `Controls` + dotted `Background`.
- **Interaction:** rich — change incident/system/seed, scrub windows, play the incident story.
- **Loading/empty/error:** `CenterCard` "Loading topology…" (`animate-ping` dot) / error / empty; sim error shows an inline banner over the static graph.
- **Live observation:** graph renders correctly (Bank-A shows `SHARED · 2 PSPs`, Bank-B `1 PSP`). At window 1/20 all nodes green ("quiet", "Diagnosis appears once the incident window is reached") — **the thesis is only visible after pressing Play / scrubbing forward**; the graph does not open on the diagnosed frame. Merchant node uses a **storefront emoji** (§F P0-2).

### `/incidents` — Incidents & RCA — `incident/IncidentExperience.tsx` → `03-incidents-rca.png`
- **Layout:** `max-w-6xl`. Controls `Card` (incident type pills, seed, risk-dial pills, expected-behaviour box, simulated disclosure) → 2-col `[1fr_360px]`: left = `IncidentTimeline` (6-step vertical spine), right = `RecoveryConsole` + `ComparisonMini`.
- **Regions/components:** `ScenarioControls` (incident-owned variant), `IncidentTimeline` steps 1–6 (Healthy → Degradation → Graph reasoning → Attribution → Decision → Outcome), `ConfidenceRing`, `EvidencePath`, `RecoveryConsole` (Execute / Do-nothing buttons + reveal), `ComparisonMini` (ARIA vs baseline side-by-side).
- **Charts/motion:** ConfidenceRing; each step `whileInView` entrance; RecoveryConsole `AnimatePresence` reveal.
- **Interaction:** change incident/seed/threshold (re-runs); Execute/Do-nothing toggle.
- **Live observation:** **strongest surface.** Timeline reads as a real story; ComparisonMini shows ARIA → Bank-A (bank) vs baseline → PSP-1 (psp) on the same seed — the thesis made explicit. Note: both sides show `money recovered ₹2,60,137` (the comparison money-per-side can read as "baseline recovered the same" — a labeling nuance for the design phase, not a data bug).

### `/evaluation` — Evaluation — `evaluation/EvaluationView.tsx` → `04-evaluation-loading-defect.png`
- **Intended layout (from code):** `max-w-6xl` header → sweep summary line → `DiscriminationPanel` (3 incident cards + 4 pass/fail chips) → `FrontierPanel` (Recharts recovery-vs-cost) → `SafetyPanel` (per-threshold table) → `SeedVariancePanel` (per-seed sparklines).
- **Charts:** Recharts `LineChart` frontier (τ-labelled points, invisible Scatter to span axes); inline SVG `Sparkline` per seed; RCA comparison bars.
- **Loading/empty/error:** `LoadingState` (role=status, aria-live) / `ErrorState` (role=alert) / `EmptyState`.
- **Live observation — DEFECT:** the page **never left the "Running evaluation sweep…" spinner** across a 10-minute observation. The four panels could not be captured live because the default sweep does not return (see §F P0-EVAL, §H). The panel code is sound; the blocker is the endpoint cost, not the UI.

### `/audit` — Audit Log — `evaluation/AuditView.tsx` → `05-audit-log.png`
- **Layout:** `max-w-5xl`. Header → `Disclosure` (derived-from-run banner) → Scenario `Card` (4 native `<select>`) → Audited-actions `Card` (`<ul>`).
- **Regions/components:** 4 `<select>` (incident / seed / threshold / system), per-entry row: `window N` badge, action-kind badge, decision_id, audited/UNAUDITED badge + conf, **formatted param chips** (`method=upi`, `from_psp=psp_1`), verbatim evidence path `<ol>`.
- **Motion:** rows stagger in.
- **Interaction:** dropdowns re-run `useAudit`.
- **Live observation:** clean and honest. Params are **formatted here** (chips), unlike CommandCenter's raw JSON — an internal inconsistency. Controls are **unstyled OS `<select>`** — the one obvious break from the premium dark aesthetic on this page (§F).

---

## E. DESIGN SYSTEM INVENTORY

### Tokens — `tailwind.config.js`
- **Backgrounds:** `bg-base #0a0e14`, `bg-surface #111722`, `bg-raised #161d2b`, `bg-hover #1c2534`.
- **Borders:** `border-subtle #1f2937`, `border-DEFAULT #2a3646`, `border-strong #3a4a5f`.
- **Text:** `text-primary #e6edf3`, `text-secondary #9aa7b8`, `text-muted #5e6b7e`.
- **Semantic status:** `healthy #2dd4a7`, `degraded #f5a623`, `down #f45b6c`, `info #4f9cf9`, `accent #6d8bff`.
- **Fonts:** `sans = Inter`, `mono = JetBrains Mono`. **Extra size:** `2xs = 0.6875rem/1rem` (used everywhere — the UI is very small-text-heavy).
- **globals.css:** `color-scheme: dark`; body uses `bg.base` + Inter; custom 10px scrollbars; **`.tabular` maps to `font-variant-numeric: tabular-nums` AND `font-family: mono`** — this is why all KPI numbers read terminal-y (root of audit P1-1).

### Primitives — `design/ui.tsx`
- **Radii:** `Card`/`Badge`/`Button` use `rounded-xl` / `rounded-md` / `rounded-lg` (three radii, not one scale).
- **Card:** `rounded-xl border border-border-subtle bg-bg-surface` + a faint inset shadow. `CardHeader` (title/subtitle/right).
- **Badge tones:** neutral / healthy / degraded / down / info / accent (each `bg-*/10 text-* border-*/30`).
- **Button variants:** primary (accent) / secondary / ghost / danger (down).
- **Metric:** label (`2xs uppercase`) + `text-2xl font-semibold tabular` value + optional hint. Tone maps to healthy/degraded/down/default.
- **StatusDot:** 2.5×2.5 with optional `animate-ping` pulse. **inr():** `₹` + `en-IN` grouping, sign-aware (negatives shown).

### Duplicated / inconsistent values (EXPLICIT)
- **Hardcoded hex OUTSIDE the token system** (design-token drift — must be reconciled by any redesign):
  - `topology/edges.tsx`: `STROKE` map `#2dd4a7 / #f5a623 / #f45b6c / #2a3646`, plus literal `#6d8bff` (highlight) and `#2dd4a7` (reroute) — duplicates the palette as raw strings.
  - `topology/nodes.tsx`: `GLOW` box-shadows with literal `rgba(45,212,167,…) / rgba(245,166,35,…) / rgba(244,91,108,…)` (the healthy/degraded/down colors again, as rgba).
  - `topology/PaymentGraph.tsx`: `Background color="#1f2937"` (= `border-subtle` literal).
  - `incident/ConfidenceRing.tsx`: `HEALTH_STROKE` map `#2dd4a7/#f5a623/#f45b6c/#3a4a5f` + track `#1f2937`.
  - `evaluation/FrontierPanel.tsx`: literals `#1f2937 / #5e6b7e / #9aa7b8 / #3a4a5f / #6d8bff` in axes, grid, ticks, lines.
  - `evaluation/Sparkline.tsx`: `#f45b6c / #f5a623 / #6d8bff / #2a3646 / #3a4a5f` literals.
  - **Every one of these is a re-typed copy of a Tailwind token** — there is no shared JS/TS color constant, so SVG/Recharts drift from the CSS palette independently.
- **`.tabular` conflation:** the class means BOTH "tabular numerals" and "mono font" — so any large number is forced into JetBrains Mono. There is no "tabular Inter" utility.
- **Radius inconsistency:** nodes use `rounded-xl`, badges `rounded-md`, buttons/inputs `rounded-lg`, small chips `rounded` — four radii, no single scale token.
- **Two `ScenarioControls` with different `ScenarioState` shapes** and **two `States.tsx`** (see §F) — visual + structural duplication.

---

## F. CODE SMELL AUDIT

Classified **P0 (demo blocker)** / **P1 (serious)** / **P2 (cleanup)**. Verified against the live render where possible.

### P0 — blockers
- **P0-1 · Dead placeholder shipped as the hero visual.** `incident/CommandCenter.tsx` → `TopologySlot()` renders a dashed box "graph slot — topology feature". **Confirmed live** on `/` (screenshot 01): the landing page's centerpiece is an empty placeholder while the real `<PaymentGraph>` exists in `topology/`. Root cause = the "features never import each other" rule + no shell composition. (Matches audit P0-1.)
- **P0-2 · Emoji as iconography.** `topology/nodes.tsx MerchantNode` renders `🏬`. **Confirmed live** (screenshot 02). Also emoji glyphs `✓`/`⚠` in `CommandCenter` audit list. No icon library installed. (Matches audit P0-2.)
- **P0-3 · "Generic cards everywhere," no hierarchy.** **Confirmed live** — Command Center is Card→2×2 grid→2×2 grid of equal-weight cards; Evaluation is a vertical stack of full-width cards. No focal point, no density variation. (Matches audit P0-3.)
- **P0-EVAL · Evaluation route never loads (LIVE-ONLY, new).** `GET /api/evaluation` with default params (20 seeds × 3 thresholds × 2 systems) **did not return within 10 minutes** in testing; measured **9.2s for 1 seed × 1 threshold** in isolation, so the default is inherently minutes-long. `useEvaluation` fires it with no reduced default, no pagination, no progressive rendering, no request timeout → **infinite spinner** (screenshot 04). This is the engineering-credibility surface and it is unusable in a live demo. *(This is an API-cost / call-pattern problem surfaced by the frontend, not a UI-code bug — recorded here as the frontend symptom; any fix touches backend/call-pattern and is out of recon scope.)*
- **P0-NAV · Hard-nav / refresh → HTTP 404 (LIVE-ONLY, new).** `web/api/main.py` mounts `StaticFiles(directory=dist, html=True)` at `/` with **no SPA catch-all**. **Confirmed live:** `GET /topology` → `404 Not Found` (screenshot 06). Any refresh, deep link, or bookmark of a sub-route breaks the app. In-app sidebar nav works (client router), so it only bites on reload — exactly what a judge does.

### P1 — serious
- **P1-1 · Mono on big numbers.** `.tabular` forces JetBrains Mono on every `Metric` value → terminal look. **Confirmed live** on all KPI strips. (Audit P1-1.)
- **P1-2 · Duplicated `ScenarioControls` (×2) and `States` (×2).** `topology/ScenarioControls.tsx` vs `incident/ScenarioControls.tsx` (different `ScenarioState` shapes: `{incident,seed,system}` vs `{incident_type,seed,intervention_threshold}`); `incident/States.tsx` vs `evaluation/States.tsx` (different spinner styles). Guarantees drift. (Audit P1-2.)
- **P1-3 · Generic spinners, not skeletons.** `incident/States` (`animate-spin` ring), `topology` (`animate-ping` dot), `evaluation/States` (spin). The Evaluation spinner is the one the user stares at for minutes (compounds P0-EVAL). (Audit P1-3.)
- **P1-4 · Raw `JSON.stringify(action.params)` shown to the operator.** `incident/CommandCenter.tsx` AND `incident/IncidentTimeline.tsx`. **Inconsistent** with `evaluation/AuditView.tsx`, which formats params as chips (`method=upi`) — so the app formats params in one place and dumps raw JSON in two others. (Audit P1-4, sharpened by the live inconsistency.)
- **P1-5 · Neon-ish node glows.** `topology/nodes.tsx GLOW` (18–22px colored box-shadows) drifts toward cyberpunk. (Audit P1-5.)
- **P1-6 · "Revenue at risk" mislabel.** `CommandCenter` KPI shows `expected_recovery` under the label "Revenue at risk" — two different concepts. **Confirmed live** (screenshot 01). (Audit P1-6.)
- **P1-7 · Unstyled native `<select>` (LIVE-ONLY, new).** `evaluation/AuditView.tsx` uses four raw OS `<select>` dropdowns (screenshot 05) — the most visible aesthetic break on an otherwise-clean page.
- **P1-8 · Thesis not visible on first paint of `/topology` (LIVE-ONLY, new).** The graph opens at window 1/20 all-green ("quiet"); the shared-bank story only appears after the user presses Play or scrubs. A judge glancing at the Topology page sees a healthy graph, not the thesis. (Product/staging gap, not a code bug — flag for the design phase.)

### P2 — cleanup
- **P2-1 · Dead code: `pages/placeholders.tsx`** — five scaffold components no longer routed (`main.tsx` imports the real pages). Ships in the bundle for nothing.
- **P2-2 · Dead dependency: `zustand`** declared but never used in `src/**`.
- **P2-3 · Unconsumed endpoint / duplicated catalog:** `useIncidents` + `GET /api/incidents` exist but no component calls them; the incident catalog is hardcoded twice instead (`incident/helpers.ts`, `evaluation/AuditView.tsx`).
- **P2-4 · Top bar is static filler:** hardcoded "Merchant · Acme Commerce" + "deterministic · seeded" chip; no breadcrumb, no page context, no scenario summary. (Audit P2-2.)
- **P2-5 · No command palette / global search** (audit P2-1); sidebar has no active-incident indicator (audit P2-3).
- **P2-6 · Health quadruple-encoded on nodes:** StatusDot + ring + pulse + glow all encode the same health. (Audit P2-9.)
- **P2-7 · Weak responsive story:** fixed `w-[340px]`/`w-[360px]` side panels + `lg:grid-cols-2` will crowd < 1024px; topology side panel not collapsible. (Audit P2-6.)
- **P2-8 · No code-splitting:** React Flow + Recharts in one ~1MB bundle, no `React.lazy` per route. (Audit P2-7.)
- **P2-9 · a11y gaps:** number-only KPI cards lack descriptive aria; emoji status glyphs; focus-visible inconsistent across the two control variants; graph story not in an aria-live region. (Audit P2-8.)
- **P2-10 · Motion stagger** on the audit list (`delay: i*0.05`) feels slow on long lists (audit P2-10).
- **P2-11 · Leftover untracked files** at repo root: `frontier.png`, `run_demo.py` (pre-existing; not web/, noted for housekeeping).

### What is GOOD (do NOT touch — confirmed live)
- Real API wiring end-to-end; **no fabricated numbers**; Zod-validated contract; not-backable fields correctly omitted and disclosed.
- **Evidence path rendered verbatim** everywhere (SidePanel, EvidencePath, timeline, audit).
- Honest **negative-money** and **do-nothing-is-a-win** handling (RecoveryConsole, IncidentTimeline).
- SVG `animateMotion` traffic particles — hard-capped at 2/edge, no rAF (performance-safe signature animation).
- **Bank health derived client-side** from PSP deltas (matches the observed-vs-derived principle exactly).
- Frontier / SeedVariance panels surface per-seed variance, ties, and negatives honestly (no overclaim) — the code is sound; only the load time blocks it.
- The Incidents/RCA timeline is a genuinely well-told story (best surface).

---

## G. TOPOLOGY IMPLEMENTATION

Files: `topology/{PaymentGraph, TopologyPage, nodes, edges, types, layout, buildGraph, deriveHealth, ScenarioControls, Legend, useScenarioPlayback}`.

- **React Flow usage** (`PaymentGraph.tsx`): non-interactive viz — `nodesDraggable/Connectable/elementsSelectable={false}`, `fitView`, dark color mode, dotted `Background`, `Controls` (no interactive toggle), attribution hidden. Stable `nodeTypes`/`edgeTypes` via `useMemo`.
- **Node/edge models** (`types.ts`): `MerchantNodeData`, `MethodNodeData{health}`, `PspNodeData{bankId,health,onEvidencePath,rerouteTarget}`, `BankNodeData{role,shared,pspIds,health,coverage,isRootCause}`; `FlowEdgeData{health,highlighted,reroute}`.
- **Custom nodes** (`nodes.tsx`): a shared `Shell` (ring color = health, glow, accent emphasis, framer pulse when unhealthy). Merchant (**emoji**), Method, Psp (evidence/reroute badges), Bank (**SHARED · N PSPs** badge, ROOT CAUSE badge, "% of its PSPs breached").
- **Custom edges** (`edges.tsx`): `FlowEdge` bezier + SVG `animateMotion` particles; `DUR` by health (healthy 2.2s / degraded 5.5s / down 0 = stopped); `PARTICLES=2` hard cap; highlighted=accent, reroute=green, down=dashed low-opacity.
- **Layout** (`layout.ts`): deterministic layered columns Merchant(0)→Method(260)→PSP(560)→Bank(860), rows vertically centered per column (`ROW_GAP=120`). Pure function of topology (no jitter).
- **Semantic-highlight data available:** `attribution.psp_causes` (evidence PSPs) + `root_cause_kind==="bank"` drive `onEvidencePath` / `isRootCause` / edge `highlighted`; `deriveHealth.ts` gives per-node health + bank coverage. `rerouteTarget` from `action.params.to_psp`.
- **What's MISSING to make the graph the primary visual signature (facts, not prescriptions):**
  - The graph lives **only on `/topology`**, not on the landing page (`/` shows the placeholder — P0-1).
  - It **opens un-diagnosed** (window 1, all healthy) — the thesis state requires user-driven playback (P1-8); no auto-advance to the representative/diagnosed window.
  - Nodes are **generic rounded boxes** with `METHOD`/`PSP`/`BANK · role` labels — they read as flowchart boxes, not domain objects (no method-specific glyphs, no bank/PSP visual identity beyond a badge).
  - Health is **quadruple-encoded** (dot+ring+pulse+glow) yet the shared-bank convergence (the whole point) is carried by a text badge + edge highlight, not a dominant visual.
  - Colors are **hardcoded hex** in `edges.tsx`/`nodes.tsx`, decoupled from the CSS tokens (§E) — theming the graph and the chrome are two separate edits today.

---

## H. PLAYWRIGHT VERIFICATION

Server: `http://127.0.0.1:8000` (FastAPI + built SPA, one origin). Viewport 1440×900. Screenshots copied to `C:\Mridul\Programs\ARIA\artifacts\frontend-recon\`.

| # | Route | How reached | Result | Screenshot |
|---|---|---|---|---|
| 1 | `/` Command Center | direct load | OK — dashed graph placeholder confirmed live | `01-command-center.png` |
| 2 | `/topology` | in-app click | OK — real React Flow graph, SHARED Bank-A, emoji merchant, all-green at window 1 | `02-topology.png` |
| 3 | `/incidents` | in-app click | OK — 6-step timeline + ComparisonMini (ARIA→Bank-A vs baseline→PSP-1) | `03-incidents-rca.png` |
| 4 | `/evaluation` | in-app click | **DEFECT** — infinite "Running evaluation sweep…" spinner (>10 min, never resolved) | `04-evaluation-loading-defect.png` |
| 5 | `/audit` | in-app click | OK — derived-from-run banner, native selects, formatted param chips | `05-audit-log.png` |
| 6 | `/topology` (hard-nav) | direct URL | **DEFECT** — HTTP 404 (no SPA fallback) | `06-defect-hardnav-404.png` |

- **Console errors:** only `favicon.ico 404` (harmless) on every route. **No app-level JS errors** on any surface.
- **API timing observed:** `/api/topology` 0.6s; `/api/simulate` (single) sub-second (Command Center/Incidents/Audit load fine); **`/api/evaluation` default > 600s (timed out at 10 min)**; `run_sweep(seeds=[1], thresholds=(0.7,))` = 9.2s in isolation.
- **Viewport / layout defects:** at 1440×900 all OK surfaces render cleanly; responsive < 1024px not tested but flagged in code (P2-7).

---

## I. GIT SAFETY

- **Branch:** `release/sept5`
- **HEAD:** `b4239de docs(web): brutal frontend design audit (3 P0, 6 P1, 10 P2) with fixes + what to keep`
- **Working tree (`git status --short`):**
  - `?? artifacts/` — the recon screenshots created this session (new, untracked)
  - `?? frontier.png` — pre-existing untracked leftover (repo root)
  - `?? run_demo.py` — pre-existing untracked leftover (repo root)
- **Commits made this session:** **NONE** (per instruction — no `git commit`).
- **Backend / eval / API / src changes:** **NONE.** No file under `src/`, `web/api/`, `eval/`, or any dependency manifest was modified. Only new files created: `docs/FRONTEND_RECON.md` and `artifacts/frontend-recon/*.png`.
- **Server:** untouched (read-only requests only).

---

## REDESIGN CONSTRAINTS (facts the design phase MUST preserve)

*These are load-bearing invariants, not aesthetic choices. The new design is free to change everything visual; it must NOT break any of the following.*

1. **Exact API contract** — the five endpoints and their shapes in `web/CONTRACT.md` / `lib/schemas.ts` are frozen. Preserve endpoints, request/response fields, and the provenance flags (observed / derived / not-backable). Any new component must consume data only through `lib/hooks.ts`.
2. **3/3/2 topology** — 3 methods (UPI/Card/Netbanking) → 3 PSPs → 2 banks: **psp_1 & psp_2 settle via the SHARED bank_A; psp_3 via bank_B.** The shared-bank structure is the thesis; keep it visually unmistakable.
3. **Honesty rules (non-negotiable):** no fabricated numbers; **negative money shown** (never clipped); **do-nothing is a valid win** (not a failure); **bank health is DERIVED** from PSP deltas, never a fed metric; **evidence_path rendered verbatim**; simulated/derived-from-run status disclosed in-UI.
4. **Deterministic seed model** — every surface is reproducible from `(incident_type, seed, intervention_threshold, system)`; identical inputs → identical output. Keep the scenario selector semantics.
5. **SPA fallback required** — the FastAPI static mount needs an SPA catch-all so hard-refresh / deep links to `/topology`, `/incidents`, etc. return `index.html` instead of 404. (Backend fix; recorded as a constraint, not applied here.)
6. **Evaluation call-pattern must change to be demo-usable** — the default full sweep does not return in usable time. The design/spec phase must account for a reduced default, precompute/caching, progressive rendering, or a background job — the current fire-a-blocking-full-sweep-on-mount pattern cannot ship in a live demo. (Recorded as a constraint; no fix applied.)
7. **Preserve the good** — real data wiring, verbatim evidence, honest money/do-nothing handling, derived bank health, performance-safe SVG traffic animation, and per-seed honesty surfaces are correct and must survive the redesign.

*(This recon deliberately proposes NO new aesthetic. It states what exists and what must be preserved.)*
