"""Every figure in the dashboard.

Each function takes a DataFrame, checks the columns it needs, and returns a
Plotly figure. None of them call ``st.*``: rendering, titles and captions are
the job of ``ui.figure``. Chart formatting lives here so that the house style
exists once.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src import formatting as fmt
from src.constants import (
    AMBER,
    BLUE,
    BLUE_DEEP,
    BLUE_LIGHT,
    FAINT,
    FONT_STACK,
    GREEN,
    GREY,
    INK,
    MUTED,
    RED,
    RULE,
)
from src.data_loader import DataError

STAY_BAND_LABELS = {
    1: "1 day",
    2: "2 days",
    3: "3 days",
    4: "4–5 days",
    6: "6–9 days",
    10: "10 or more days",
}


# --------------------------------------------------------------------------
# shared plumbing
# --------------------------------------------------------------------------


def _require(frame: pd.DataFrame, columns: Sequence[str], who: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise DataError(
            f"{who} needs column(s) {', '.join(missing)}, which are not in the "
            f"table it was given (found: {', '.join(map(str, frame.columns))})."
        )


def _blank(height: int = 300, showlegend: bool = False) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="none",
        height=height,
        margin=dict(l=0, r=8, t=6, b=4),
        font=dict(family=FONT_STACK, size=12, color=INK),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=showlegend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=12, color=MUTED),
            bgcolor="rgba(0,0,0,0)",
            traceorder="normal",
        ),
        barcornerradius=6,
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor=RULE,
            font=dict(family=FONT_STACK, size=12.5, color=INK),
            align="left",
        ),
        transition=dict(duration=350, easing="cubic-in-out"),
        dragmode=False,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=RULE,
        ticks="outside",
        ticklen=4,
        tickcolor=RULE,
        tickfont=dict(size=11.5, color=MUTED),
        title_font=dict(size=12, color=MUTED),
        automargin=True,
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        linecolor="rgba(0,0,0,0)",
        ticks="",
        tickfont=dict(size=12.5, color=INK),
        title_font=dict(size=12, color=MUTED),
        automargin=True,
    )
    return fig


def _value_grid(fig: go.Figure, axis: str = "x") -> go.Figure:
    update = dict(showgrid=True, gridcolor=RULE, gridwidth=1, griddash="dot")
    if axis == "x":
        fig.update_xaxes(**update)
    else:
        fig.update_yaxes(**update)
    return fig


def _marker_sizes(counts: Sequence[float], low: float = 7, high: float = 17):
    """Area-proportional marker sizes, so group size is visible on the chart."""
    values = np.asarray([0 if fmt.is_missing(c) else float(c) for c in counts],
                        dtype=float)
    roots = np.sqrt(np.clip(values, 0, None))
    if roots.max() <= 0 or np.isclose(roots.max(), roots.min()):
        return [(low + high) / 2] * len(values)
    scaled = low + (roots - roots.min()) / (roots.max() - roots.min()) * (high - low)
    return scaled.tolist()


_LABEL_POSITIONS = (
    "middle right", "middle left", "top center", "bottom center",
    "top right", "bottom right", "top left", "bottom left",
)


def _overlaps(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _label_positions(xs, ys, texts, x_range, y_range,
                     char_width: float = 0.0082, line_height: float = 0.052,
                     pad: float = 0.012):
    """Pick a text position per point so labels do not sit on top of each other.

    Works in axis-normalised space, tries the candidate positions in order and
    takes the first that collides with nothing already placed.
    """
    x_span = max(x_range[1] - x_range[0], 1e-9)
    y_span = max(y_range[1] - y_range[0], 1e-9)
    points = [((x - x_range[0]) / x_span, (y - y_range[0]) / y_span)
              for x, y in zip(xs, ys)]

    taken = [(px - 0.012, py - 0.022, px + 0.012, py + 0.022) for px, py in points]
    chosen = []
    for (px, py), text in zip(points, texts):
        width = len(str(text)) * char_width
        boxes = {
            "middle right": (px + pad, py - line_height / 2,
                             px + pad + width, py + line_height / 2),
            "middle left": (px - pad - width, py - line_height / 2,
                            px - pad, py + line_height / 2),
            "top center": (px - width / 2, py + pad,
                           px + width / 2, py + pad + line_height),
            "bottom center": (px - width / 2, py - pad - line_height,
                              px + width / 2, py - pad),
            "top right": (px + pad, py + pad,
                          px + pad + width, py + pad + line_height),
            "bottom right": (px + pad, py - pad - line_height,
                             px + pad + width, py - pad),
            "top left": (px - pad - width, py + pad,
                         px - pad, py + pad + line_height),
            "bottom left": (px - pad - width, py - pad - line_height,
                            px - pad, py - pad),
        }
        placed = None
        for position in _LABEL_POSITIONS:
            box = boxes[position]
            if box[0] < -0.02 or box[2] > 1.02 or box[1] < -0.02 or box[3] > 1.02:
                continue
            if any(_overlaps(box, other) for other in taken):
                continue
            placed = position
            taken.append(box)
            break
        if placed is None:
            placed = "middle right"
            taken.append(boxes[placed])
        chosen.append(placed)
    return chosen


def _row_height(rows: int, per_row: int = 26, pad: int = 62) -> int:
    return int(rows * per_row + pad)


def _annotate_right(fig: go.Figure, xs, ys, labels, shift: int = 12,
                    color: str = MUTED, size: float = 11.5) -> None:
    for x, y, label in zip(xs, ys, labels):
        if fmt.is_missing(x) or not label:
            continue
        fig.add_annotation(
            x=x, y=y, text=label, showarrow=False,
            xanchor="left", xshift=shift, align="left",
            font=dict(family=FONT_STACK, size=size, color=color),
        )


def _dot_with_intervals(
    frame: pd.DataFrame,
    label_col: str,
    value_col: str,
    *,
    ci_low: str | None = None,
    ci_high: str | None = None,
    size_col: str | None = None,
    label_suffix: str = "%",
    x_title: str = "",
    x_max: float | None = None,
    highlight: str | None = None,
    highlight_color: str = RED,
    base_color: str = BLUE,
    extra_label: Sequence[str] | None = None,
    hover: Sequence[str] | None = None,
) -> go.Figure:
    """Horizontal dot plot, largest value at the top, intervals drawn."""
    data = frame.copy()
    labels = data[label_col].astype(str).tolist()
    values = data[value_col].astype(float).tolist()

    colors = [
        highlight_color if (highlight and lab == highlight) else base_color
        for lab in labels
    ]
    sizes = _marker_sizes(data[size_col]) if size_col else [10] * len(values)

    fig = _blank(height=_row_height(len(values)))

    # A stem from zero to the value: length is readable without reading the axis.
    for value, label, colour in zip(values, labels, colors):
        fig.add_shape(
            type="line", x0=0, x1=value, y0=label, y1=label,
            line=dict(color=colour, width=4), opacity=0.16, layer="below",
        )

    if ci_low and ci_high:
        error = dict(
            type="data",
            symmetric=False,
            array=(data[ci_high].astype(float) - data[value_col].astype(float)).tolist(),
            arrayminus=(data[value_col].astype(float) - data[ci_low].astype(float)).tolist(),
            color="#8d8a84",
            thickness=1.1,
            width=4,  # end caps, so the interval reads as separate from the stem
        )
    else:
        error = None

    fig.add_trace(
        go.Scatter(
            x=values,
            y=labels,
            mode="markers",
            marker=dict(color=colors, size=sizes,
                        line=dict(color="white", width=1)),
            error_x=error,
            hovertext=hover,
            hovertemplate="%{y}<br>%{x:.1f}" + label_suffix +
                          ("<br>%{hovertext}" if hover is not None else "") +
                          "<extra></extra>",
        )
    )

    right_edge = data[ci_high].astype(float) if ci_high else data[value_col].astype(float)
    text = extra_label or [f"{v:.1f}{label_suffix}" for v in values]
    _annotate_right(fig, right_edge.tolist(), labels, text)

    upper = x_max if x_max is not None else float(right_edge.max()) * 1.30
    fig.update_xaxes(range=[0, upper], title=x_title, ticksuffix="")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


# --------------------------------------------------------------------------
# cohort
# --------------------------------------------------------------------------


def cohort_flow(frame: pd.DataFrame, steps: int | None = None) -> go.Figure:
    """Sequential cohort construction as proportional horizontal bars."""
    _require(frame, ["step", "n"], "cohort_flow")
    data = frame.copy()
    if steps:
        data = data.tail(steps)

    labels = data["step"].astype(str).tolist()
    values = data["n"].astype(float).tolist()

    fig = _blank(height=_row_height(len(values), per_row=30, pad=56))
    fig.add_trace(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=[BLUE_LIGHT] * (len(values) - 1) + [BLUE_DEEP]),
            width=0.62,
            hovertemplate="%{y}<br>%{x:,.0f} <extra></extra>",
        )
    )
    _annotate_right(fig, values, labels,
                    [f"{v:,.0f}" for v in values], shift=10, color=INK, size=12)
    fig.update_xaxes(range=[0, max(values) * 1.3], showticklabels=False,
                     showline=False, ticks="")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(margin=dict(r=0, t=6, b=0))
    return fig


# --------------------------------------------------------------------------
# readmission
# --------------------------------------------------------------------------


def readmission_by_site(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["cancer_site", "episodes", "percent", "ci_low", "ci_high"],
             "readmission_by_site")
    data = (
        frame.dropna(subset=["percent", "episodes"])
        .sort_values("percent", ascending=False)
        .reset_index(drop=True)
    )
    labels = [
        f"{p:.1f}%   n={int(n):,}"
        for p, n in zip(data["percent"], data["episodes"])
    ]
    return _dot_with_intervals(
        data, "cancer_site", "percent",
        ci_low="ci_low", ci_high="ci_high", size_col="episodes",
        x_title="Urgent/emergent readmission within 30 days (%)",
        extra_label=labels,
        hover=[f"{int(n):,} episodes, {int(r):,} readmitted"
               for n, r in zip(data["episodes"], data["readmitted"])]
        if "readmitted" in data.columns else None,
    )


def readmission_by_province(frame: pd.DataFrame, reference: float | None = None,
                            highlight: str | None = None) -> go.Figure:
    _require(frame, ["province", "episodes", "percent", "ci_low", "ci_high"],
             "readmission_by_province")
    data = (
        frame.dropna(subset=["percent", "episodes"])
        .sort_values("percent", ascending=False)
        .reset_index(drop=True)
    )
    labels = [
        f"{p:.1f}%   n={int(n):,}"
        for p, n in zip(data["percent"], data["episodes"])
    ]
    fig = _dot_with_intervals(
        data, "province", "percent",
        ci_low="ci_low", ci_high="ci_high", size_col="episodes",
        x_title="Urgent/emergent readmission within 30 days (%)",
        extra_label=labels, highlight=highlight,
    )
    if reference is not None:
        fig.add_vline(x=reference, line=dict(color=FAINT, width=1, dash="dot"))
        fig.add_annotation(
            x=reference, y=1.0, yref="paper", text=f"Cohort average {reference:.1f}%",
            showarrow=False, xanchor="left", xshift=6, yanchor="bottom", yshift=2,
            font=dict(family=FONT_STACK, size=11, color=MUTED),
        )
    return fig


def adjusted_risk_comparison(
    rows: Sequence[dict],
    *,
    x_title: str,
    x_max: float | None = None,
    colors: Sequence[str] = (RED, BLUE),
) -> go.Figure:
    """Two adjusted risks with intervals, drawn on one axis.

    rows: [{"label": str, "value": float, "ci": "21.5 to 23.0"}, ...]
    """
    labels = [r["label"] for r in rows]
    values = [float(r["value"]) for r in rows]
    lows, highs = [], []
    for row, value in zip(rows, values):
        bounds = fmt.parse_interval(row.get("ci"))
        lows.append(bounds[0] if bounds else value)
        highs.append(bounds[1] if bounds else value)

    fig = _blank(height=_row_height(len(rows), per_row=46, pad=72))
    fig.add_trace(
        go.Scatter(
            x=values,
            y=labels,
            mode="markers",
            marker=dict(color=list(colors)[: len(rows)], size=15,
                        line=dict(color="white", width=1.5)),
            error_x=dict(
                type="data", symmetric=False,
                array=[h - v for h, v in zip(highs, values)],
                arrayminus=[v - l for v, l in zip(values, lows)],
                color=GREY, thickness=1.4, width=6,
            ),
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    text = []
    for row, value in zip(rows, values):
        interval = fmt.interval(row.get("ci"), label="95% CI", suffix="%")
        text.append(f"{value:.1f}%" + (f"   {interval}" if interval else ""))
    _annotate_right(fig, highs, labels, text, shift=14, color=INK, size=12.5)

    upper = x_max or max(highs) * 1.75
    fig.update_xaxes(range=[0, upper], title=x_title)
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


def adjusted_readmission_comparison(frame: pd.DataFrame,
                                    model_prefix: str = "1.") -> go.Figure:
    _require(frame, ["adjusted_readmission_if_all_urgent_pct",
                     "adjusted_readmission_if_all_planned_pct", "model"],
             "adjusted_readmission_comparison")
    row = frame[frame["model"].astype(str).str.startswith(model_prefix)]
    if row.empty:
        raise DataError(
            f"No model beginning '{model_prefix}' in the adjusted-risk table."
        )
    row = row.iloc[0]
    return adjusted_risk_comparison(
        [
            {"label": "If every index episode<br>had been urgent/emergent",
             "value": row["adjusted_readmission_if_all_urgent_pct"],
             "ci": row.get("urgent_ci")},
            {"label": "If every index episode<br>had been planned",
             "value": row["adjusted_readmission_if_all_planned_pct"],
             "ci": row.get("planned_ci")},
        ],
        x_title="Adjusted 30-day urgent readmission risk (%)",
        x_max=34,
    )


def mortality_urgent_vs_planned(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["adjusted_risk_if_all_urgent_pct",
                     "adjusted_risk_if_all_planned_pct"],
             "mortality_urgent_vs_planned")
    row = frame.iloc[0]
    return adjusted_risk_comparison(
        [
            {"label": "If every episode had begun<br>as urgent/emergent",
             "value": row["adjusted_risk_if_all_urgent_pct"],
             "ci": row.get("urgent_ci")},
            {"label": "If every episode had begun<br>as planned",
             "value": row["adjusted_risk_if_all_planned_pct"],
             "ci": row.get("planned_ci")},
        ],
        x_title="Adjusted in-hospital mortality risk (%)",
        x_max=26,
    )


def definition_sensitivity(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["analysis", "urgent_readmit_pct"], "definition_sensitivity")
    data = frame.sort_values("urgent_readmit_pct", ascending=False).reset_index(drop=True)
    labels = [
        f"{v:.1f}%" + (f"   n={int(n):,}" if "episodes" in data.columns else "")
        for v, n in zip(data["urgent_readmit_pct"],
                        data.get("episodes", pd.Series([0] * len(data))))
    ]
    fig = _blank(height=_row_height(len(data), per_row=30, pad=62))
    fig.add_trace(
        go.Bar(
            x=data["urgent_readmit_pct"], y=data["analysis"], orientation="h",
            marker=dict(color=BLUE), width=0.6,
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    _annotate_right(fig, data["urgent_readmit_pct"].tolist(),
                    data["analysis"].tolist(), labels, color=INK)
    fig.update_xaxes(range=[0, 24], title="30-day readmission (%)")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


def certainty_breakdown(frame: pd.DataFrame) -> go.Figure:
    """One stacked bar: how much of the outcome can be proven on timing."""
    _require(frame, ["certainty", "episodes", "pct"], "certainty_breakdown")
    order = ["definite", "ambiguous", "definitely not", "no later urgent episode"]
    colors = {"definite": BLUE_DEEP, "ambiguous": AMBER,
              "definitely not": BLUE_LIGHT, "no later urgent episode": "#eef1f4"}
    labels = {
        "definite": "Definite",
        "ambiguous": "Ambiguous",
        "definitely not": "Definitely outside",
        "no later urgent episode": "No later urgent episode",
    }
    data = frame.set_index("certainty")

    fig = _blank(height=170, showlegend=True)
    for key in order:
        if key not in data.index:
            continue
        row = data.loc[key]
        fig.add_trace(
            go.Bar(
                x=[float(row["pct"])], y=[""], orientation="h",
                name=labels[key],
                marker=dict(color=colors[key],
                            line=dict(color="white", width=1)),
                width=0.42,
                text=[f"{float(row['pct']):.1f}%"],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(
                    size=11.5,
                    # White only where the fill is dark enough to carry it.
                    color="white" if key == "definite" else INK,
                ),
                hovertemplate=f"{labels[key]}<br>%{{x:.1f}}% "
                              f"({int(row['episodes']):,} episodes)<extra></extra>",
            )
        )
    fig.update_layout(barmode="stack", margin=dict(l=0, r=0, t=34, b=10))
    fig.update_xaxes(range=[0, 100], showticklabels=False, showline=False, ticks="")
    fig.update_yaxes(showticklabels=False)
    return fig


def odds_ratio_forest(frame: pd.DataFrame, model_prefix: str = "1.",
                      drop_intercept: bool = True, top: int | None = None) -> go.Figure:
    """Adjusted odds ratios on a log axis, reference line at 1."""
    _require(frame, ["model", "factor", "odds_ratio", "ci_low", "ci_high"],
             "odds_ratio_forest")
    data = frame[frame["model"].astype(str).str.startswith(model_prefix)].copy()
    if drop_intercept:
        data = data[data["factor"].astype(str) != "Intercept"]
    data = data.dropna(subset=["odds_ratio", "ci_low", "ci_high"])
    if data.empty:
        raise DataError(f"No coefficients for a model beginning '{model_prefix}'.")
    data["label"] = data["factor"].map(fmt.tidy_factor)
    data = data.sort_values("odds_ratio", ascending=False)
    if top:
        data = data.head(top)

    fig = _blank(height=_row_height(len(data), per_row=23, pad=78))
    fig.add_vline(x=1, line=dict(color=INK, width=1, dash="dot"))
    fig.add_trace(
        go.Scatter(
            x=data["odds_ratio"], y=data["label"], mode="markers",
            marker=dict(color=BLUE, size=8, line=dict(color="white", width=1)),
            error_x=dict(
                type="data", symmetric=False,
                array=(data["ci_high"] - data["odds_ratio"]).tolist(),
                arrayminus=(data["odds_ratio"] - data["ci_low"]).tolist(),
                color=GREY, thickness=1, width=0,
            ),
            hovertemplate="%{y}<br>OR %{x:.2f}<extra></extra>",
        )
    )
    low = max(0.2, float(data["ci_low"].min()) * 0.85)
    high = float(data["ci_high"].max()) * 1.15
    fig.update_xaxes(type="log", range=[math.log10(low), math.log10(high)],
                     title="Adjusted odds ratio (log scale)",
                     tickvals=[0.25, 0.5, 1, 2, 4, 8],
                     ticktext=["0.25", "0.5", "1", "2", "4", "8"])
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11.5))
    _value_grid(fig, "x")
    return fig


# --------------------------------------------------------------------------
# mortality and admission route
# --------------------------------------------------------------------------


def urgent_share_vs_mortality(frame: pd.DataFrame) -> go.Figure:
    """Ecological comparison across cancer-site groups."""
    _require(frame, ["cancer_site", "episodes", "pct_urgent", "pct_died"],
             "urgent_share_vs_mortality")
    data = frame.dropna(subset=["pct_urgent", "pct_died"]).copy()
    x_range = (0, 96)
    y_range = (0, max(16, float(data["pct_died"].max()) * 1.25))
    positions = _label_positions(
        data["pct_urgent"].tolist(), data["pct_died"].tolist(),
        data["cancer_site"].tolist(), x_range, y_range,
    )

    fig = _blank(height=360)
    fig.add_trace(
        go.Scatter(
            x=data["pct_urgent"], y=data["pct_died"],
            mode="markers+text",
            text=data["cancer_site"],
            textposition=positions,
            textfont=dict(size=11, color=MUTED),
            marker=dict(
                color=BLUE, opacity=0.75,
                size=_marker_sizes(data["episodes"], 9, 30),
                line=dict(color="white", width=1),
            ),
            customdata=data[["episodes"]].to_numpy(),
            hovertemplate="%{text}<br>Urgent %{x:.1f}%<br>Died %{y:.1f}%"
                          "<br>%{customdata[0]:,} episodes<extra></extra>",
        )
    )
    fig.update_xaxes(range=list(x_range), title="Urgent/emergent admission category (%)")
    fig.update_yaxes(range=list(y_range), title="Died during the episode (%)")
    _value_grid(fig, "y")
    fig.update_layout(margin=dict(l=0, r=8, t=10, b=8))
    return fig


# --------------------------------------------------------------------------
# post-admission conditions
# --------------------------------------------------------------------------


def post_admission_conditions(frame: pd.DataFrame, top: int = 12) -> go.Figure:
    _require(frame, ["code", "condition", "n_episodes", "pct_of_episodes"],
             "post_admission_conditions")
    data = (
        frame.sort_values("pct_of_episodes", ascending=False)
        .head(top)
        .reset_index(drop=True)
    )
    labels = [f"{c} · {n}" for c, n in zip(data["code"], data["condition"])]
    right = [
        f"{p:.1f}%   {int(n):,} episodes"
        for p, n in zip(data["pct_of_episodes"], data["n_episodes"])
    ]

    fig = _blank(height=_row_height(len(data), per_row=30, pad=80))
    fig.add_trace(
        go.Bar(
            x=data["pct_of_episodes"], y=labels, orientation="h",
            marker=dict(color=BLUE), width=0.6,
            customdata=data[["n_episodes", "n_occurrences"]].to_numpy()
            if "n_occurrences" in data.columns else None,
            hovertemplate="%{y}<br>%{x:.2f}% of episodes"
                          "<br>%{customdata[0]:,} episodes, "
                          "%{customdata[1]:,} coded occurrences<extra></extra>"
            if "n_occurrences" in data.columns
            else "%{y}<br>%{x:.2f}%<extra></extra>",
        )
    )
    _annotate_right(fig, data["pct_of_episodes"].tolist(), labels, right, color=INK)
    fig.update_xaxes(range=[0, float(data["pct_of_episodes"].max()) * 1.7],
                     title="Share of invasive-cancer episodes (%)")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12))
    _value_grid(fig, "x")
    return fig


def post_admission_outcomes(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["post_admission_condition", "pct_died",
                     "pct_intensive_care", "pct_long_stay"],
             "post_admission_outcomes")
    measures = [
        ("pct_died", "Died in hospital"),
        ("pct_intensive_care", "Special care unit stay"),
        ("pct_long_stay", "Episode of 6 days or longer"),
    ]
    data = frame.set_index("post_admission_condition")
    groups = [("None coded", GREY), ("At least one coded", RED)]

    fig = _blank(height=250, showlegend=True)
    for name, color in groups:
        if name not in data.index:
            continue
        row = data.loc[name]
        fig.add_trace(
            go.Bar(
                y=[label for _, label in measures],
                x=[float(row[col]) for col, _ in measures],
                orientation="h",
                name=f"{name} ({int(row['episodes']):,} episodes)"
                if "episodes" in data.columns else name,
                marker=dict(color=color), width=0.34,
                text=[f"{float(row[col]):.1f}%" for col, _ in measures],
                textposition="outside",
                textfont=dict(size=11.5, color=INK),
                cliponaxis=False,
                hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
            )
        )
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08,
                      margin=dict(l=0, r=10, t=36, b=8))
    fig.update_xaxes(range=[0, 100], title="Share of episodes (%)")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


def post_admission_by_group(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["group", "episodes", "pct_with_post_admission_condition"],
             "post_admission_by_group")
    data = frame.copy()
    right = [
        f"{p:.1f}%   n={int(n):,}"
        for p, n in zip(data["pct_with_post_admission_condition"], data["episodes"])
    ]
    fig = _blank(height=_row_height(len(data), per_row=30, pad=76))
    fig.add_trace(
        go.Bar(
            x=data["pct_with_post_admission_condition"], y=data["group"],
            orientation="h", marker=dict(color=BLUE), width=0.58,
            hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
        )
    )
    _annotate_right(fig, data["pct_with_post_admission_condition"].tolist(),
                    data["group"].tolist(), right, color=INK)
    fig.update_xaxes(range=[0, 60], title="Episodes with at least one such condition (%)")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


# --------------------------------------------------------------------------
# mortality trend
# --------------------------------------------------------------------------


def mortality_quarterly_trend(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["quarter", "pct_died"], "mortality_quarterly_trend")
    data = frame.sort_values("quarter").reset_index(drop=True)
    # Every quarter tied at the maximum is labelled. The peak is read from the
    # series rather than assumed to be a single quarter or a pair.
    peak_value = float(data["pct_died"].max())
    peak_rows = [
        int(i) for i in data.index[data["pct_died"] >= peak_value - 1e-9].tolist()
    ]

    fig = _blank(height=300)
    fig.add_trace(
        go.Scatter(
            x=data["quarter"], y=data["pct_died"],
            mode="lines+markers",
            line=dict(color=RED, width=2.6, shape="spline", smoothing=0.5),
            fill="tozeroy", fillcolor="rgba(156, 97, 70, 0.10)",
            marker=dict(color=RED, size=7, line=dict(color="white", width=1.5)),
            customdata=data[["episodes", "deaths"]].to_numpy()
            if {"episodes", "deaths"}.issubset(data.columns) else None,
            hovertemplate="Quarter %{x}<br>%{y:.1f}% died"
                          "<br>%{customdata[1]:,} of %{customdata[0]:,} episodes"
                          "<extra></extra>"
            if {"episodes", "deaths"}.issubset(data.columns)
            else "Quarter %{x}<br>%{y:.1f}%<extra></extra>",
        )
    )
    last_row = len(data) - 1
    marked = [(0, "left", 8)]
    marked += [(row, "center", 0) for row in peak_rows if row not in (0, last_row)]
    marked.append((last_row, "right", -8))
    for index, anchor, shift in marked:
        row = data.iloc[index]
        fig.add_annotation(
            x=row["quarter"], y=row["pct_died"],
            text=f"{row['pct_died']:.1f}%", showarrow=False,
            yshift=16, xshift=shift, xanchor=anchor,
            font=dict(family=FONT_STACK, size=12, color=INK),
        )
    fig.update_xaxes(tickmode="array", tickvals=data["quarter"].tolist(),
                     title="Quarter, anchored on discharge (1 = earliest)")
    fig.update_yaxes(range=[0, max(16, float(data["pct_died"].max()) * 1.28)],
                     title="Died in hospital (%)", ticksuffix="", dtick=4)
    _value_grid(fig, "y")
    return fig


def trend_case_mix(frame: pd.DataFrame, columns: Sequence[str]) -> go.Figure:
    """Mortality against the measured characteristics over the same quarters."""
    _require(frame, ["quarter", *columns], "trend_case_mix")
    data = frame.sort_values("quarter").reset_index(drop=True)
    pretty = {
        "pct_died": "Died in hospital",
        "pct_urgent": "Urgent/emergent admission",
        "pct_spread": "Secondary deposits coded",
        "pct_aged_80_plus": "Aged 80 or over",
        "pct_intensive_care": "Special care unit stay",
        "pct_palliative": "Palliative care coded",
        "pct_episode_long_stay": "Episode of 6 days or longer",
    }
    palette = {"pct_died": RED}
    others = [GREY, BLUE, AMBER, GREEN, BLUE_LIGHT, "#7f8c99"]

    fig = _blank(height=330)
    other_index = 0
    for column in columns:
        if column in palette:
            color, width, dash = palette[column], 2.4, "solid"
        else:
            color = others[other_index % len(others)]
            other_index += 1
            width, dash = 1.4, "dot"
        fig.add_trace(
            go.Scatter(
                x=data["quarter"], y=data[column], mode="lines+markers",
                name=pretty.get(column, column),
                line=dict(color=color, width=width, dash=dash),
                marker=dict(color=color, size=5),
                hovertemplate="Quarter %{x}<br>%{y:.1f}%<extra>"
                              f"{pretty.get(column, column)}</extra>",
            )
        )
        fig.add_annotation(
            x=float(data["quarter"].iloc[-1]), y=float(data[column].iloc[-1]),
            text=pretty.get(column, column), showarrow=False,
            xanchor="left", xshift=8,
            font=dict(family=FONT_STACK, size=11, color=color),
        )
    fig.update_xaxes(tickmode="array", tickvals=data["quarter"].tolist(),
                     range=[0.7, float(data["quarter"].max()) + 5.6],
                     title="Quarter, anchored on discharge")
    fig.update_yaxes(range=[0, 62], title="Percent of invasive-cancer episodes")
    _value_grid(fig, "y")
    return fig


def anchor_comparison(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["quarter", "discharge_anchored_pct", "admission_anchored_pct"],
             "anchor_comparison")
    data = frame.sort_values("quarter")
    fig = _blank(height=270, showlegend=True)
    for column, name, color, dash in (
        ("discharge_anchored_pct", "Anchored on discharge (primary)", RED, "solid"),
        ("admission_anchored_pct", "Anchored on the derived admission day", GREY, "dash"),
    ):
        fig.add_trace(
            go.Scatter(
                x=data["quarter"], y=data[column], mode="lines+markers",
                name=name, line=dict(color=color, width=2, dash=dash),
                marker=dict(color=color, size=6),
                hovertemplate="Quarter %{x}<br>%{y:.1f}%<extra>" + name + "</extra>",
            )
        )
    fig.update_xaxes(tickmode="array", tickvals=data["quarter"].tolist(),
                     title="Quarter")
    fig.update_yaxes(range=[0, 16], title="Died in hospital (%)")
    _value_grid(fig, "y")
    fig.update_layout(margin=dict(l=0, r=8, t=36, b=8))
    return fig


# --------------------------------------------------------------------------
# prediction model
# --------------------------------------------------------------------------


def calibration_plot(frame: pd.DataFrame) -> go.Figure:
    """Predicted against observed risk, with the ideal 45-degree line."""
    _require(frame, ["group", "episodes", "predicted_pct", "actual_pct"],
             "calibration_plot")
    data = frame.sort_values("group")
    upper = max(float(data["predicted_pct"].max()),
                float(data["actual_pct"].max())) * 1.2

    fig = _blank(height=380)
    fig.add_trace(
        go.Scatter(
            x=[0, upper], y=[0, upper], mode="lines",
            line=dict(color=GREY, width=1, dash="dash"),
            hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_annotation(
        x=upper * 0.82, y=upper * 0.88, text="Ideal calibration",
        showarrow=False, font=dict(family=FONT_STACK, size=11, color=FAINT),
        textangle=-45,
    )
    fig.add_trace(
        go.Scatter(
            x=data["predicted_pct"], y=data["actual_pct"],
            mode="markers+text",
            text=[str(int(g)) for g in data["group"]],
            textposition="top left",
            textfont=dict(size=10.5, color=MUTED),
            marker=dict(color=BLUE, size=11, line=dict(color="white", width=1)),
            customdata=data[["episodes"]].to_numpy(),
            hovertemplate="Risk tenth %{text}<br>Predicted %{x:.1f}%"
                          "<br>Observed %{y:.1f}%"
                          "<br>%{customdata[0]:,} episodes<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_xaxes(range=[0, upper], title="Mean predicted risk (%)")
    fig.update_yaxes(range=[0, upper], title="Observed readmission (%)")
    _value_grid(fig, "y")
    _value_grid(fig, "x")
    return fig


def calibration_by_decile(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["group", "predicted_pct", "actual_pct"], "calibration_by_decile")
    data = frame.sort_values("group")
    fig = _blank(height=280, showlegend=True)
    for column, name, color, dash in (
        ("predicted_pct", "Model predicted", GREY, "dash"),
        ("actual_pct", "Observed", BLUE, "solid"),
    ):
        fig.add_trace(
            go.Scatter(
                x=data["group"], y=data[column], mode="lines+markers", name=name,
                line=dict(color=color, width=2, dash=dash),
                marker=dict(color=color, size=6),
                hovertemplate="Risk tenth %{x}<br>%{y:.1f}%<extra>" + name + "</extra>",
            )
        )
    fig.update_xaxes(tickmode="array", tickvals=data["group"].tolist(),
                     title="Risk tenth (1 = lowest predicted risk)")
    fig.update_yaxes(range=[0, 38], title="Urgent 30-day readmission (%)")
    _value_grid(fig, "y")
    fig.update_layout(margin=dict(l=0, r=8, t=36, b=8))
    return fig


def threshold_operating_points(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["threshold", "flagged_pct", "sensitivity", "specificity", "ppv"],
             "threshold_operating_points")
    data = frame.sort_values("threshold")
    series = [
        ("sensitivity", "Sensitivity", BLUE),
        ("specificity", "Specificity", GREY),
        ("ppv", "Positive predictive value", RED),
    ]
    fig = _blank(height=300)
    for column, name, color in series:
        fig.add_trace(
            go.Scatter(
                x=data["threshold"], y=data[column] * 100, mode="lines+markers",
                name=name, line=dict(color=color, width=2),
                marker=dict(color=color, size=7),
                hovertemplate="Threshold %{x:.2f}<br>%{y:.1f}%<extra>"
                              + name + "</extra>",
            )
        )
        fig.add_annotation(
            x=float(data["threshold"].iloc[-1]), y=float(data[column].iloc[-1]) * 100,
            text=name, showarrow=False, xanchor="left", xshift=8,
            font=dict(family=FONT_STACK, size=11, color=color),
        )
    fig.update_xaxes(tickmode="array", tickvals=data["threshold"].tolist(),
                     range=[0.07, 0.45],
                     title="Probability threshold for flagging an episode")
    fig.update_yaxes(range=[0, 100], title="Percent")
    _value_grid(fig, "y")
    return fig


def feature_importance(frame: pd.DataFrame, top: int = 12) -> go.Figure:
    _require(frame, ["feature", "importance"], "feature_importance")
    data = frame.sort_values("importance", ascending=False).head(top)
    labels = [fmt.tidy_feature(f) for f in data["feature"]]
    fig = _blank(height=_row_height(len(data), per_row=24, pad=56))
    fig.add_trace(
        go.Bar(
            x=data["importance"], y=labels, orientation="h",
            marker=dict(color=BLUE_LIGHT), width=0.6,
            hovertemplate="%{y}<br>%{x:.3f}<extra></extra>",
        )
    )
    _annotate_right(fig, data["importance"].tolist(), labels,
                    [f"{v:.3f}" for v in data["importance"]])
    fig.update_xaxes(range=[0, float(data["importance"].max()) * 1.35],
                     title="Random forest feature importance")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11.5))
    _value_grid(fig, "x")
    return fig


# --------------------------------------------------------------------------
# robustness
# --------------------------------------------------------------------------


def transfer_rule_rate(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["transfer_rule", "kind", "primary_cohort_n", "urgent_readmit_pct"],
             "transfer_rule_rate")
    data = frame.copy()
    colors = [AMBER if str(k).lower().startswith("stress") else BLUE
              for k in data["kind"]]
    labels = [
        f"{v:.2f}%   n={int(n):,}" + ("   stress test" if str(k).lower().startswith("stress") else "")
        for v, n, k in zip(data["urgent_readmit_pct"], data["primary_cohort_n"],
                           data["kind"])
    ]
    fig = _blank(height=_row_height(len(data), per_row=28, pad=60))
    fig.add_trace(
        go.Scatter(
            x=data["urgent_readmit_pct"], y=data["transfer_rule"], mode="markers",
            marker=dict(color=colors, size=11, line=dict(color="white", width=1)),
            hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>",
        )
    )
    _annotate_right(fig, data["urgent_readmit_pct"].tolist(),
                    data["transfer_rule"].tolist(), labels, color=INK)
    fig.update_xaxes(range=[0, 24], title="Urgent 30-day readmission (%)")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12))
    _value_grid(fig, "x")
    return fig


def rule_robustness(frame: pd.DataFrame, column: str, *,
                    interval: tuple[float, float] | None = None,
                    primary: float | None = None,
                    x_title: str = "Adjusted risk ratio") -> go.Figure:
    """Each transfer rule's refitted estimate against the primary interval."""
    _require(frame, ["transfer_rule", column], "rule_robustness")
    data = frame.copy()

    fig = _blank(height=_row_height(len(data), per_row=30, pad=66))
    if interval:
        fig.add_vrect(x0=interval[0], x1=interval[1], fillcolor=BLUE,
                      opacity=0.09, line_width=0, layer="below")
    if primary is not None:
        fig.add_vline(x=primary, line=dict(color=BLUE_DEEP, width=1, dash="dot"))

    fig.add_trace(
        go.Scatter(
            x=data[column], y=data["transfer_rule"], mode="markers",
            marker=dict(color=INK, size=10, line=dict(color="white", width=1)),
            customdata=data[["cohort_n"]].to_numpy() if "cohort_n" in data else None,
            hovertemplate="%{y}<br>%{x:.2f}"
                          + ("<br>%{customdata[0]:,} episodes" if "cohort_n" in data else "")
                          + "<extra></extra>",
        )
    )
    _annotate_right(fig, data[column].tolist(), data["transfer_rule"].tolist(),
                    [f"{v:.2f}" for v in data[column]], color=INK, size=12)

    lower_bound = min([float(data[column].min())] + ([interval[0]] if interval else []))
    upper_bound = max([float(data[column].max())] + ([interval[1]] if interval else []))
    span = max(upper_bound - lower_bound, 0.4)
    fig.update_xaxes(range=[lower_bound - span * 0.25, upper_bound + span * 0.55],
                     title=x_title)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12))
    _value_grid(fig, "x")
    return fig


def merge_diagnostic(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["receiving_stay_band", "abstracts_after_a_transfer",
                     "merged", "pct_merged"], "merge_diagnostic")
    data = frame.copy()
    labels = [STAY_BAND_LABELS.get(int(b), str(b)) for b in data["receiving_stay_band"]]

    fig = _blank(height=290)
    fig.add_trace(
        go.Bar(
            x=labels, y=data["pct_merged"], marker=dict(color=BLUE), width=0.6,
            text=[f"{v:.1f}%" for v in data["pct_merged"]],
            textposition="outside", cliponaxis=False,
            textfont=dict(size=11.5, color=INK),
            customdata=data[["abstracts_after_a_transfer", "merged"]].to_numpy(),
            hovertemplate="%{x}<br>%{y:.1f}% merged"
                          "<br>%{customdata[1]:,.0f} of %{customdata[0]:,} abstracts"
                          "<extra></extra>",
        )
    )
    fig.update_xaxes(title="Length of the receiving stay")
    fig.update_yaxes(range=[0, 70], title="Merged into the earlier episode (%)")
    _value_grid(fig, "y")
    return fig


def contamination(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["urgent_admission", "episodes", "possible_continuation", "pct"],
             "contamination")
    data = frame.copy()
    data["label"] = np.where(
        data["urgent_admission"].astype(str).str.lower().isin(["true", "1"]),
        "Urgent/emergent index episodes", "Planned index episodes",
    )
    fig = _blank(height=180)
    fig.add_trace(
        go.Bar(
            x=data["pct"], y=data["label"], orientation="h",
            marker=dict(color=[RED, GREY]), width=0.45,
            customdata=data[["possible_continuation", "episodes"]].to_numpy(),
            hovertemplate="%{y}<br>%{x:.1f}%"
                          "<br>%{customdata[0]:,.0f} of %{customdata[1]:,} episodes"
                          "<extra></extra>",
        )
    )
    _annotate_right(
        fig, data["pct"].tolist(), data["label"].tolist(),
        [f"{p:.1f}%   {int(c):,} of {int(n):,}"
         for p, c, n in zip(data["pct"], data["possible_continuation"], data["episodes"])],
        color=INK,
    )
    fig.update_xaxes(range=[0, 9], title="Possibly an unmerged transfer continuation (%)")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


def los_assumption_strip(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["stay_length_assumption", "urgent_readmit_pct"],
             "los_assumption_strip")
    data = frame.copy()
    fig = _blank(height=_row_height(len(data), per_row=28, pad=62))
    fig.add_trace(
        go.Scatter(
            x=data["urgent_readmit_pct"], y=data["stay_length_assumption"],
            mode="markers",
            marker=dict(color=BLUE, size=11, line=dict(color="white", width=1)),
            hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>",
        )
    )
    _annotate_right(fig, data["urgent_readmit_pct"].tolist(),
                    data["stay_length_assumption"].tolist(),
                    [f"{v:.2f}%" for v in data["urgent_readmit_pct"]], color=INK)
    fig.update_xaxes(range=[15.0, 16.4],
                     title="Urgent 30-day readmission (%) — axis spans 1.4 points")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig


def cohort_definition(frame: pd.DataFrame) -> go.Figure:
    _require(frame, ["cohort_definition", "episodes", "any_return_pct",
                     "urgent_pct", "ed_entry_pct"], "cohort_definition")
    measures = [
        ("any_return_pct", "Any 30-day return"),
        ("urgent_pct", "Urgent/emergent readmission"),
        ("ed_entry_pct", "Readmission entering via ED"),
    ]
    colors = [GREY, BLUE]
    fig = _blank(height=300, showlegend=True)
    for (_, row), color in zip(frame.iterrows(), colors):
        fig.add_trace(
            go.Bar(
                y=[label for _, label in measures],
                x=[float(row[col]) for col, _ in measures],
                orientation="h", marker=dict(color=color), width=0.34,
                name=f"{row['cohort_definition']} ({int(row['episodes']):,})",
                text=[f"{float(row[col]):.1f}%" for col, _ in measures],
                textposition="outside", cliponaxis=False,
                textfont=dict(size=11.5, color=INK),
                hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>",
            )
        )
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08,
                      margin=dict(l=0, r=10, t=36, b=8))
    fig.update_xaxes(range=[0, 26], title="Share of episodes (%)")
    fig.update_yaxes(autorange="reversed")
    _value_grid(fig, "x")
    return fig
