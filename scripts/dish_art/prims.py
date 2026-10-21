"""Drawing primitives for the generated dish illustrations (pure SVG strings)."""

from __future__ import annotations

import math
import random

W, H = 400, 300
CX, CY = 200, 150


# ── basic shapes ────────────────────────────────────────────────────────────
def _attrs(fill, stroke=None, sw=0, op=1.0, extra=""):
    a = f'fill="{fill}"'
    if stroke:
        a += f' stroke="{stroke}" stroke-width="{sw}"'
    if op != 1.0:
        a += f' opacity="{op}"'
    if extra:
        a += " " + extra
    return a


def C(cx, cy, r, fill, stroke=None, sw=0, op=1.0, extra=""):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" {_attrs(fill, stroke, sw, op, extra)}/>'


def E(cx, cy, rx, ry, fill, stroke=None, sw=0, op=1.0, rot=0, extra=""):
    t = f' transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})"' if rot else ""
    return (
        f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"{t} '
        f"{_attrs(fill, stroke, sw, op, extra)}/>"
    )


def R(x, y, w, h, fill, stroke=None, sw=0, rx=0, op=1.0, rot=0, extra=""):
    t = f' transform="rotate({rot:.1f} {x + w / 2:.1f} {y + h / 2:.1f})"' if rot else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}"{t} '
        f"{_attrs(fill, stroke, sw, op, extra)}/>"
    )


def P(d, fill="none", stroke=None, sw=0, op=1.0, extra=""):
    return f'<path d="{d}" {_attrs(fill, stroke, sw, op, extra)}/>'


def L(x1, y1, x2, y2, stroke, sw=2, op=1.0, cap="round"):
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
        f'stroke-width="{sw}" stroke-linecap="{cap}" opacity="{op}"/>'
    )


def T(x, y, text, size, fill, weight=800, anchor="middle", rot=0):
    t = f' transform="rotate({rot} {x} {y})"' if rot else ""
    return (
        f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{t}>{text}</text>'
    )


def G(content, transform=""):
    t = f' transform="{transform}"' if transform else ""
    return f"<g{t}>{content}</g>"


def shadow(cx, cy, rx, ry, op=0.22):
    return E(cx, cy, rx, ry, "#3b2a1a", op=op, extra='filter="url(#blur)"')


def shine(cx, cy, rx, ry, op=0.35, rot=-20):
    return E(cx, cy, rx, ry, "#ffffff", op=op, rot=rot)


# ── scattering helper ───────────────────────────────────────────────────────
def scatter(rng, cx, cy, rad, n, fn, squash=1.0, inner=0.0):
    """Evenly spread n items inside an ellipse (golden-angle spiral + jitter)."""
    out = []
    phase = rng.uniform(0, 2 * math.pi)
    for i in range(n):
        a = phase + i * 2.399963 + rng.uniform(-0.25, 0.25)
        t = (i + 0.5) / n
        r = rad * math.sqrt(inner * inner + (1 - inner * inner) * t) * rng.uniform(0.9, 1.0)
        out.append(fn(cx + r * math.cos(a), cy + r * math.sin(a) * squash, i))
    return "".join(out)


# ── garnish ─────────────────────────────────────────────────────────────────
def coriander(x, y, rng, s=1.0):
    out = ""
    for k in range(3):
        a = rng.uniform(0, 360)
        out += E(x, y, 5 * s, 2.6 * s, "#4f9a3f", rot=a)
    return out


def curry_leaf(x, y, rot=0, s=1.0):
    return E(x, y, 8 * s, 3.4 * s, "#3f7d34", rot=rot) + L(
        x - 7 * s * math.cos(math.radians(rot)),
        y - 7 * s * math.sin(math.radians(rot)),
        x + 7 * s * math.cos(math.radians(rot)),
        y + 7 * s * math.sin(math.radians(rot)),
        "#2d5f26",
        1,
    )


def red_chili(x, y, rot=0, s=1.0):
    return G(
        E(0, 0, 12 * s, 3.6 * s, "#c8261b") + E(-3 * s, -1 * s, 6 * s, 1.1 * s, "#ef6a57", op=0.8)
        + R(10 * s, -1.5 * s, 4 * s, 3 * s, "#3f7d34", rx=1),
        f"translate({x:.1f} {y:.1f}) rotate({rot})",
    )


def green_chili(x, y, rot=0, s=1.0):
    return G(
        E(0, 0, 12 * s, 3.4 * s, "#4f9a3f") + E(-3 * s, -1 * s, 6 * s, 1.0 * s, "#8bd06f", op=0.8)
        + R(10 * s, -1.4 * s, 4 * s, 2.8 * s, "#2d5f26", rx=1),
        f"translate({x:.1f} {y:.1f}) rotate({rot})",
    )


def onion_ring(x, y, r=9, rot=0):
    return E(x, y, r, r * 0.6, "none", stroke="#d9a6c9", sw=2.2, rot=rot) + E(
        x, y, r * 0.6, r * 0.36, "none", stroke="#efd0e4", sw=1.6, rot=rot
    )


def lime_wedge(x, y, r=16, rot=0):
    return G(
        P(f"M{-r} 0 A{r} {r} 0 0 1 {r} 0 Z", "#8fcf3f", "#4f8f1f", 2)
        + P(f"M{-r * 0.8:.1f} 0 A{r * 0.8:.1f} {r * 0.8:.1f} 0 0 1 {r * 0.8:.1f} 0 Z", "#d6f08a")
        + "".join(
            L(0, 0, r * 0.72 * math.cos(math.radians(a)), -r * 0.72 * math.sin(math.radians(a)), "#8fcf3f", 1.3)
            for a in (30, 60, 90, 120, 150)
        ),
        f"translate({x:.1f} {y:.1f}) rotate({rot})",
    )


def lemon_wedge(x, y, r=16, rot=0):
    return G(
        P(f"M{-r} 0 A{r} {r} 0 0 1 {r} 0 Z", "#f6d84a", "#d9b414", 2)
        + P(f"M{-r * 0.8:.1f} 0 A{r * 0.8:.1f} {r * 0.8:.1f} 0 0 1 {r * 0.8:.1f} 0 Z", "#fff3a8")
        + "".join(
            L(0, 0, r * 0.72 * math.cos(math.radians(a)), -r * 0.72 * math.sin(math.radians(a)), "#f6d84a", 1.3)
            for a in (30, 60, 90, 120, 150)
        ),
        f"translate({x:.1f} {y:.1f}) rotate({rot})",
    )


def spring_onion(x, y, rng, n=1):
    out = ""
    for _ in range(n):
        out += E(x + rng.uniform(-2, 2), y + rng.uniform(-2, 2), 4, 2.2, "#7cc35a", "#3f8f2f", 0.8)
    return out


# ── vessels (top-down) ──────────────────────────────────────────────────────
def plate_white(cx, cy, r):
    return (
        shadow(cx + 4, cy + r * 0.2, r, r * 0.92)
        + C(cx, cy, r, "#ffffff", "#e3ddd3", 2)
        + C(cx, cy, r * 0.82, "#fbf9f5", "#ece6dc", 1.5)
    )


def plate_steel(cx, cy, r):
    return (
        shadow(cx + 4, cy + r * 0.2, r, r * 0.92)
        + C(cx, cy, r, "#c9ced4", "#9aa1a9", 2)
        + C(cx, cy, r * 0.94, "#e8ebef")
        + C(cx, cy, r * 0.78, "#dde1e6", "#b9bfc6", 1.5)
        + shine(cx - r * 0.35, cy - r * 0.55, r * 0.35, r * 0.1, 0.5)
    )


def plate_black(cx, cy, r):
    return (
        shadow(cx + 4, cy + r * 0.2, r, r * 0.92, 0.3)
        + C(cx, cy, r, "#2b2b2f", "#161618", 2)
        + C(cx, cy, r * 0.86, "#37373c", "#232327", 1.5)
        + shine(cx - r * 0.35, cy - r * 0.6, r * 0.3, r * 0.07, 0.15)
    )


def bowl_top(cx, cy, r, inner, rim="#ffffff", rim_stroke="#e1dad0"):
    return (
        shadow(cx + 3, cy + r * 0.25, r, r * 0.9, 0.2)
        + C(cx, cy, r, rim, rim_stroke, 2)
        + C(cx, cy, r * 0.84, inner)
        + P(
            f"M{cx - r * 0.78:.1f} {cy - r * 0.15:.1f} A{r * 0.8:.1f} {r * 0.8:.1f} 0 0 1 {cx + r * 0.1:.1f} {cy - r * 0.8:.1f}",
            "none",
            "#ffffff",
            2,
            0.35,
        )
    )


def katori(cx, cy, r, inner):
    return (
        shadow(cx + 2, cy + r * 0.25, r, r * 0.9, 0.2)
        + C(cx, cy, r, "#c9ced4", "#9aa1a9", 1.5)
        + C(cx, cy, r * 0.82, inner)
        + P(
            f"M{cx - r * 0.7:.1f} {cy - r * 0.1:.1f} A{r * 0.72:.1f} {r * 0.72:.1f} 0 0 1 {cx + r * 0.1:.1f} {cy - r * 0.72:.1f}",
            "none",
            "#ffffff",
            1.6,
            0.5,
        )
    )


def banana_leaf(cx, cy, rx, ry):
    veins = "".join(
        L(cx - rx * 0.9 + i * rx * 0.2, cy, cx - rx * 0.78 + i * rx * 0.2, cy - ry * 0.95, "#3f8f43", 1.2, 0.55)
        + L(cx - rx * 0.9 + i * rx * 0.2, cy, cx - rx * 0.78 + i * rx * 0.2, cy + ry * 0.95, "#3f8f43", 1.2, 0.55)
        for i in range(0, 10)
    )
    return (
        shadow(cx + 4, cy + ry * 0.2, rx, ry * 0.95)
        + E(cx, cy, rx, ry, "#58a95a", "#3a7f3e", 2)
        + E(cx, cy, rx * 0.94, ry * 0.92, "#6cba6c")
        + veins
        + L(cx - rx * 0.95, cy, cx + rx * 0.95, cy, "#3a7f3e", 2.4)
    )


def rice_mound(cx, cy, rx, ry, rng, tint="#fffdf7", grains=40):
    out = E(cx, cy, rx, ry, tint, "#efe8d8", 1.5)
    out += scatter(rng, cx, cy, rx * 0.85, grains, lambda x, y, i: E(x, y, 3.2, 1.2, "#ffffff", rot=rng.uniform(0, 180), op=0.9), squash=ry / rx)
    out += shine(cx - rx * 0.3, cy - ry * 0.45, rx * 0.35, ry * 0.18, 0.5)
    return out


def sauce_bowl(cx, cy, r, color, dot=None):
    out = katori(cx, cy, r, color)
    if dot:
        out += C(cx - r * 0.2, cy - r * 0.1, r * 0.12, dot) + C(cx + r * 0.25, cy + r * 0.2, r * 0.1, dot)
    return out


def steam(x, y, n=3, color="#ffffff"):
    out = ""
    for i in range(n):
        ox = x + (i - (n - 1) / 2) * 16
        out += P(
            f"M{ox:.1f} {y:.1f} c-8 -12 8 -20 0 -32 c-6 -9 4 -16 0 -24",
            "none",
            color,
            3.2,
            0.55,
            'stroke-linecap="round"',
        )
    return out


# ── glassware (side view) ───────────────────────────────────────────────────
def tall_glass(cx, top, bottom, wt, wb, liquid_a, liquid_b, level=0.18, uid="g", extras_inside="", extras_front=""):
    """Tapered tumbler. level = fraction of height left empty at the top."""
    h = bottom - top
    ly = top + h * level
    wl = wt - (wt - wb) * level
    clip = (
        f'<clipPath id="{uid}c"><path d="M{cx - wt / 2:.1f} {top:.1f} L{cx + wt / 2:.1f} {top:.1f} '
        f'L{cx + wb / 2:.1f} {bottom:.1f} Q{cx:.1f} {bottom + 8:.1f} {cx - wb / 2:.1f} {bottom:.1f} Z"/></clipPath>'
    )
    grad = (
        f'<linearGradient id="{uid}l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{liquid_a}"/>'
        f'<stop offset="1" stop-color="{liquid_b}"/></linearGradient>'
    )
    body = (
        f'<g clip-path="url(#{uid}c)">'
        + R(cx - wt / 2, ly, wt, bottom - ly + 10, f"url(#{uid}l)")
        + E(cx, ly, wl / 2, 6, liquid_a, op=0.9)
        + extras_inside
        + "</g>"
    )
    outline = P(
        f"M{cx - wt / 2:.1f} {top:.1f} L{cx + wt / 2:.1f} {top:.1f} L{cx + wb / 2:.1f} {bottom:.1f} "
        f"Q{cx:.1f} {bottom + 8:.1f} {cx - wb / 2:.1f} {bottom:.1f} Z",
        "#ffffff",
        "#b8c4cc",
        2.4,
        extra='fill-opacity="0.16"',
    )
    rim = E(cx, top, wt / 2, 6, "none", "#b8c4cc", 2)
    hl = P(
        f"M{cx - wt / 2 + 9:.1f} {top + 12:.1f} L{cx - wb / 2 + 8:.1f} {bottom - 14:.1f}", "none", "#ffffff", 5, 0.55, 'stroke-linecap="round"'
    )
    return f"<defs>{clip}{grad}</defs>" + body + outline + rim + hl + extras_front


def straw(x1, y1, x2, y2, color="#e4572e"):
    return L(x1, y1, x2, y2, color, 6) + L(x1 - 1.5, y1, x2 - 1.5, y2, "#ffffff", 1.6, 0.45)


def ice_cubes(rng, cx, ytop, ybot, wid, n=4, op=0.55):
    out = ""
    for _ in range(n):
        x = cx + rng.uniform(-wid / 2, wid / 2)
        y = rng.uniform(ytop, ybot)
        out += R(x - 10, y - 10, 20, 20, "#ffffff", rx=4, stroke="#dff1fb", sw=1.5, op=op, rot=rng.uniform(-25, 25))
    return out


def bubbles(rng, cx, ytop, ybot, wid, n=14):
    return "".join(
        C(cx + rng.uniform(-wid / 2, wid / 2), rng.uniform(ytop, ybot), rng.uniform(1.4, 3.2), "#ffffff", op=0.7)
        for _ in range(n)
    )


def soft_scoop(cx, cy, r, color, shade):
    return (
        E(cx, cy + r * 0.62, r * 1.02, r * 0.3, shade)
        + C(cx, cy, r, color)
        + E(cx - r * 0.3, cy - r * 0.35, r * 0.32, r * 0.18, "#ffffff", op=0.45, rot=-30)
    )


def whipped_cream(cx, cy, w=34):
    return (
        E(cx, cy + 8, w * 0.55, 9, "#fffaf0", "#eadfca", 1)
        + E(cx, cy, w * 0.42, 9, "#ffffff", "#eadfca", 1)
        + E(cx, cy - 9, w * 0.26, 8, "#ffffff", "#eadfca", 1)
        + P(f"M{cx - 4:.1f} {cy - 20:.1f} q4 -9 8 0", "#ffffff", "#eadfca", 1)
    )


def wrap_svg(body, bg_a, bg_b, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
        f'aria-label="{title}"><title>{title}</title><defs>'
        f'<radialGradient id="bg" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="{bg_a}"/>'
        f'<stop offset="1" stop-color="{bg_b}"/></radialGradient>'
        '<filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="5"/></filter>'
        f'</defs><rect width="{W}" height="{H}" fill="url(#bg)"/>{body}</svg>'
    )


def rng_for(code):
    return random.Random(code)
