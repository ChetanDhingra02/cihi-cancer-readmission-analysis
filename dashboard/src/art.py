"""Page motifs: a small animated scene at the top of each page.

Each one restates the idea of its page as a picture (a return trip, two routes,
a timeline, twelve quarters, a scan, a band of estimates, layers of data). They
are decorative. Nothing here is drawn from the data, and no motif carries a
number the page does not already state in words.

Motion is CSS (keyframes generated below, plus the shared rules under
"page motifs" in assets/styles.css), so it stops under prefers-reduced-motion.
"""

from __future__ import annotations

import math
import random

WIDTH, HEIGHT = 340, 190

TEAL, TEAL_LIGHT = "#16a394", "#4fd1c0"
BLUE, BLUE_LIGHT = "#4c7bf4", "#8fb0ff"
CORAL, CORAL_LIGHT = "#f0674a", "#ff8f76"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _bezier(p0, p1, p2, p3, steps: int = 32, ease: bool = False):
    """Points along a cubic curve; ``ease`` slows both ends (smoothstep)."""
    points = []
    for index in range(steps + 1):
        u = index / steps
        if ease:
            u = u * u * (3 - 2 * u)
        v = 1 - u
        x = v**3 * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u**3 * p3[0]
        y = v**3 * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u**3 * p3[1]
        points.append((x, y))
    return points


def _travel(name: str, points, start: float, end: float, fade_in: float,
            hold_to: float, gone_by: float) -> str:
    """Keyframes that carry an element along ``points`` (all times are % of the
    cycle): visible from start+fade_in to hold_to, gone by ``gone_by``."""
    frames: dict[float, dict[str, str]] = {}

    def put(pct: float, **props: str) -> None:
        frames.setdefault(round(pct, 2), {}).update(props)

    def move(point) -> str:
        return f"translate({point[0]:.1f}px,{point[1]:.1f}px)"

    last = len(points) - 1
    put(0, transform=move(points[0]), opacity="0")
    for index, point in enumerate(points):
        put(start + (end - start) * index / last, transform=move(point))
    put(start, opacity="0")
    put(start + fade_in, opacity="1")
    put(hold_to, opacity="1")
    put(gone_by, opacity="0")
    put(100, transform=move(points[-1]), opacity="0")
    body = "".join(
        f"{pct:g}%{{" + ";".join(f"{key}:{value}" for key, value in props.items()) + "}"
        for pct, props in sorted(frames.items())
    )
    return f"@keyframes {name}{{{body}}}"


def _text(x: float, y: float, label: str, anchor: str = "middle") -> str:
    return f'<text class="mt" x="{x}" y="{y}" text-anchor="{anchor}">{label}</text>'


# --------------------------------------------------------------------------
# motifs: each returns (svg contents, extra css)
# --------------------------------------------------------------------------
def _readmission():
    """Home, a dotted 30-day arc, and a return to hospital."""
    home, hosp = (74, 126), (266, 126)
    c1, c2 = (106, 22), (234, 22)
    css = _travel("mv-return", _bezier(home, c1, c2, hosp, 34, ease=True),
                  start=8, end=72, fade_in=2, hold_to=72, gone_by=82)
    svg = (
        f'<path class="m-trail" d="M{home[0]},{home[1]} C{c1[0]},{c1[1]} '
        f'{c2[0]},{c2[1]} {hosp[0]},{hosp[1]}"/>'
        + _text(170, 44, "WITHIN 30 DAYS")
        + f'<g transform="translate({home[0]},{home[1]})">'
        '<circle class="m-node m-node--teal" r="16"/>'
        '<path class="m-glyph m-glyph--teal" d="M-6.5,1 L0,-6 L6.5,1 M-4.5,0 V6.5 H4.5 V0"/></g>'
        + f'<g transform="translate({hosp[0]},{hosp[1]})">'
        '<circle class="m-ripple" r="16"/>'
        '<circle class="m-node m-node--coral" r="16"/>'
        '<path class="m-glyph m-glyph--coral" d="M0,-6.5 V6.5 M-6.5,0 H6.5"/></g>'
        + _text(home[0], 158, "HOME")
        + _text(hosp[0], 158, "EMERGENCY")
        + '<g style="animation:mv-return 6s linear infinite">'
        f'<circle r="10" fill="{CORAL}" opacity=".22"/><circle r="4.2" fill="{CORAL_LIGHT}"/></g>'
    )
    return svg, css


def _mortality():
    """One arrival, two routes."""
    start, up_end, down_end = (58, 95), (282, 46), (282, 144)
    up = _bezier(start, (150, 95), (170, 46), up_end, 30)
    down = _bezier(start, (150, 95), (170, 144), down_end, 30)
    css = (
        _travel("mv-up", up, 0, 100, 7, 93, 100)
        + _travel("mv-down", down, 0, 100, 7, 93, 100)
    )

    def movers(name: str, colour: str, halo: str) -> str:
        return "".join(
            f'<g style="animation:{name} 6s linear infinite;animation-delay:{delay}s">'
            f'<circle r="8" fill="{halo}" opacity=".2"/><circle r="3.6" fill="{colour}"/></g>'
            for delay in (0, -2, -4)
        )

    svg = (
        f'<path class="m-line m-line--blue" d="M{start[0]},{start[1]} C150,95 170,46 {up_end[0]},{up_end[1]}"/>'
        f'<path class="m-line m-line--coral" d="M{start[0]},{start[1]} C150,95 170,144 {down_end[0]},{down_end[1]}"/>'
        f'<circle cx="{start[0]}" cy="{start[1]}" r="11" fill="#fff" opacity=".1"/>'
        f'<circle cx="{start[0]}" cy="{start[1]}" r="5" fill="#fff" opacity=".92"/>'
        f'<circle class="m-end m-end--blue" cx="{up_end[0]}" cy="{up_end[1]}" r="7"/>'
        f'<circle class="m-end m-end--coral" cx="{down_end[0]}" cy="{down_end[1]}" r="7"/>'
        + movers("mv-up", BLUE_LIGHT, BLUE)
        + movers("mv-down", CORAL_LIGHT, CORAL)
        + _text(start[0], 120, "ARRIVAL")
        + _text(up_end[0], 29, "PLANNED")
        + _text(down_end[0], 168, "EMERGENCY")
    )
    return svg, css


def _post_admission():
    """A timeline: what was there on arrival, and what started afterwards."""
    y, x0, x1, mark = 100, 26, 314, 112
    already = (40, 58, 76, 94)
    after = (138, 170, 199, 236, 268, 294)
    dots = "".join(f'<circle class="pa-old" cx="{x}" cy="{y}" r="4.5"/>' for x in already)
    # the scan crosses the line between 4% and 70% of an 8-second cycle
    dots += "".join(
        f'<circle class="pa-new" style="--t:{8 * (0.04 + 0.66 * (x - x0) / (x1 - x0)):.2f}s" '
        f'cx="{x}" cy="{y}" r="5"/>'
        for x in after
    )
    svg = (
        f'<line class="m-base" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>'
        f'<line class="m-dash" x1="{mark}" y1="58" x2="{mark}" y2="146"/>'
        + _text(mark, 46, "ADMITTED")
        + dots
        + f'<rect class="pa-scan" x="{x0}" y="64" width="2" height="72" rx="1"/>'
        + _text(62, 138, "ON ARRIVAL")
        + _text(213, 138, "STARTED AFTER")
    )
    css = ".pa-scan{--dx:%dpx}" % (x1 - x0)
    return svg, css


def _trend():
    """Twelve quarters, lighting up in order."""
    cx, cy, radius = 170, 94, 60
    segments = []
    for k in range(12):
        a0 = math.radians(k * 30 - 90 + 4)
        a1 = math.radians(k * 30 - 90 + 26)
        segments.append(
            f'<path class="seg" style="--k:{k}" d="M{cx + radius * math.cos(a0):.1f},'
            f'{cy + radius * math.sin(a0):.1f} A{radius},{radius} 0 0 1 '
            f'{cx + radius * math.cos(a1):.1f},{cy + radius * math.sin(a1):.1f}"/>'
        )
    svg = (
        f'<circle cx="{cx}" cy="{cy}" r="{radius - 16}" class="m-inner"/>'
        + "".join(segments)
        + f'<text class="m-num" x="{cx}" y="{cy + 8}" text-anchor="middle">12</text>'
        + _text(cx, cy + 25, "QUARTERS")
    )
    return svg, ""


def _prediction():
    """A hundred stays; a scan flags some of them."""
    rng = random.Random(11)
    flagged = set(rng.sample(range(100), 17))
    spacing = 13
    gx, gy = 170 - 4.5 * spacing, 94 - 4.5 * spacing
    dots = []
    for index in range(100):
        row, col = divmod(index, 10)
        x, y = gx + col * spacing, gy + row * spacing
        if index in flagged:
            delay = 7 * (0.03 + 0.63 * col / 9)
            dots.append(f'<circle class="fl" style="--t:{delay:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="2.6"/>')
        else:
            dots.append(f'<circle class="dt" cx="{x:.1f}" cy="{y:.1f}" r="2.6"/>')
    travel = 9 * spacing + 14
    svg = (
        "".join(dots)
        + f'<rect class="scan" x="{gx - 8:.1f}" y="{gy - 10:.1f}" width="2" height="{9 * spacing + 20}" rx="1"/>'
    )
    return svg, f".scan{{--dx:{travel}px}}"


def _robustness():
    """A band of plausible values; estimates drift, some out of it."""
    rows = (38, 70, 102, 134, 166)
    spec = (  # x, drift, colour, halo
        (166, 4, BLUE_LIGHT, BLUE),
        (173, 6, BLUE_LIGHT, BLUE),
        (170, 5, BLUE_LIGHT, BLUE),
        (192, 30, CORAL_LIGHT, CORAL),
        (150, 34, CORAL_LIGHT, CORAL),
    )
    guides = "".join(f'<line class="m-guide" x1="46" y1="{y}" x2="294" y2="{y}"/>' for y in rows)
    dots = "".join(
        f'<g class="drift" style="--a:{amp}px;animation-delay:-{i * 1.3:.1f}s">'
        f'<circle cx="{x}" cy="{y}" r="9" fill="{halo}" opacity=".2"/>'
        f'<circle cx="{x}" cy="{y}" r="4" fill="{colour}"/></g>'
        for i, (y, (x, amp, colour, halo)) in enumerate(zip(rows, spec))
    )
    svg = (
        '<rect class="m-band" x="130" y="18" width="80" height="154" rx="8"/>'
        + guides
        + '<line class="m-dash" x1="170" y1="18" x2="170" y2="172"/>'
        + dots
    )
    return svg, ""


def _methods():
    """Layers of data, held still and locked."""
    def plate(top: float, cls: str) -> str:
        return (
            f'<g class="plate {cls}"><path class="m-plate" d="M170,{top} L242,{top + 22} L170,{top + 44} '
            f'L98,{top + 22} Z"/></g>'
        )

    svg = (
        '<ellipse class="m-shadow" cx="170" cy="164" rx="66" ry="9"/>'
        + plate(96, "plate--3")
        + plate(70, "plate--2")
        + plate(44, "plate--1")
        # positioned by the outer group, floated by the inner one, so the CSS
        # animation never has to fight a transform attribute
        + '<g transform="translate(170,66)"><g class="plate plate--1">'
        '<rect class="m-lock" x="-6" y="-1" width="12" height="9" rx="2"/>'
        '<path class="m-lock-arc" d="M-3.5,-1 V-4 a3.5,3.5 0 0 1 7,0 V-1"/></g></g>'
    )
    return svg, ""


_MOTIFS = {
    "readmission": _readmission,
    "mortality": _mortality,
    "post_admission_conditions": _post_admission,
    "mortality_trends": _trend,
    "prediction_model": _prediction,
    "robustness": _robustness,
    "methods_and_data": _methods,
}


def motif(page: str | None) -> str:
    """The tile for a page (by its url path), or '' where there is none."""
    builder = _MOTIFS.get((page or "").strip("/").lower())
    if builder is None:
        return ""
    svg, css = builder()
    style = f"<style>{css}</style>" if css else ""
    return (
        '<div class="phead__art" aria-hidden="true">'
        + style
        + f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
        'fill="none" xmlns="http://www.w3.org/2000/svg">'
        + svg
        + "</svg></div>"
    )
