"""The recovery-vs-risk frontier plot (BUILD_SPEC §3.15).

``plot_frontier`` draws the headline figure: x = false_intervention_cost,
y = money_recovered, one point per threshold, one series for ariadne and one for
baseline — "here is the recovery-vs-risk frontier; the merchant chooses."

matplotlib is an OPTIONAL extra used ONLY here. Its import is LOCAL to the
function and the ``Agg`` (headless) backend is selected before importing pyplot,
so the rest of the suite imports and runs without matplotlib installed. This is
the ONLY module in the package allowed to touch matplotlib.
"""


def plot_frontier(sweep_result: dict, out_path: str) -> None:
    """Scatter/line of the recovery-vs-false-intervention-cost frontier; save PNG.

    ``sweep_result`` is the dict returned by ``eval.run.run_sweep`` (it must carry
    a ``"frontier"`` mapping of system -> list of per-threshold points). The
    matplotlib import is deliberately local + guarded so importing this module
    never forces the dependency on the rest of the suite."""
    import matplotlib

    matplotlib.use("Agg")  # headless backend — no display required
    import matplotlib.pyplot as plt

    frontier = sweep_result.get("frontier", {})
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    markers = {"ariadne": "o", "baseline": "s"}
    for system, points in frontier.items():
        ordered = sorted(points, key=lambda p: p["threshold"])
        xs = [p["false_intervention_cost"] for p in ordered]
        ys = [p["money_recovered"] for p in ordered]
        ax.plot(
            xs,
            ys,
            marker=markers.get(system, "x"),
            linestyle="-",
            label=system,
        )
        for p in ordered:
            ax.annotate(
                f"thr={p['threshold']:.2f}",
                (p["false_intervention_cost"], p["money_recovered"]),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=8,
            )

    ax.set_xlabel("false intervention cost")
    ax.set_ylabel("money recovered")
    ax.set_title("Recovery vs risk frontier (one point per threshold)")
    ax.axhline(0.0, color="grey", linewidth=0.8, linestyle="--")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
