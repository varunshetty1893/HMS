"""Renderers for breakfast, meals, rice, biryani, breads and curries."""

from __future__ import annotations

import math

from prims import *  # noqa: F401,F403


# ── Breakfast ───────────────────────────────────────────────────────────────
def _idli(cx, cy, rng):
    return (
        E(cx, cy + 10, 52, 20, "#e0d8c4")
        + E(cx, cy, 52, 40, "#fffefa", "#e6dfcc", 2)
        + E(cx, cy - 8, 40, 26, "#ffffff", "#f0ead8", 1.2)
        + scatter(rng, cx, cy - 6, 30, 10, lambda x, y, i: C(x, y, 1.5, "#e0d6bc"), squash=0.6)
        + shine(cx - 16, cy - 20, 18, 6, 0.7)
    )


def breakfast_idli(code, rng):
    return (
        banana_leaf(200, 150, 168, 112)
        + _idli(150, 138, rng)
        + _idli(235, 168, rng)
        + sauce_bowl(300, 108, 30, "#c8642a", "#f0a44a")
        + sauce_bowl(110, 205, 28, "#f4f1e4", "#6aa84f")
        + coriander(300, 108, rng)
    )


def _dosa_cone(cx, cy, length, thick, filling=False, rot=-8):
    body = (
        E(0, 0, length / 2, thick / 2, "#e3a74a", "#b9792a", 2)
        + E(0, -thick * 0.1, length / 2 - 6, thick / 2 - 6, "#f0bf62")
        + "".join(L(-length / 2 + 14 + i * 22, -thick / 2 + 8, -length / 2 + 26 + i * 22, thick / 2 - 8, "#c98a34", 2, 0.5) for i in range(int(length / 22) - 1))
        + E(length / 2 - 4, 0, 9, thick / 2 - 3, "#b9792a")
    )
    if filling:
        body += (
            E(length / 2 - 6, 0, 17, thick / 2 - 8, "#f4d03f", "#d9ab1b", 1.5)
            + "".join(C(length / 2 - 12 + dx, dy, 4.2, "#e6b422", "#c99a14", 1) for dx, dy in ((0, -14), (8, -4), (-2, 6), (10, 12), (2, 0)))
            + C(length / 2 - 4, 8, 2.6, "#4f9a3f") + C(length / 2 - 10, -8, 2.4, "#4f9a3f")
        )
    return G(body, f"translate({cx} {cy}) rotate({rot})")


def breakfast_dosa(code, rng, kind="plain"):
    out = plate_steel(200, 150, 138)
    if kind == "plain":
        out += _dosa_cone(196, 152, 252, 96, rot=-12)
    elif kind == "masala":
        out += _dosa_cone(196, 152, 252, 96, filling=True, rot=-12)
    else:  # set dosa – stack of 3 soft round dosas
        for i, (x, y) in enumerate(((165, 168), (205, 148), (238, 125))):
            out += E(x, y + 6, 58, 40, "#d9b56b") + E(x, y, 58, 40, "#fbeccb", "#ead29b", 2)
            out += scatter(rng, x, y, 40, 26, lambda a, b, j: C(a, b, 1.5, "#e6c98a"), squash=0.6)
            out += shine(x - 18, y - 16, 20, 6, 0.55)
    out += sauce_bowl(318, 232, 24, "#f4f1e4", "#6aa84f") + sauce_bowl(76, 70, 24, "#c8642a", "#f0a44a")
    return out


def breakfast_poori(code, rng):
    out = plate_white(200, 150, 138)
    for x, y in ((140, 120), (200, 96), (150, 188)):
        out += E(x, y + 5, 46, 32, "#c98a34") + E(x, y, 46, 32, "#eeb455", "#c98a34", 2)
        out += E(x - 10, y - 8, 20, 7, "#fff3c4", op=0.55, rot=-15)
    out += bowl_top(262, 170, 48, "#f2c230")
    out += scatter(rng, 262, 170, 34, 9, lambda x, y, i: E(x, y, 7, 5, "#d9a31a", rot=rng.uniform(0, 180)), squash=0.9)
    out += coriander(262, 165, rng) + red_chili(240, 214, -20, 0.8)
    return out


# ── Meals / thali ───────────────────────────────────────────────────────────
def lunch_meals(code, rng, kind="veg"):
    south = kind == "south"
    out = banana_leaf(200, 150, 180, 125) if south else plate_steel(200, 150, 142)
    out += rice_mound(200, 150, 60, 46, rng)
    cups = {
        "veg": ["#d98a2b", "#8ba84a", "#c8432b", "#f0e0a0"],
        "special": ["#d98a2b", "#8ba84a", "#c8432b", "#f0e0a0", "#e8a0b4", "#f2e6c4"],
        "south": ["#c8642a", "#d9c46a", "#f4f1e4", "#8ba84a"],
        "chicken": ["#b8441f", "#8b4a1f", "#8ba84a", "#f0e0a0"],
        "fish": ["#c8432b", "#d98a2b", "#8ba84a", "#f0e0a0"],
    }[kind]
    n = len(cups)
    for i, col in enumerate(cups):
        a = math.radians(-90 + i * 360 / n + 20)
        out += katori(200 + 98 * math.cos(a), 150 + 76 * math.sin(a), 24 if n < 6 else 21, col)
    if kind == "chicken":
        out += E(200, 112, 18, 10, "#c0652a", rot=20) + E(226, 140, 16, 9, "#a8501f", rot=-30)
    if kind == "fish":
        out += E(205, 118, 32, 13, "#d8943a", "#a8641a", 1.5, rot=-12) + L(185, 118, 225, 112, "#b57426", 2)
        out += lemon_wedge(250, 184, 12, 20)
    if kind in ("veg", "special"):
        out += E(200, 214, 34, 5, "#f2dc9a", "#d9b96a", 1)  # papad
    if kind == "special":
        out += C(280, 205, 11, "#8c3b1c") + C(298, 196, 11, "#8c3b1c")  # sweet balls
    out += coriander(200, 150, rng, 0.9)
    return out


# ── Rice ────────────────────────────────────────────────────────────────────
def rice_dish(code, rng, kind="steamed", style="bowl"):
    base = {"bowl": lambda: bowl_top(200, 150, 128, "#f7f1e2", rim="#ffffff" if kind != "steamed" else "#5fa8d3", rim_stroke="#e1dad0" if kind != "steamed" else "#3f84ad"), "black": lambda: plate_black(200, 150, 138), "steel": lambda: plate_steel(200, 150, 138)}[style]
    out = base()
    tint = {"steamed": "#fffdf7", "jeera": "#f8f1da", "ghee": "#f8e7a5", "pulao": "#f4e4a0", "veg": "#f5e6b0", "egg": "#f5e3a2", "chicken": "#f3dba0"}[kind]
    out += E(200, 150, 92, 70, tint, "#e8dcb8", 1.5)
    out += scatter(rng, 200, 150, 82, 70, lambda x, y, i: E(x, y, 4, 1.5, "#ffffff", rot=rng.uniform(0, 180), op=0.9), squash=0.78)
    if kind == "steamed":
        out += E(200, 142, 76, 52, "#fffdf6", "#e6dcc0", 1.8)
        out += scatter(rng, 200, 140, 66, 70, lambda x, y, i: E(x, y, 4.2, 1.6, "#ffffff", "#ece3c8", 0.5, rot=rng.uniform(0, 180)), squash=0.62)
        out += shine(168, 112, 30, 9, 0.7) + steam(200, 92, 3, "#9fb4c4")
    if kind == "jeera":
        out += scatter(rng, 200, 150, 80, 36, lambda x, y, i: E(x, y, 3, 1.2, "#6b4a1f", rot=rng.uniform(0, 180)), squash=0.78)
        out += coriander(200, 100, rng, 1.1)
    elif kind == "ghee":
        out += E(200, 150, 40, 22, "#f6c744", op=0.55)
        out += scatter(rng, 200, 150, 70, 7, lambda x, y, i: E(x, y, 6, 3.4, "#e8c07a", "#c9993a", 1, rot=rng.uniform(0, 180)), squash=0.75)
        out += scatter(rng, 200, 150, 70, 6, lambda x, y, i: C(x, y, 2.6, "#7a3d18"), squash=0.75)
    elif kind in ("pulao", "veg"):
        cols = ["#e8742a", "#4f9a3f", "#7cc35a", "#f2f2e8"] if kind == "pulao" else ["#e8742a", "#4f9a3f", "#7cc35a", "#f4f0e0"]
        out += scatter(rng, 200, 150, 78, 34, lambda x, y, i: R(x - 3.5, y - 3.5, 7, 7, cols[i % 4], rx=1.5, rot=rng.uniform(0, 90)), squash=0.78)
        if kind == "pulao":
            out += scatter(rng, 200, 150, 70, 6, lambda x, y, i: E(x, y, 5, 3, "#e8c07a", "#c9993a", 1, rot=rng.uniform(0, 180)), squash=0.75)
            out += E(200, 150, 14, 14, "#fff", "#ddd", 0.1, op=0)
        else:
            out += scatter(rng, 200, 150, 76, 10, lambda x, y, i: spring_onion(x, y, rng), squash=0.78)
    elif kind == "egg":
        out += scatter(rng, 200, 150, 76, 22, lambda x, y, i: E(x, y, 7, 4.5, "#f7d84a", "#e0b820", 1, rot=rng.uniform(0, 180)), squash=0.78)
        out += scatter(rng, 200, 150, 72, 10, lambda x, y, i: spring_onion(x, y, rng), squash=0.78)
        out += scatter(rng, 200, 150, 60, 8, lambda x, y, i: R(x - 3, y - 3, 6, 6, "#e8742a", rx=1.5), squash=0.78)
    elif kind == "chicken":
        out += scatter(rng, 200, 150, 76, 14, lambda x, y, i: R(x - 5, y - 4, 10, 8, "#c0793a", rx=2, rot=rng.uniform(0, 90)), squash=0.78)
        out += scatter(rng, 200, 150, 76, 14, lambda x, y, i: R(x - 3, y - 3, 6, 6, "#7cc35a" if i % 2 else "#e8742a", rx=1.5), squash=0.78)
        out += scatter(rng, 200, 150, 72, 8, lambda x, y, i: spring_onion(x, y, rng), squash=0.78)
    else:
        out += E(200, 112, 12, 5, "#ffffff", op=0.6)
    if style == "black":
        out += L(300, 70, 345, 120, "#c79a5c", 4) + L(312, 64, 355, 112, "#c79a5c", 4)
    return out


# ── Biryani ─────────────────────────────────────────────────────────────────
def _biryani_base(rng, tint_a="#f0b34a"):
    out = plate_steel(200, 150, 140)
    out += E(200, 148, 100, 72, tint_a, "#c98a2a", 1.5)
    out += scatter(rng, 200, 148, 92, 90, lambda x, y, i: E(x, y, 4.4, 1.5, ["#fff4d6", "#f6c562", "#e8932a", "#fffdf2"][i % 4], rot=rng.uniform(0, 180)), squash=0.74)
    return out


def _fried_onions(rng, n=14):
    return scatter(rng, 200, 148, 80, n, lambda x, y, i: E(x, y, 7, 1.8, "#7a4416", rot=rng.uniform(0, 180)), squash=0.74)


def _drumstick(x, y, rot=0, s=1.0, col="#b9561f"):
    return G(
        E(0, 0, 26 * s, 15 * s, col, "#8a3a14", 1.5)
        + E(-4 * s, -4 * s, 15 * s, 5 * s, "#e08a4a", op=0.6)
        + R(22 * s, -3 * s, 16 * s, 6 * s, "#f6efe0", rx=3, stroke="#d8cdb4", sw=1)
        + C(38 * s, -3 * s, 4.2 * s, "#f6efe0", "#d8cdb4", 1)
        + C(38 * s, 3 * s, 4.2 * s, "#f6efe0", "#d8cdb4", 1),
        f"translate({x} {y}) rotate({rot})",
    )


def biryani(code, rng, kind="chicken"):
    out = _biryani_base(rng, "#f2b94d" if kind != "mutton" else "#e8a23c")
    out += _fried_onions(rng)
    if kind == "veg":
        out += scatter(rng, 200, 148, 62, 7, lambda x, y, i: R(x - 8, y - 8, 16, 16, "#fff1d0", rx=6, stroke="#e3c98a", sw=1.2, rot=rng.uniform(0, 90)), squash=0.74)
        out += scatter(rng, 200, 148, 70, 8, lambda x, y, i: R(x - 4, y - 4, 8, 8, "#e8742a", rx=2), squash=0.74)
        out += scatter(rng, 200, 148, 70, 8, lambda x, y, i: C(x, y, 3.2, "#4f9a3f"), squash=0.74)
        out += E(150, 140, 18, 10, "#e8d070", rot=-10, op=0.0)
    elif kind == "egg":
        for x, y, r in ((158, 140, -15), (238, 156, 20)):
            out += E(x, y, 24, 17, "#fffaf0", "#e6d9b8", 1.5, rot=r) + E(x, y, 10, 8, "#f8c820", rot=r)
        out += scatter(rng, 200, 148, 62, 6, lambda x, y, i: R(x - 3, y - 3, 6, 6, "#e8742a", rx=1.5), squash=0.74)
    elif kind == "chicken":
        out += _drumstick(160, 140, -25) + _drumstick(236, 160, 200, 0.95)
    elif kind == "dum":
        out = plate_steel(200, 150, 140) + C(200, 150, 112, "#7a4a2a", "#4e2c14", 3) + C(200, 150, 98, "#a8693a", "#6a3b1a", 2)
        out += C(200, 150, 80, "#f2b94d", "#c98a2a", 2)
        out += scatter(rng, 200, 150, 70, 70, lambda x, y, i: E(x, y, 4.4, 1.5, ["#fff4d6", "#f6c562", "#e8932a"][i % 3], rot=rng.uniform(0, 180)), squash=0.95)
        out += _drumstick(188, 140, -20, 1.05) + _fried_onions(rng, 10)
        out += P("M92 150 A108 108 0 0 1 150 70", "none", "#d9a05a", 6, 0.8)  # dough seal
    elif kind == "mutton":
        for x, y, r in ((152, 138, -20), (238, 156, 25), (196, 118, 70)):
            out += R(x - 17, y - 12, 34, 24, "#7a3a1a", rx=9, stroke="#4e2410", sw=1.5, rot=r) + R(x - 8, y - 7, 16, 8, "#a8582a", rx=4, rot=r, op=0.7)
            out += R(x + 8, y - 3, 14, 5, "#f6efe0", rx=2.5, rot=r, op=0.0)
    out += coriander(200, 100, rng) + coriander(240, 190, rng) + lime_wedge(300, 215, 14, -15)
    out += bowl_top(95, 225, 26, "#fbf4e6") + E(95, 225, 12, 8, "#ffffff", op=0.8)
    return out


# ── Breads ──────────────────────────────────────────────────────────────────
def breads(code, rng, kind="parotta"):
    out = plate_white(200, 150, 140)
    if kind == "parotta":
        for x, y in ((165, 170), (222, 130)):
            out += E(x, y + 5, 74, 56, "#b9792a") + E(x, y, 74, 56, "#e8b05a", "#c98a34", 2)
            out += "".join(P(f"M{x - 60 + i * 6:.1f} {y:.1f} A{22 + i * 8} {16 + i * 6} 0 0 1 {x + 20 - i * 3:.1f} {y - 20 - i * 5:.1f}", "none", "#c98a34", 2, 0.65) for i in range(5))
            out += shine(x - 22, y - 22, 24, 7, 0.4)
    elif kind == "chapati":
        for x, y in ((160, 160), (230, 130)):
            out += E(x, y + 4, 72, 54, "#c99a52") + E(x, y, 72, 54, "#f0d49a", "#d9b46a", 2)
            out += scatter(rng, x, y, 56, 12, lambda a, b, i: E(a, b, 6, 4, "#c98a3a", op=0.7), squash=0.72)
    elif kind == "roti":
        out += E(200, 156, 104, 80, "#b07a3a") + E(200, 150, 104, 80, "#e0b46a", "#b07a3a", 2)
        out += scatter(rng, 200, 150, 90, 24, lambda a, b, i: E(a, b, rng.uniform(5, 10), rng.uniform(3, 6), "#7a4a1a", op=0.75), squash=0.72)
    else:  # naan / butter naan
        path = "M110 205 C95 120 160 60 240 78 C300 92 312 150 286 196 C262 240 140 252 110 205 Z"
        out += P(path, "#cf9a4a", "#9a6a22", 2, extra='transform="translate(3 6)"') + P(path, "#f2d08a", "#d9a24a", 2)
        out += scatter(rng, 200, 150, 70, 14, lambda a, b, i: E(a, b, rng.uniform(5, 9), rng.uniform(3, 6), "#b5702a", op=0.6), squash=0.8)
        out += scatter(rng, 200, 150, 70, 10, lambda a, b, i: coriander(a, b, rng, 0.7), squash=0.8)
        if kind == "butter":
            out += R(172, 120, 34, 22, "#ffe36e", rx=3, stroke="#e8c030", sw=1.5, rot=-8) + E(200, 160, 62, 36, "#ffd84a", op=0.3, rot=-10)
            out += shine(180, 126, 12, 4, 0.7)
    return out


# ── Curries ─────────────────────────────────────────────────────────────────
def _kadai(cx, cy, r, gravy):
    return (
        shadow(cx + 4, cy + r * 0.3, r, r * 0.9, 0.28)
        + C(cx, cy, r, "#2d2d31", "#17171a", 2)
        + R(cx + r - 4, cy - 7, 36, 14, "#2d2d31", rx=6)
        + C(cx, cy, r * 0.86, gravy)
        + P(f"M{cx - r * 0.75:.1f} {cy - r * 0.2:.1f} A{r * 0.78:.1f} {r * 0.78:.1f} 0 0 1 {cx + r * 0.1:.1f} {cy - r * 0.78:.1f}", "none", "#ffffff", 2, 0.3)
    )


def veg_curry(code, rng, kind="paneer_butter"):
    if kind == "paneer_butter":
        out = bowl_top(200, 150, 132, "#e8832a")
        out += E(200, 150, 92, 70, "#f0963a")
        out += P("M130 150 q35 -26 70 0 t70 0", "none", "#fff6e0", 7, 0.9) + P("M140 175 q30 -18 60 0 t55 0", "none", "#fff6e0", 5, 0.7)
        out += scatter(rng, 200, 150, 60, 6, lambda x, y, i: R(x - 15, y - 15, 30, 30, "#fff0b8", "#e8cf7c", 1.5, rx=5, rot=rng.uniform(0, 60)), squash=0.8)
        out += R(188, 128, 22, 15, "#ffe36e", rx=3, stroke="#e8c030", sw=1.2, rot=-8) + coriander(240, 180, rng)
    elif kind == "kadai":
        out = _kadai(200, 150, 128, "#c8321a")
        out += scatter(rng, 200, 150, 70, 6, lambda x, y, i: R(x - 15, y - 15, 30, 30, "#f6dc92", "#d9b45a", 1.5, rx=5, rot=rng.uniform(0, 60)), squash=0.85)
        out += scatter(rng, 200, 150, 76, 9, lambda x, y, i: R(x - 12, y - 3, 24, 6, "#5fae3f", rx=3, rot=rng.uniform(0, 180)), squash=0.85)
        out += scatter(rng, 200, 150, 70, 4, lambda x, y, i: onion_ring(x, y, 9), squash=0.85) + coriander(205, 140, rng)
    elif kind == "dal":
        out = bowl_top(200, 150, 132, "#e6a520")
        out += E(200, 150, 92, 70, "#efb531")
        out += scatter(rng, 200, 150, 70, 24, lambda x, y, i: C(x, y, rng.uniform(2.5, 5), "#d98f12", op=0.55), squash=0.8)
        out += C(200, 150, 26, "#f6c744", op=0.8) + scatter(rng, 200, 150, 38, 10, lambda x, y, i: E(x, y, 5, 2, "#c8261b", rot=rng.uniform(0, 180)), squash=0.8)
        out += scatter(rng, 200, 150, 36, 7, lambda x, y, i: C(x, y, 2, "#4a2a10"), squash=0.8) + coriander(215, 140, rng) + coriander(185, 160, rng)
    elif kind == "kurma":
        out = bowl_top(200, 150, 132, "#e9d37a")
        out += E(200, 150, 92, 70, "#f1e09a")
        out += scatter(rng, 200, 150, 66, 7, lambda x, y, i: R(x - 7, y - 7, 14, 14, "#e8742a", rx=3, rot=rng.uniform(0, 90)), squash=0.8)
        out += scatter(rng, 200, 150, 66, 7, lambda x, y, i: R(x - 10, y - 3, 20, 6, "#5fae3f", rx=3, rot=rng.uniform(0, 180)), squash=0.8)
        out += scatter(rng, 200, 150, 66, 9, lambda x, y, i: C(x, y, 4, "#7cc35a"), squash=0.8)
        out += scatter(rng, 200, 150, 62, 5, lambda x, y, i: R(x - 8, y - 8, 16, 16, "#fff1c2", rx=5, stroke="#e3c98a", sw=1.2), squash=0.8) + coriander(200, 150, rng)
    else:  # chana
        out = bowl_top(200, 150, 132, "#a8501f")
        out += E(200, 150, 92, 70, "#b8631f")
        out += scatter(rng, 200, 150, 72, 28, lambda x, y, i: C(x, y, 8, "#e0b066", "#b88a3a", 1.5) + E(x - 2, y - 2, 3, 1.6, "#fff0c0", op=0.7), squash=0.8)
        out += scatter(rng, 200, 150, 60, 4, lambda x, y, i: onion_ring(x, y, 10, rng.uniform(0, 90)), squash=0.8) + coriander(210, 150, rng) + lemon_wedge(300, 215, 14, -20)
    return out


def nonveg_curry(code, rng, kind="chicken_curry"):
    if kind == "mutton":
        out = _kadai(200, 150, 128, "#6a2c12")
    else:
        out = bowl_top(200, 150, 132, {"chicken_curry": "#c8481f", "butter_chicken": "#e6762a", "chettinad": "#8a2a14", "egg": "#d9561f"}[kind])
        out += E(200, 150, 92, 70, {"chicken_curry": "#d8561f", "butter_chicken": "#ee8636", "chettinad": "#9a3418", "egg": "#e6662a"}[kind])
    if kind == "chicken_curry":
        out += scatter(rng, 200, 150, 58, 5, lambda x, y, i: R(x - 20, y - 14, 40, 28, "#b9561f", "#8a3a14", 1.8, rx=12, rot=rng.uniform(0, 90)) + E(x - 4, y - 4, 11, 4, "#e08a4a", op=0.6), squash=0.8)
        out += coriander(215, 195, rng) + coriander(165, 120, rng) + green_chili(260, 135, 30, 0.8)
    elif kind == "butter_chicken":
        out += P("M126 150 q40 -30 80 0 t76 0", "none", "#fff2dc", 8, 0.9)
        out += scatter(rng, 200, 150, 60, 5, lambda x, y, i: R(x - 20, y - 14, 40, 28, "#b8461a", "#7a2a0e", 1.8, rx=12, rot=rng.uniform(0, 90)), squash=0.8)
        out += R(190, 168, 22, 14, "#ffe36e", rx=3, stroke="#e8c030", sw=1.2, rot=8) + coriander(236, 128, rng)
    elif kind == "chettinad":
        out += scatter(rng, 200, 150, 58, 5, lambda x, y, i: R(x - 20, y - 14, 40, 28, "#7a2a10", "#4e1808", 1.8, rx=12, rot=rng.uniform(0, 90)), squash=0.8)
        out += scatter(rng, 200, 150, 78, 22, lambda x, y, i: C(x, y, 2.2, "#14100c"), squash=0.8)
        out += scatter(rng, 200, 150, 72, 8, lambda x, y, i: curry_leaf(x, y, rng.uniform(0, 180), 1.1), squash=0.8)
        out += red_chili(150, 118, 20, 0.9) + red_chili(250, 186, -30, 0.9)
    elif kind == "mutton":
        out += scatter(rng, 200, 150, 60, 5, lambda x, y, i: R(x - 21, y - 15, 42, 30, "#5a2410", "#33140a", 1.8, rx=12, rot=rng.uniform(0, 90)) + R(x - 6, y - 5, 12, 5, "#8a4a26", rx=3, op=0.6), squash=0.85)
        out += scatter(rng, 200, 150, 76, 12, lambda x, y, i: C(x, y, 2, "#e8c070"), squash=0.85) + coriander(210, 150, rng) + red_chili(120, 108, 30, 0.8)
    else:  # egg curry
        for x, y, r in ((165, 140, -10), (232, 160, 15)):
            out += E(x, y, 26, 19, "#fffaf0", "#e6d9b8", 1.5, rot=r) + E(x, y, 11, 8.5, "#f8c820", rot=r)
        out += scatter(rng, 200, 150, 70, 8, lambda x, y, i: C(x, y, 2.6, "#7a2a10", op=0.7), squash=0.8) + coriander(200, 190, rng) + coriander(200, 110, rng)
    return out
