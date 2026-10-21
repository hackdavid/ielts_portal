"""Deterministic charts (matplotlib): exact values the answer key depends on."""

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLOURS = ["#1d4ed8", "#f97316", "#059669", "#a855f7", "#dc2626", "#0891b2"]


def render(chart):
    """ChartSpec (dict or model) → (png bytes, width, height)."""
    c = chart if isinstance(chart, dict) else chart.model_dump()
    fig, ax = plt.subplots(figsize=(8, 5), dpi=110)
    cats, series, unit = c["categories"], c["series"], c.get("unit") or ""
    kind = c["chart_type"]
    if kind == "pie":
        values = series[0]["values"]
        ax.pie(
            values,
            labels=cats,
            colors=COLOURS[: len(values)],
            autopct=lambda p: f"{p:.0f}%",
            startangle=90,
            wedgeprops={"edgecolor": "white"},
        )
        ax.axis("equal")
    elif kind == "table":
        ax.axis("off")
        rows = [
            [cat] + [f"{s['values'][i]:g}{unit}" for s in series]
            for i, cat in enumerate(cats)
        ]
        table = ax.table(
            cellText=rows,
            colLabels=[c.get("x_label") or ""] + [s["name"] for s in series],
            loc="center",
            cellLoc="center",
        )
        table.scale(1, 1.6)
        table.set_fontsize(11)
    elif kind == "line":
        for i, s in enumerate(series):
            ax.plot(cats, s["values"], marker="o", color=COLOURS[i % 6], label=s["name"])
    else:
        n = max(len(series), 1)
        width = 0.8 / n
        for i, s in enumerate(series):
            xs = [x + (i - (n - 1) / 2) * width for x in range(len(cats))]
            ax.bar(xs, s["values"], width, color=COLOURS[i % 6], label=s["name"])
        ax.set_xticks(range(len(cats)), cats)
    if kind in ("bar", "line"):
        ax.set_xlabel(c.get("x_label") or "")
        y_label = c.get("y_label") or ""
        ax.set_ylabel(f"{y_label} ({unit})" if unit and y_label else y_label or unit)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        if len(series) > 1:
            ax.legend(frameon=False)
    ax.set_title(c["title"], fontsize=13, fontweight="bold")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    width, height = fig.canvas.get_width_height()
    plt.close(fig)
    return buf.getvalue(), width, height
