# ARIA — run report

Seeds: [1, 2, 3]  |  Thresholds: [0.55, 0.7, 0.85]

RCA is shown as **unconditional** (all active-incident windows, detection misses included) **/ conditional** (windows where detection fired). The unconditional number is the honest headline; the conditional number is the historical detected-only figure, shown for continuity.

## Shared Dependency Discrimination result

| Incident | Metric | ARIA | Baseline |
|----------|--------|---------|----------|
| A shared-bank | root-cause accuracy (uncond/cond) | 0.92 uncond / 0.92 cond | 0.00 uncond / 0.00 cond |
| A shared-bank | money recovered | 101353 | 46393 |
| B single-PSP  | root-cause accuracy (uncond/cond) | 0.73 uncond / 0.92 cond | 0.73 uncond / 0.92 cond |
| E coincidental| root-cause accuracy (uncond/cond) | 0.56 uncond / 0.83 cond | 0.56 uncond / 0.83 cond |

- ARIA beats baseline on A (unconditional accuracy): **True**
- ARIA beats baseline on A (money): **True**
- No regression on B: **True**
- No over-attribution on E: **True**

### Per-seed variance (unconditional RCA, exposes fragility)

- A ARIA per-seed: [0.75, 1.0, 1.0]
- A baseline per-seed: [0.0, 0.0, 0.0]
- E ARIA per-seed: [0.556, 1.0, 0.125]
- E baseline per-seed: [0.556, 1.0, 0.125]

## Recovery-vs-risk frontier + safety (measured, not asserted)

| System | Thr | Money recovered | False-interv cost | False-interv count | Unsafe-action rate | Executed actions | Unaudited | Do-nothing-correct | Do-nothing misses |
|--------|-----|-----------------|-------------------|--------------------|--------------------|------------------|-----------|--------------------|-------------------|
| ariadne | 0.55 | 446510 | 1667 | 1 | 0.000 | 33 | 0 | 0.9917 | 1 |
| ariadne | 0.7 | 404873 | 1667 | 1 | 0.000 | 28 | 0 | 0.9917 | 1 |
| ariadne | 0.85 | 366967 | 1667 | 1 | 0.000 | 25 | 0 | 0.9917 | 1 |
| baseline | 0.55 | 305456 | 0 | 0 | 0.000 | 18 | 0 | 1.0000 | 0 |
| baseline | 0.7 | 222637 | 0 | 0 | 0.000 | 9 | 0 | 1.0000 | 0 |
| baseline | 0.85 | 162801 | 0 | 0 | 0.000 | 7 | 0 | 1.0000 | 0 |
