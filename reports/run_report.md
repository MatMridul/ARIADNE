# ARIADNE — run report

Seeds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]  |  Thresholds: [0.55, 0.7, 0.85]

RCA is shown as **unconditional** (all active-incident windows, detection misses included) **/ conditional** (windows where detection fired). The unconditional number is the honest headline; the conditional number is the historical detected-only figure, shown for continuity.

## Shared Dependency Discrimination result

| Incident | Metric | ARIADNE | Baseline |
|----------|--------|---------|----------|
| A shared-bank | root-cause accuracy (uncond/cond) | 0.94 uncond / 0.89 cond | 0.00 uncond / 0.00 cond |
| A shared-bank | money recovered | 131349 | 104313 |
| B single-PSP  | root-cause accuracy (uncond/cond) | 0.79 uncond / 0.85 cond | 0.79 uncond / 0.85 cond |
| E coincidental| root-cause accuracy (uncond/cond) | 0.78 uncond / 0.89 cond | 0.78 uncond / 0.90 cond |

- ARIADNE beats baseline on A (unconditional accuracy): **True**
- ARIADNE beats baseline on A (money): **True**
- No regression on B: **True**
- No over-attribution on E: **False**

### Per-seed variance (unconditional RCA, exposes fragility)

- A ARIADNE per-seed: [0.75, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
- A baseline per-seed: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
- E ARIADNE per-seed: [0.556, 1.0, 0.125, 1.0, 1.0, 0.2, 0.714, 1.0, 0.714, 1.0, 0.778, 0.75, 1.0, 1.0, 0.833, 1.0, 0.5, 0.5, 1.0, 0.857]
- E baseline per-seed: [0.556, 1.0, 0.125, 1.0, 1.0, 0.2, 0.714, 1.0, 0.857, 1.0, 0.778, 0.75, 1.0, 1.0, 0.833, 1.0, 0.5, 0.5, 1.0, 0.857]

## Recovery-vs-risk frontier + safety (measured, not asserted)

| System | Thr | Money recovered | False-interv cost | False-interv count | Unsafe-action rate | Executed actions | Unaudited | Do-nothing-correct | Do-nothing misses |
|--------|-----|-----------------|-------------------|--------------------|--------------------|------------------|-----------|--------------------|-------------------|
| ariadne | 0.55 | 515625 | 250 | 1 | 0.000 | 258 | 0 | 0.9988 | 1 |
| ariadne | 0.7 | 459788 | 250 | 1 | 0.000 | 217 | 0 | 0.9988 | 1 |
| ariadne | 0.85 | 418918 | 250 | 1 | 0.000 | 181 | 0 | 0.9988 | 1 |
| baseline | 0.55 | 407230 | 0 | 0 | 0.000 | 171 | 0 | 1.0000 | 0 |
| baseline | 0.7 | 332673 | 0 | 0 | 0.000 | 114 | 0 | 1.0000 | 0 |
| baseline | 0.85 | 262152 | 0 | 0 | 0.000 | 63 | 0 | 1.0000 | 0 |
