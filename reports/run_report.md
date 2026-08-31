# ARIADNE — run report

Seeds: [1, 2, 3, 4, 5]  |  Thresholds: [0.55, 0.7, 0.85]

## Shared Dependency Discrimination result

| Incident | Metric | ARIADNE | Baseline |
|----------|--------|---------|----------|
| A shared-bank | root-cause accuracy | 0.95 | 0.00 |
| A shared-bank | money recovered | 107680 | 78440 |
| B single-PSP  | root-cause accuracy | 0.95 | 0.95 |
| E coincidental| root-cause accuracy | 0.95 | 0.95 |

- ARIADNE beats baseline on A (accuracy): **True**
- ARIADNE beats baseline on A (money): **True**
- No regression on B: **True**
- No over-attribution on E: **True**

## Recovery-vs-risk frontier

| System | Threshold | Money recovered | False-interv. cost | Do-nothing-correct |
|--------|-----------|-----------------|--------------------|--------------------|
| ariadne | 0.55 | 419453 | 1000 | 1.00 |
| ariadne | 0.7 | 419453 | 1000 | 1.00 |
| ariadne | 0.85 | 364114 | 1000 | 1.00 |
| baseline | 0.55 | 400293 | 0 | 1.00 |
| baseline | 0.7 | 356582 | 0 | 1.00 |
| baseline | 0.85 | 270319 | 0 | 1.00 |
