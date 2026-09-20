"""Presentation components: navigation, hero, answer card, KPI grid, finding
cards, chart cards, callouts and the small pictures that sit inside them.

This module decides how the dashboard looks. It reads nothing, computes no
statistic and formats no result: pages pass in values that came from
``metrics`` and ``data_loader``, and this module arranges them. The only
arithmetic here is geometry (turning a value into a bar length or an arc), and
every picture prints the exact figure beside it.

Two conventions are worth knowing before editing it:

* Card styling hangs off ``st.container(key=...)``, which Streamlit renders as
  a ``st-key-<key>`` class, so the stylesheet targets classes this app creates
  rather than internal test ids.
* Grids of cards (KPIs, findings) are emitted as a single block of HTML laid
  out by CSS grid. Building them from ``st.columns`` lets each card size itself
  against Streamlit's auto-height wrappers, which is what made cards overlap
  and rows end up ragged. HTML strings are collapsed to one line so the
  Markdown parser never treats them as code.
"""

from __future__ import annotations

import html
import itertools
import math
import re
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import art, licensing
from src.constants import APP_SHORT_TITLE, PLOTLY_CONFIG
from src.data_loader import DataError

STYLESHEET = Path(__file__).resolve().parents[1] / "assets" / "styles.css"
MOTION_SCRIPT = Path(__file__).resolve().parents[1] / "assets" / "motion.js"

_card_counter = itertools.count()
_uid_counter = itertools.count()


# --------------------------------------------------------------------------
# icons - small inline glyphs, drawn rather than pulled from an icon font.
# Paths adapted from the Lucide set (ISC licence).
# --------------------------------------------------------------------------

_ICONS = {
    "records": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
               '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "episodes": '<path d="m12.8 2.2a2 2 0 0 0-1.6 0L2.6 6.1a1 1 0 0 0 0 1.8l8.6 3.9a2 2 0 0 0 1.6 0l8.6-3.9a1 1 0 0 0 0-1.8Z"/>'
                '<path d="m22 17.6-9.2 4.2a2 2 0 0 1-1.6 0L2 17.6"/>'
                '<path d="m22 12.6-9.2 4.2a2 2 0 0 1-1.6 0L2 12.6"/>',
    "cohort": '<circle cx="9" cy="9" r="5"/><circle cx="16" cy="15" r="5"/>',
    "people": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
              '<path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "rate": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "risk": '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>'
            '<path d="M3.2 12h6.3l.5-1 2 4.5 2-7 1.5 3.5h5.3"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "scale": '<path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/><path d="M7 21h10"/>'
             '<path d="m16 16 3-8 3 8c-.9.65-1.9 1-3 1s-2.1-.35-3-1Z"/>'
             '<path d="m2 16 3-8 3 8c-.9.65-1.9 1-3 1s-2.1-.35-3-1Z"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "spread": '<circle cx="7" cy="16" r="2"/><circle cx="12" cy="9" r="2"/><circle cx="18" cy="14" r="2"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.7 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "trend": '<path d="M22 7 13.5 15.5 8.5 10.5 2 17"/><path d="M16 7h6v6"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "alert": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "bulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
            '<path d="M9 18h6"/><path d="M10 22h4"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>',
}

# Which glyph a card gets when a page does not name one. Presentation only:
# the label text decides the picture, never the value.
_ICON_HINTS = (
    ("readmission", "rate"), ("readmit", "rate"), ("came back", "rate"),
    ("died", "risk"), ("mortality", "risk"), ("death", "risk"), ("dying", "risk"),
    ("abstract", "records"), ("episode", "episodes"), ("stays studied", "episodes"),
    ("cohort", "cohort"), ("patient", "people"), ("people", "people"),
    ("population", "people"),
    ("auc", "target"), ("roc", "target"), ("pr-auc", "target"),
    ("calibration", "check"), ("brier", "scale"), ("threshold", "scale"),
    ("quarter", "clock"), ("three months", "clock"), ("highest", "trend"),
    ("spread", "spread"), ("moved", "spread"), ("condition", "shield"),
    ("provable", "check"), ("forest", "spread"), ("test", "target"),
    ("risk", "risk"), ("flagged", "flag"), ("caught", "target"),
    ("tables", "database"), ("sample", "database"), ("records", "records"),
    ("years", "clock"), ("rule", "scale"),
)


def _infer_icon(label: str) -> str:
    lowered = label.lower()
    for needle, name in _ICON_HINTS:
        if needle in lowered:
            return name
    return "records"


def _svg(name: str) -> str:
    path = _ICONS.get(name)
    if not path:
        return ""
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{path}</svg>'
    )


def _icon_badge(name: str) -> str:
    svg = _svg(name)
    return f'<span class="kpi__icon">{svg}</span>' if svg else ""


def _uid(prefix: str) -> str:
    return f"{prefix}{next(_uid_counter)}"


def _one_line(markup: str) -> str:
    """Collapse whitespace between tags so Markdown never sees a code block."""
    return re.sub(r">\s+<", "><", " ".join(markup.split()))


def _md(markup: str) -> None:
    st.markdown(_one_line(markup), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# page scaffolding and navigation
# --------------------------------------------------------------------------

# Short labels for the navigation bar, keyed by the page titles set in app.py.
# A title with no entry here simply uses itself.
_NAV_LABELS = {
    "Overview": "Overview",
    "30-day readmission": "Readmission",
    "Urgent admission and mortality": "Mortality",
    "Post-admission conditions": "Post-admission",
    "Mortality over time": "Trend",
    "Prediction model": "Prediction",
    "Robustness and uncertainty": "Robustness",
    "Methods, data and licensing": "Data & methods",
}

_BRAND_MARK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M3 12h4l2.5-6 5 12L17 12h4"/></svg>'
)


def _run_script(source: str) -> None:
    """Run a script in the page itself.

    Current Streamlit does this directly through ``st.html``. Older releases
    lack that option, so a zero-height component injects the same script into
    the parent page instead. Either way the script guards against running twice
    and the page is fully usable if it does not run at all.
    """
    try:
        st.html(f"<script>{source}</script>", unsafe_allow_javascript=True)
    except TypeError:
        import json

        from streamlit.components.v1 import html as component_html

        component_html(
            "<script>(function(){var p=window.parent;if(!p||p.__cihiMotion)return;"
            "var s=p.document.createElement('script');s.textContent="
            + json.dumps(source)
            + ";p.document.head.appendChild(s);})();</script>",
            height=0,
        )


def configure() -> None:
    """Page config, stylesheet and motion script. Called once from the entrypoint."""
    st.set_page_config(
        page_title=APP_SHORT_TITLE,
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(f"<style>{STYLESHEET.read_text()}</style>", unsafe_allow_html=True)
    _run_script(MOTION_SCRIPT.read_text())


def top_nav(sections: dict, current) -> None:
    """A floating navigation bar, with the active page marked by this app."""
    pages = [page for group in sections.values() for page in group]
    st.session_state["_nav"] = {
        "pages": pages,
        "current": getattr(current, "url_path", None),
    }
    with st.container(key="topnav"):
        _md(
            '<div class="brand"><span class="brand__mark">' + _BRAND_MARK + "</span>"
            '<span><div class="brand__name">Cancer episodes</div>'
            '<div class="brand__sub">CIHI DAD study</div></span></div>'
        )
        for page in pages:
            active = page.url_path == getattr(current, "url_path", None)
            slug = (page.url_path or "home").replace("/", "-")
            key = f"nav-active-{slug}" if active else f"nav-{slug}"
            with st.container(key=key):
                st.page_link(page, label=_NAV_LABELS.get(page.title, page.title))


def page_href(title: str) -> str:
    """Relative link to a page, by its navigation title ('' if unknown)."""
    nav = st.session_state.get("_nav")
    if not nav:
        return ""
    for page in nav["pages"]:
        if page.title == title:
            return page.url_path or "."
    return ""


def next_up() -> None:
    """A large link to the next page in the reading order."""
    nav = st.session_state.get("_nav")
    if not nav:
        return
    pages, current = nav["pages"], nav["current"]
    position = next(
        (i for i, page in enumerate(pages) if page.url_path == current), None
    )
    if position is None or position + 1 >= len(pages):
        return
    following = pages[position + 1]
    with st.container(key="nextup"):
        st.page_link(following, label=following.title)


def run_page(render: Callable[[], None]) -> None:
    """Run a page body, turning a data problem into a clear message.

    A missing or malformed published table stops the page with the reason
    rather than letting a partially drawn page imply that everything is fine.
    """
    global _card_counter
    _card_counter = itertools.count()  # deterministic card keys within a page
    try:
        render()
    except DataError as exc:
        st.error(f"**This page cannot be shown.**\n\n{exc}")
        st.stop()
    next_up()
    footer()


def card():
    """A surface for charts, tables or prose. Styled via its container key."""
    return st.container(key=f"uicard-{next(_card_counter)}")


# --------------------------------------------------------------------------
# hero and headings
# --------------------------------------------------------------------------


def _hero_art() -> str:
    """Orbit motif: a 30-day window, drawn as thirty ticks around a ring, with
    things coming back around it. Decorative; carries no data."""
    cx = cy = 180
    ticks = []
    for step in range(30):
        angle = math.radians(step * 12 - 90)
        inner = 150
        outer = 158 if step % 5 else 166
        ticks.append(
            f'<line x1="{cx + inner * math.cos(angle):.1f}" y1="{cy + inner * math.sin(angle):.1f}" '
            f'x2="{cx + outer * math.cos(angle):.1f}" y2="{cy + outer * math.sin(angle):.1f}" '
            'stroke="rgba(255,255,255,.35)" stroke-width="1.4" stroke-linecap="round"/>'
        )
    return (
        '<div class="hero__art" aria-hidden="true">'
        '<svg viewBox="0 0 360 360" fill="none" xmlns="http://www.w3.org/2000/svg">'
        + "".join(ticks)
        + '<circle cx="180" cy="180" r="128" stroke="rgba(255,255,255,.14)" stroke-dasharray="2 7"/>'
        '<circle cx="180" cy="180" r="92" stroke="rgba(255,255,255,.10)"/>'
        '<g class="orbit" style="transform-box:view-box;transform-origin:180px 180px">'
        '<circle cx="308" cy="180" r="7" fill="#16a394"/>'
        '<circle cx="308" cy="180" r="15" fill="#16a394" opacity=".22"/>'
        '<circle cx="90" cy="270" r="3.5" fill="#fff" opacity=".8"/></g>'
        '<g class="orbit orbit--2" style="transform-box:view-box;transform-origin:180px 180px">'
        '<circle cx="180" cy="52" r="7" fill="#f0674a"/>'
        '<circle cx="180" cy="52" r="15" fill="#f0674a" opacity=".22"/>'
        '<circle cx="271" cy="271" r="3" fill="#fff" opacity=".7"/></g>'
        '<g class="orbit orbit--3" style="transform-box:view-box;transform-origin:180px 180px">'
        '<circle cx="88" cy="180" r="6" fill="#8fb0ff"/>'
        '<circle cx="88" cy="180" r="13" fill="#8fb0ff" opacity=".22"/></g>'
        "</svg>"
        '<div class="hero__core"><div><b>30</b><span>day window</span></div></div>'
        "</div>"
    )


def _emphasis(text: str) -> str:
    """Escape ``text``, then turn *word* into italic emphasis."""
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", html.escape(text))


def hero(title: str, lede: str, chips: Sequence = (), kicker: str = "") -> None:
    """The opening panel: what this is, on what data, in about five seconds."""
    chip_html = "".join(
        f'<span class="chip">{html.escape(text)}</span>' for text, _tone in chips
    )
    _md(
        '<section class="hero"><div class="hero__copy">'
        + (f'<div class="hero__kicker">{html.escape(kicker)}</div>' if kicker else "")
        + f'<h1 class="hero__title">{_emphasis(title)}</h1>'
        f'<p class="hero__lede">{lede}</p></div>'
        + _hero_art()
        + (f'<div class="hero__chips">{chip_html}</div>' if chip_html else "")
        + "</section>"
    )


def page_header(eyebrow: str, title: str, standfirst: str = "") -> None:
    current = (st.session_state.get("_nav") or {}).get("current")
    tile = art.motif(current)
    copy = [
        f'<div class="phead__eyebrow">{html.escape(eyebrow)}</div>',
        f'<h1 class="phead__title">{_emphasis(title)}</h1>',
    ]
    if standfirst:
        copy.append(f'<p class="phead__lede">{standfirst}</p>')
    _md(
        f'<header class="phead{" phead--art" if tile else ""}">'
        '<div class="phead__copy">' + "".join(copy) + "</div>" + tile + "</header>"
    )


def section(label: str, note: str = "") -> None:
    body = f'<div class="sect"><div class="sect__label">{html.escape(label)}</div>'
    if note:
        body += f'<div class="sect__note">{note}</div>'
    _md(body + "</div>")


def answer(text: str, label: str = "The short answer", sub: str = "",
           figure: str = "", pair: bool = False, viz: str = "") -> None:
    """One plain-English sentence stating what the page found.

    ``figure`` is an optional headline number, already formatted by the page,
    shown large beside the sentence. ``viz`` is optional HTML (see
    ``dots_html``) placed at the right edge. The wording is written by the
    page; the numbers inside it come from the analysis outputs like the rest.
    """
    figure_html = ""
    if figure:
        css = "answer__figure answer__figure--pair" if pair else "answer__figure"
        figure_html = f'<div class="{css}">{html.escape(figure)}</div>'
    _md(
        '<div class="answer"><div>'
        f'<div class="answer__label">{html.escape(label)}</div>'
        f'<div class="answer__lead">{figure_html}<div class="answer__text">{text}</div></div>'
        + (f'<div class="answer__sub">{sub}</div>' if sub else "")
        + "</div>"
        + (f'<div class="answer__viz">{viz}</div>' if viz else "")
        + "</div>"
    )


def plain(text: str) -> None:
    """A plain-English paragraph, used inside tabs and expanders."""
    _md(f'<div class="plain">{text}</div>')


def callout(body: str, title: str = "", tone: str = "note") -> None:
    """tone: note | caution | strong."""
    classes = "callout" if tone == "note" else f"callout {tone}"
    glyph = {"note": "info", "caution": "alert", "strong": "flag"}.get(tone, "info")
    head = f'<div class="t">{html.escape(title)}</div>' if title else ""
    _md(
        f'<div class="{classes}"><span class="callout__icon">{_svg(glyph)}</span>'
        f'<div>{head}<div class="b">{body}</div></div></div>'
    )


def population(text: str, label: str = "Population") -> None:
    _md(
        f'<div class="pop"><span class="pop__icon">{_svg("users")}</span>'
        f'<div><div class="t">{html.escape(label)}</div>{text}</div></div>'
    )


def note(text: str) -> None:
    _md(f'<div class="fig-note">{text}</div>')


def definition_list(pairs: Iterable) -> None:
    rows = "".join(
        f'<div class="row"><div class="k">{html.escape(str(k))}</div>'
        f'<div class="v">{v}</div></div>'
        for k, v in pairs
    )
    with card():
        _md(f'<div class="deflist">{rows}</div>')


# --------------------------------------------------------------------------
# 100-dot arrays
# --------------------------------------------------------------------------


def dots_html(share: float, label_on: str, label_off: str, tone: str = "on",
              caption: str = "") -> str:
    """Draw 100 circles, filling the nearest whole number to ``share``.

    This is a picture of a percentage that is already reported elsewhere on the
    page, not a new statistic: the exact value stays in the label beside it.
    """
    filled = max(0, min(100, int(round(float(share)))))
    marks = "".join(
        f'<i class="{tone}" style="--i:{index}"></i>' if index < filled
        else f'<i style="--i:{index}"></i>'
        for index in range(100)
    )
    return (
        '<div class="dotwrap">'
        f'<div class="dots" role="img" aria-label="{html.escape(label_on)}">{marks}</div>'
        '<div class="dotside">'
        f'<div class="dots-legend"><b class="{tone}">{html.escape(label_on)}</b>'
        f'<b class="muted">{html.escape(label_off)}</b></div>'
        + (f'<div class="dots-cap">{caption}</div>' if caption else "")
        + "</div></div>"
    )


def dots(share: float, label_on: str, label_off: str, tone: str = "on",
         caption: str = "") -> None:
    _md(dots_html(share, label_on, label_off, tone, caption))


# --------------------------------------------------------------------------
# micro-visuals: small pictures of numbers the page has already printed
# --------------------------------------------------------------------------


def viz_duo(rows: Sequence, caption: str = "") -> str:
    """Two or more bars on a common scale. rows: (label, value, text, kind),
    kind 'a' (coral) or 'b' (blue). Bar length is value / largest value."""
    top = max(float(value) for _, value, _, _ in rows) or 1.0
    body = "".join(
        f'<div class="r"><span>{html.escape(label)}</span>'
        f'<span class="track"><i class="fill {kind}" '
        f'style="--w:{float(value) / top * 100:.2f}%"></i></span>'
        f"<b>{html.escape(text)}</b></div>"
        for label, value, text, kind in rows
    )
    cap = f'<div class="viz-cap">{html.escape(caption)}</div>' if caption else ""
    return f'<div class="viz viz-duo">{cap}{body}</div>'


def viz_ring(share: float, label: str, sub: str = "") -> str:
    """A ring filled to ``share`` per cent of the circle."""
    radius = 34
    length = max(0.0, min(100.0, float(share))) / 100 * 2 * math.pi * radius
    return (
        '<div class="viz viz-ring"><svg viewBox="0 0 84 84" aria-hidden="true">'
        f'<circle class="bg" cx="42" cy="42" r="{radius}"/>'
        f'<circle class="fg" cx="42" cy="42" r="{radius}" style="--len:{length:.2f}"/></svg>'
        f'<div><div class="lab">{html.escape(label)}</div>'
        f'<div class="sub">{html.escape(sub)}</div></div></div>'
    )


def viz_spark(values: Sequence[float], first_text: str, last_text: str,
              first_label: str = "First", last_label: str = "Last") -> str:
    """A sparkline drawn from zero, so its slope is not exaggerated."""
    series = [float(v) for v in values]
    width, height, pad_x, base, top = 200.0, 84.0, 4.0, 76.0, 8.0
    ceiling = max(series) * 1.12 or 1.0
    step = (width - 2 * pad_x) / max(len(series) - 1, 1)
    points = [
        (pad_x + i * step, base - (value / ceiling) * (base - top))
        for i, value in enumerate(series)
    ]
    path = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        mid = (x0 + x1) / 2
        path += f" C{mid:.1f} {y0:.1f} {mid:.1f} {y1:.1f} {x1:.1f} {y1:.1f}"
    area = f"{path} L{points[-1][0]:.1f} {base} L{points[0][0]:.1f} {base} Z"
    gradient = _uid("sg")
    return (
        f'<div class="viz viz-spark"><svg viewBox="0 0 {width:.0f} {height:.0f}" '
        'preserveAspectRatio="none" aria-hidden="true">'
        f'<defs><linearGradient id="{gradient}" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#f0674a" stop-opacity=".28"/>'
        '<stop offset="1" stop-color="#f0674a" stop-opacity="0"/></linearGradient></defs>'
        f'<line class="base" x1="0" y1="{base}" x2="{width:.0f}" y2="{base}"/>'
        f'<path class="area" d="{area}" style="fill:url(#{gradient})"/>'
        f'<path class="line" d="{path}" pathLength="1"/></svg>'
        f'<div class="cap"><span>{html.escape(first_label)} <b>{html.escape(first_text)}</b></span>'
        f'<span>{html.escape(last_label)} <b>{html.escape(last_text)}</b></span></div></div>'
    )


def viz_gauge(value: float, label: str, low: float = 0.5, high: float = 1.0,
              low_text: str = "0.5 guessing", high_text: str = "1 perfect") -> str:
    """A half-dial from ``low`` to ``high`` with the value marked."""
    radius = 50
    fraction = max(0.0, min(1.0, (float(value) - low) / (high - low)))
    length = fraction * math.pi * radius
    arc = f"M10 60A{radius} {radius} 0 0 1 110 60"
    return (
        '<div class="viz viz-gauge"><div class="dial">'
        f'<svg viewBox="0 0 120 66" aria-hidden="true"><path class="bg" d="{arc}"/>'
        f'<path class="fg" d="{arc}" style="--len:{length:.2f}"/></svg>'
        f'<div class="lab">{html.escape(label)}</div>'
        f'<div class="ticks"><span>{html.escape(low_text)}</span>'
        f"<span>{html.escape(high_text)}</span></div></div></div>"
    )


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

_TONE_CLASS = {"coral": "kpi--coral", "teal": "kpi--teal", "amber": "kpi--amber"}


def _kpi_html(item: dict) -> str:
    """One KPI card. ``tone`` keeps the meaning pages already assign:
    accent = the headline figure, quiet = supporting detail."""
    tone = item.get("tone", "")
    classes = ["kpi"]
    if tone == "accent":
        classes.append("kpi--feature")
    elif tone == "quiet":
        classes.append("kpi--quiet")
    elif item.get("tint") in _TONE_CLASS:
        classes.append(_TONE_CLASS[item["tint"]])

    value_class = "kpi__value kpi__value--small" if item.get("small") else "kpi__value"
    icon = _icon_badge(item.get("icon") or _infer_icon(item["label"]))
    note_text = item.get("note", "")
    return (
        f'<div class="{" ".join(classes)}"><div class="kpi__top">'
        f'<div class="kpi__label">{html.escape(item["label"])}</div>{icon}</div>'
        f'<div class="{value_class}">{html.escape(str(item["value"]))}</div>'
        + (f'<div class="kpi__note">{note_text}</div>' if note_text else "")
        + "</div>"
    )


def stat(value: str, label: str, note_text: str = "", tone: str = "",
         small: bool = False) -> None:
    stat_grid([{"value": value, "label": label, "note": note_text,
                "tone": tone, "small": small}], columns=1)


def stat_grid(items: Sequence, columns: int = None) -> None:
    """A row of KPI cards. Each item: value, label, note, tone, icon, tint, small.

    All cards share one grid, so widths are equal and every card in a row is
    as tall as the tallest, whatever their text lengths.
    """
    items = list(items)
    if not items:
        return
    columns = columns or len(items)
    _md(
        f'<div class="kpis" style="--cols:{columns}">'
        + "".join(_kpi_html(item) for item in items)
        + "</div>"
    )


def findings(items: Sequence) -> None:
    """Numbered finding cards, each one a link to the page holding the evidence.

    Each item: title, body, viz (optional HTML), go (a navigation page title).
    Five cards fill a 6-column grid as three-then-two, so both rows are flush.
    """
    cards = []
    for index, item in enumerate(items):
        href = page_href(item.get("go", ""))
        tag = "a" if href else "div"
        link = f' href="{html.escape(href)}" target="_self"' if href else ""
        cards.append(
            f'<{tag} class="finding"{link}>'
            f'<div class="finding__top"><span class="finding__idx">{index + 1:02d}</span>'
            f'<span class="finding__go">{_svg("arrow")}</span></div>'
            + (f'<div class="finding__viz">{item["viz"]}</div>' if item.get("viz") else "")
            + f'<div class="finding__title">{html.escape(item["title"])}</div>'
            f'<div class="finding__body">{item["body"]}</div></{tag}>'
        )
    _md('<div class="findings">' + "".join(cards) + "</div>")


# --------------------------------------------------------------------------
# figures and tables
# --------------------------------------------------------------------------


def figure(fig: go.Figure, title: str, subtitle: str = "",
           note_text: str = "", source: str = "", takeaway: str = "") -> None:
    """A chart on a card, with its plain-English reading inside the same card.

    ``takeaway`` is the sentence a non-specialist should leave with. It sits
    under the chart rather than in a separate box, so the two are read together
    and the widths always match.
    """
    head = f'<div class="fig-head"><div class="t">{html.escape(title)}</div>'
    if subtitle:
        head += f'<div class="s">{html.escape(subtitle)}</div>'
    with card():
        _md(head + "</div>")
        st.plotly_chart(fig, config=PLOTLY_CONFIG, theme=None)
        if takeaway:
            _md(
                f'<div class="takeaway"><span class="takeaway__icon">{_svg("bulb")}</span>'
                f"<div>{takeaway}</div></div>"
            )
        trailing = " ".join(
            part for part in (note_text, f"Source: {html.escape(source)}." if source else "")
            if part
        )
        if trailing:
            note(trailing)


def table(frame: pd.DataFrame, note_text: str = "", column_config=None,
          height: int = None) -> None:
    with card():
        st.dataframe(
            frame,
            hide_index=True,
            column_config=column_config,
            **({"height": height} if height else {}),
        )
        if note_text:
            note(note_text)


def suppression_text(small_cells: pd.DataFrame, table_name: str) -> str:
    """State what the source table withheld, without restating the value."""
    rows = small_cells[small_cells["table"] == table_name]
    if rows.empty:
        return ""
    withheld = ", ".join(sorted(rows["row"].astype(str)))
    reason = rows["reason"].iloc[0]
    return (
        f"Withheld in the released table and therefore not plotted: "
        f"<b>{html.escape(withheld)}</b> ({html.escape(str(reason))}). "
        "Suppressed values are not recovered from the visible rows."
    )


def suppression_notice(small_cells: pd.DataFrame, table_name: str) -> None:
    text = suppression_text(small_cells, table_name)
    if text:
        note(text)


# --------------------------------------------------------------------------
# footer
# --------------------------------------------------------------------------


def footer() -> None:
    _md(
        '<div class="foot"><span class="cite">'
        f"{html.escape(licensing.CIHI_ATTRIBUTION)}</span><hr>"
        "Derived aggregate results. No record-level data is included in or "
        "reachable from this application. Figures are read from the analysis "
        "outputs at load time, not typed into the pages."
        "</div>"
    )
