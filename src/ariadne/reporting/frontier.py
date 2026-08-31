"""The headline figure (BUILD_SPEC §3.15).

Recovery-vs-risk frontier: x = false_intervention_cost, y = money_recovered, one
point per intervention threshold, one series for ARIADNE and one for the baseline.

matplotlib is used ONLY here (the sole reporting-side exception to stdlib-only).
Kept isolated so core logic never imports it.
"""
from __future__ import annotations


def plot_frontier(sweep_result: dict, out_path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")  # headless / deterministic file output
    import matplotlib.pyplot as plt

    frontier = sweep_result["frontier"]
    fig, ax = plt.subplots(figsize=(8, 6))

    styles = {
        "ariadne": {"color": "#1f77b4", "marker": "o", "label": "ARIADNE (relational)"},
        "baseline": {"color": "#d62728", "marker": "s", "label": "Baseline (independent)"},
    }

    for system, pts in frontier.items():
        pts_sorted = sorted(pts, key=lambda p: p["false_intervention_cost"])
        xs = [p["false_intervention_cost"] for p in pts_sorted]
        ys = [p["money_recovered"] for p in pts_sorted]
        st = styles.get(system, {"marker": "x", "label": system})
        ax.plot(xs, ys, marker=st["marker"], color=st.get("color"),
                label=st["label"], linewidth=2, markersize=9)
        for p in pts_sorted:
            ax.annotate(
                f"thr={p['threshold']}",
                (p["false_intervention_cost"], p["money_recovered"]),
                textcoords="offset points", xytext=(8, 6), fontsize=8,
            )

    ax.set_xlabel("False-intervention cost (lower is safer)")
    ax.set_ylabel("Money recovered across the batch")
    ax.set_title(
        "ARIADNE — recovery vs. risk frontier\n"
        "(the merchant chooses the intervention threshold)"
    )
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def write_report(sweep_result: dict, out_path: str) -> None:
    """A short markdown run report summarising the sweep + discrimination result.
    Stdlib only (no matplotlib needed)."""
    d = sweep_result["discrimination"]
    a = d["incident_A_shared_bank"]
    b = d["incident_B_single_psp"]
    e = d["incident_E_coincidental"]
    lines = [
        "# ARIADNE — run report",
        "",
        f"Seeds: {sweep_result['seeds']}  |  Thresholds: {sweep_result['thresholds']}",
        "",
        "## Shared Dependency Discrimination result",
        "",
        "| Incident | Metric | ARIADNE | Baseline |",
        "|----------|--------|---------|----------|",
        f"| A shared-bank | root-cause accuracy | {a['ariadne']['root_cause_accuracy']:.2f} | {a['baseline']['root_cause_accuracy']:.2f} |",
        f"| A shared-bank | money recovered | {a['ariadne']['money_recovered']:.0f} | {a['baseline']['money_recovered']:.0f} |",
        f"| B single-PSP  | root-cause accuracy | {b['ariadne']['root_cause_accuracy']:.2f} | {b['baseline']['root_cause_accuracy']:.2f} |",
        f"| E coincidental| root-cause accuracy | {e['ariadne']['root_cause_accuracy']:.2f} | {e['baseline']['root_cause_accuracy']:.2f} |",
        "",
        f"- ARIADNE beats baseline on A (accuracy): **{d['A_ariadne_beats_baseline_rca']}**",
        f"- ARIADNE beats baseline on A (money): **{d['A_ariadne_beats_baseline_money']}**",
        f"- No regression on B: **{d['B_no_regression']}**",
        f"- No over-attribution on E: **{d['E_ariadne_not_over_attributes']}**",
        "",
        "## Recovery-vs-risk frontier",
        "",
        "| System | Threshold | Money recovered | False-interv. cost | Do-nothing-correct |",
        "|--------|-----------|-----------------|--------------------|--------------------|",
    ]
    for system in ("ariadne", "baseline"):
        for p in sweep_result["frontier"][system]:
            lines.append(
                f"| {system} | {p['threshold']} | {p['money_recovered']:.0f} | "
                f"{p['false_intervention_cost']:.0f} | {p['do_nothing_correct_rate']:.2f} |"
            )
    lines.append("")
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
