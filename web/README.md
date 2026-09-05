# ARIADNE Web

The operator-console frontend for ARIADNE and the thin FastAPI layer that wraps the
Python core. See `../docs/frontend-stack-decision.md` for why this stack, and
`./CONTRACT.md` for the exact API shapes (build against that file).

## Stack (frozen)
- **Framework:** Vite + React 18 + TypeScript (React Router)
- **UI kit:** shadcn/ui (Radix + Tailwind CSS)
- **Graph engine:** React Flow (`@xyflow/react`) — custom nodes + animated SVG edges
- **Charts:** Recharts
- **Animation:** Motion (framer-motion) for UI; SVG `<animateMotion>` / CSS for edge traffic
- **State/data:** TanStack Query (server) + Zustand (UI); Zod validates responses
- **API:** FastAPI wrapping `src/ariadne/`; single origin, static bundle served by FastAPI

## Prerequisites
- Node 20+ and npm
- Python 3.11+ with the repo installed editable (`pip install -e .` from repo root)
- Windows/PowerShell friendly (no bash-only constructs)

## Run — development (two processes, live reload)
Backend (from repo root `C:\Mridul\Programs\ARIADNE`):
```powershell
pip install -e .
pip install fastapi "uvicorn[standard]"
uvicorn web.api.main:app --reload --host 127.0.0.1 --port 8000
```
Frontend (from `web/`):
```powershell
cd web
npm install
npm run dev   # Vite dev server on http://127.0.0.1:5173
```
In dev, Vite proxies `/api` to the backend. Add to `web/vite.config.ts`:
```ts
server: { proxy: { "/api": "http://127.0.0.1:8000" } }
```
Open `http://127.0.0.1:5173`. Frontend calls `/api/...` (same-origin via proxy) — no
CORS config needed in dev.

## Run — production (one process, one origin)
```powershell
cd web
npm run build            # emits web/dist
cd ..
uvicorn web.api.main:app --host 127.0.0.1 --port 8000
```
`web/api/main.py` mounts the built bundle:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="web/dist", html=True), name="ui")
```
`/api/*` is served by FastAPI; everything else serves the SPA. One process, one origin,
no CORS.

## How the frontend talks to FastAPI
- All network access goes through the **single** client in `web/src/lib` (see below).
  No component calls `fetch` directly.
- The client fetches `/api/...`, Zod-validates the JSON against the schemas derived
  from `CONTRACT.md`, and hands typed objects to TanStack Query hooks.
- FastAPI handlers are thin: they import from `ariadne.*` and reshape output to the
  `CONTRACT.md` JSON. No domain logic in the API layer (vision §16).

## Directory-ownership map (for parallel frontend agents)
One owner per folder → clean parallel work, no merge collisions. **`web/src/lib` is the
single shared contract module** — every other folder depends on it and only it for
types + data.

```
web/
  api/                  FastAPI app (backend agent): endpoints from CONTRACT.md, wraps ariadne.*
  src/
    lib/        [SHARED] api-client + TypeScript types + Zod schemas. SINGLE source of
                        truth for the API contract. Owner: contract agent. Everyone imports
                        from here; nobody else defines API types or calls fetch.
    design/             design system (F1): Tailwind tokens, shadcn components, typography,
                        color, buttons, cards, tables, dialogs, command palette. Owner: design agent.
    shell/              app shell (F2): sidebar, top bar, routing, responsive layout,
                        account menu, global search, notifications. Owner: shell agent.
    topology/           living graph (F4): React Flow custom PSP/bank/method nodes, animated
                        traffic edges, semantic motion, dependency highlighting. Owner: topology agent.
    incident/           incident/command-center experience (F3+F5): state->topology->diagnosis
                        ->action->outcome, evidence panel, confidence, recovery console. Owner: incident agent.
    evaluation/         evaluation view (F7): ARIADNE vs baseline, frontier chart (Recharts),
                        per-seed variance, safety metrics. Owner: evaluation agent.
    pages/              route-level page compositions that assemble the above feature folders.
                        Owner: shell agent (thin; delegates to feature folders).
```

### Dependency rules
- `design/` depends on nothing internal (pure UI primitives).
- `lib/` depends on nothing internal (types + client only).
- `shell/`, `topology/`, `incident/`, `evaluation/`, `pages/` may import from `design/`
  and `lib/`, but **not** from each other. Cross-feature composition happens only in
  `pages/`.
- No folder outside `lib/` may declare an API type or call `fetch`/`axios` — always go
  through `lib/`.

### Contract-first workflow
1. Contract agent lands `web/src/lib` (types + Zod + client) from `CONTRACT.md` first.
2. Backend agent implements `web/api/` against the same contract.
3. Feature agents (`topology`, `incident`, `evaluation`) build in parallel against the
   typed hooks in `lib/`, using placeholder/loading states until the API is live.
4. Any field flagged **NOT-BACKABLE** in `CONTRACT.md` must render an explicit
   "simulated / not persisted" disclosure — never a fabricated number (vision §20).
