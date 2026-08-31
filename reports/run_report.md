# ARIADNE — run report

Seeds: [1, 2, 3, 4, 5]  |  Thresholds: [0.55, 0.7, 0.85]

## Shared Dependency Discrimination result

| Incident | Metric | ARIADNE | Baseline |
|----------|--------|---------|----------|
| A shared-bank | root-cause accuracy | 0.95 | 0.00 |
| A shared-bank | money recovered | 120235 | 87259 |
| B single-PSP  | root-cause accuracy | 0.95 | 0.95 |
| E coincidental| root-cause accuracy | 0.90 | 0.90 |

- ARIADNE beats baseline on A (accuracy): **True**
- ARIADNE beats baseline on A (money): **True**
- No regression on B: **True**
- No over-attribution on E: **True**

## Recovery-vs-risk frontier

| System | Threshold | Money recovered | False-interv. cost | Do-nothing-correct |
|--------|-----------|-----------------|--------------------|--------------------|
| ariadne | 0.55 | 567421 | 1000 | 1.00 |
| ariadne | 0.7 | 520356 | 1000 | 1.00 |
| ariadne | 0.85 | 437654 | 1000 | 1.00 |
| baseline | 0.55 | 373196 | 0 | 1.00 |
| baseline | 0.7 | 323504 | 0 | 1.00 |
| baseline | 0.85 | 203961 | 0 | 1.00 |
