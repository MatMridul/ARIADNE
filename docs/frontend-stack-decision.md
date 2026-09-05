# ARIA — Frontend Stack Decision

> **Status:** Decided (F0 output). Chosen for a ~12-hour sprint that must deliver a
> high visual ceiling, a living animated dependency graph, and a thin FastAPI seam
> over the existing Python core.
> **Scope note:** This freezes the *build* stack. It does not redesign the core
> (`src/ariadne/`) — the web layer wraps it (see `web/CONTRACT.md`).

## Decision summary

| Concern | Choice |
|---|---|
| Framework | **Vite + React 18 + TypeScript** (React Router for client routing) |
| UI kit | **shadcn/ui** (Radix primitives + Tailwind CSS) |
| Graph engine | **React Flow (@xyflow/react)** with custom nodes + animated SVG edges |
| Charts | **Recharts** (frontier scatter, time-series, distributions) |
| Animation | **Motion (framer-motion)** for UI/layout; **SVG `<animateMotion>` / CSS** for traffic particles on edges |
| State / data | **TanStack Query** (server state) + **Zustand** (small client/UI state) |
| API layer | **FastAPI** (thin, typed) wrapping the core; **Zod** validates responses client-side |
| Deploy | Vite static build served by FastAPI `StaticFiles`; single origin, one process |

## Rationale by concern

### Framework — Vite + React over Next.js
The product is a client-heavy operator console (a live graph, charts, incident
choreography), not a content/SEO site. Next's server rendering, routing conventions,
and build model add ceremony we do not need in a 12-hour sprint, and SSR fights an
animation-heavy canvas. Vite gives sub-second HMR (critical when several agents
iterate in parallel) and a dead-simple static build. React is the non-negotiable
substrate because the strongest graph engine (React Flow) and the widest component
ecosystem (shadcn/Radix) are React-first. React Router covers the handful of routes
(Command Center, Topology, Incident, Evaluation) without a meta-framework.

_Tradeoff:_ we forgo Next's file-based routing and API routes, but we deliberately
want the API in FastAPI (co-located with the Python core), so Next's API routes are
irrelevant. No SSR means no first-paint SEO — acceptable for an authenticated
operator tool.

### UI kit — shadcn/ui (Radix + Tailwind) over Mantine / MUI
shadcn is copy-in, not a dependency: components live in `web/src/design` as our own
source, so we can push the visual language toward the "Linear-polish / financial
control room" bar the vision demands instead of fighting a vendor theme. Radix under
the hood gives accessible, unstyled primitives (dialog, popover, command palette via
`cmdk`), and Tailwind gives fast, consistent spacing/typography tokens — exactly the
design-system layer F1 needs. Ownership is clean: the design tokens and primitives
are files we edit.

_Tradeoff:_ shadcn ships fewer batteries-included complex widgets than Mantine (e.g.
no built-in heavy data-grid), so the Transactions/Audit tables use TanStack Table +
shadcn primitives rather than a turnkey grid. For this sprint the flexibility and
visual ceiling outweigh the missing batteries; Mantine's default look also reads more
"generic dashboard," which the vision explicitly warns against.

### Graph engine — React Flow (@xyflow/react) over Cytoscape / D3
The living topology is ARIA's visual signature, and the two heaviest requirements
are **custom node rendering** (health-state PSP/bank/method nodes with pulsing,
badges, evidence highlighting) and **animated edge traffic** (particles that flow,
slow, and reroute to carry system semantics). React Flow makes custom nodes ordinary
React components — trivial to style with our design system and animate with Motion —
and lets us render fully custom SVG edges where we drop animated particles via
`<animateMotion>` along the edge path. Its React-native model means node state flows
straight from TanStack Query data with no imperative bridge. Our graph is tiny
(3 methods / 3 PSPs / 2 banks + merchant ≈ 9 nodes), so raw rendering scale is a
non-issue; developer ergonomics and custom-rendering freedom dominate.

_Tradeoff:_ Cytoscape has stronger built-in graph layout algorithms and scales to
thousands of nodes, and D3/Canvas gives ultimate control. But Cytoscape's canvas
rendering makes bespoke React node UIs and per-edge particle choreography harder, and
D3-from-scratch is too much hand-rolling for a 12-hour budget. With 9 fixed nodes we
do not need heavy auto-layout — a hand-placed layout matching the vision's
Merchant→Method→PSP→Bank columns is clearer and fully controllable in React Flow.

### Charts — Recharts
The charting needs are modest and well-defined: the recovery-vs-risk **frontier**
(scatter/line, one series per system, one point per threshold — mirrors
`reporting/frontier.py`), per-window success-rate time-series, and simple
distributions. Recharts is declarative React/SVG, themes cleanly with our tokens, and
is fast to wire. It is not the highest-ceiling charting library, but the plots here
are simple and legibility beats flourish.

_Tradeoff:_ for very dense/interactive analytics Visx or ECharts would give more
control; unnecessary at this scope and slower to build.

### Animation — Motion for UI, SVG/CSS for traffic
Split by responsibility, as the vision suggests. **Motion (framer-motion)** handles
component/layout transitions, incident state changes, and orchestrated reveals
(healthy → degradation → attribution → recovery). **Edge traffic particles** are
rendered as SVG circles animated along the edge path with `<animateMotion>` (or a
lightweight CSS keyframe on `offset-distance`), driven off each edge's health so
"flow slows/stops on degradation" is a data-bound visual, not decoration. GSAP is
deliberately **not** adopted: Motion covers the coordinated sequences we need, and
adding GSAP is extra weight/learning for no sprint-level gain.

### State / data — TanStack Query + Zustand
All meaningful state is server state (topology, simulation result, evaluation) from
the FastAPI endpoints — TanStack Query gives caching, loading/error states, and
refetch for free, which directly supports the vision's "strong empty/error/loading
states" bar. Zustand holds the small amount of pure UI state (selected incident,
active threshold slider, command-palette open) without Redux ceremony.

_Tradeoff:_ no global normalized cache (Redux Toolkit) — unneeded; the data is small
and read-mostly. No websocket/real-time layer in v1; the "alive" feel is driven by
client-side animation over the per-window arrays the simulate endpoint returns, and
the sweep is a one-shot fetch. (A future event-stream can layer on without changing
this decision.)

### API layer — thin FastAPI + client-side Zod
FastAPI sits in the same repo/process as the Python core and calls `run_once`,
`discrimination_result`, `run_sweep`, and `default_graph()` directly — no logic
duplicated, the API is a serialization boundary only (per vision §16). Pydantic types
the responses server-side; Zod re-validates them in `web/src/lib` so the frontend
types are enforced at the seam. The built Vite bundle is served by the same FastAPI
app via `StaticFiles`, so deploy is one process on one origin (no CORS, no separate
host) — the simplest thing that ships.

## What we explicitly are NOT doing in this sprint
- No SSR / meta-framework, no websockets/SSE, no GSAP.
- No database — the core is stateless per-request (simulation is seed-deterministic).
  Any endpoint implying persistence (audit log, incident history) is flagged in
  `web/CONTRACT.md` as derived-per-request or not-backable, per vision §20
  ("avoid fake product experiences").
