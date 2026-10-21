"""Renderers for mandi/grill, snacks, seafood, rolls, soups, drinks, desserts and Indo-Chinese."""

from __future__ import annotations

import math

from prims import *  # noqa: F401,F403
from food_a import _drumstick


# ── Mandi & grill ───────────────────────────────────────────────────────────
def _chicken_piece(x, y, rot, col, edge, s=1.0, char=False):
    out = (
        E(x, y, 36 * s, 22 * s, col, edge, 1.8, rot=rot)
        + E(x - 6 * s, y - 6 * s, 20 * s, 6 * s, "#ffffff", op=0.22, rot=rot)
    )
    if char:
        for k in range(4):
            out += L(x - 18 * s + k * 12 * s, y - 14 * s, x - 10 * s + k * 12 * s, y + 14 * s, "#3b1a08", 2.4, 0.7)
    return out


def mandi(code, rng, kind="alfaham"):
    out = C(200, 150, 142, "#8a8f96", "#5d6268", 3) + C(200, 150, 132, "#d7dadf", "#b0b5bb", 2)
    if kind in ("alfaham_mandi", "bbq_mandi", "tandoori_mandi"):
        rice = {"alfaham_mandi": "#f4d56a", "bbq_mandi": "#f0c24f", "tandoori_mandi": "#f2cf62"}[kind]
        out += E(200, 150, 110, 82, rice, "#d9ab3a", 1.5)
        out += scatter(rng, 200, 150, 100, 90, lambda x, y, i: E(x, y, 4.4, 1.5, ["#fff3c4", "#f6c545", "#fffde8"][i % 3], rot=rng.uniform(0, 180)), squash=0.74)
        out += scatter(rng, 200, 150, 90, 10, lambda x, y, i: E(x, y, 5, 3, "#7a3a14", rot=rng.uniform(0, 180)), squash=0.74)
        col, edge, char = {"alfaham_mandi": ("#e9a63c", "#b5741a", False), "bbq_mandi": ("#8a3a14", "#5a2208", True), "tandoori_mandi": ("#d9421a", "#9a2208", False)}[kind]
        out += _chicken_piece(158, 138, -18, col, edge, 1.35, char) + _chicken_piece(244, 162, 22, col, edge, 1.35, char)
        out += scatter(rng, 200, 150, 90, 8, lambda x, y, i: E(x, y, 6, 3.4, "#e8c07a", "#c9993a", 1, rot=rng.uniform(0, 180)), squash=0.74)
        if kind == "tandoori_mandi":
            out += scatter(rng, 200, 150, 90, 5, lambda x, y, i: onion_ring(x, y, 10), squash=0.74)
        out += coriander(200, 98, rng) + lemon_wedge(318, 222, 14, -20)
    elif kind == "alfaham_chicken":
        for x, y, r in ((150, 130, -20), (232, 128, 18), (190, 188, 4)):
            out += _chicken_piece(x, y, r, "#d96a2a", "#9a3a10", 1.25, True)
        out += bowl_top(305, 205, 30, "#fff7ea") + E(305, 205, 14, 9, "#ffffff", op=0.9)  # garlic sauce
        out += scatter(rng, 110, 210, 24, 8, lambda x, y, i: C(x, y, 4, "#8bc34a"), squash=0.8) + onion_ring(90, 90, 12) + onion_ring(112, 82, 11) + lemon_wedge(280, 90, 14, 20)
    else:  # grilled chicken (half / full)
        out += E(200, 158, 100, 70, "#c8641e", "#8a3a0e", 2.5)
        out += E(200, 150, 92, 62, "#e0852c")
        for k in range(5):
            out += L(130 + k * 30, 102, 150 + k * 30, 200, "#4a1f08", 4, 0.55)
        out += _drumstick(105, 195, -150, 0.9, "#c8641e") + _drumstick(300, 200, -30, 0.9, "#c8641e")
        out += E(180, 120, 30, 8, "#ffe0a0", op=0.35, rot=-15)
        out += lemon_wedge(312, 100, 15, 20) + onion_ring(96, 100, 12) + coriander(200, 218, rng)
    return out


# ── Snacks – veg ────────────────────────────────────────────────────────────
def snack_veg(code, rng, kind="gobi"):
    if kind == "fries":
        out = shadow(205, 262, 90, 14, 0.25)
        out += P("M130 120 L270 120 L252 268 L148 268 Z", "#d9261c", "#a8180f", 3)
        out += P("M146 120 L254 120 L250 150 L150 150 Z", "#fff1c9", op=0.0)
        for i in range(14):
            x = 142 + i * 9 + rng.uniform(-3, 3)
            out += R(x, 50 + rng.uniform(0, 30), 8, 100 + rng.uniform(0, 14), "#f6c744", rx=2, stroke="#d9a21a", sw=1, rot=rng.uniform(-14, 14))
        out += P("M130 120 L270 120 L252 268 L148 268 Z", "#d9261c", "#a8180f", 3)
        out += R(150, 168, 100, 40, "#fff1c9", rx=6, op=0.9) + T(200, 196, "FRIES", 26, "#d9261c", 900)
        out += shine(160, 190, 10, 56, 0.2, 0)
        out += bowl_top(330, 250, 24, "#d9261c") + C(318, 238, 5, "#ffffff", op=0.4)
        return out
    out = plate_white(200, 150, 140)
    if kind == "gobi":
        out += scatter(rng, 200, 150, 82, 13, lambda x, y, i: C(x, y, 17, "#8a2a14", "#5a1608", 1.5) + E(x - 4, y - 5, 9, 4, "#c8603a", op=0.6) + scatter(rng, x, y, 10, 5, lambda a, b, j: C(a, b, 2.2, "#7a1f0c", op=0.8)), squash=0.8)
        out += scatter(rng, 200, 150, 90, 12, lambda x, y, i: spring_onion(x, y, rng, 2), squash=0.8)
    elif kind == "paneer65":
        out += scatter(rng, 200, 150, 80, 10, lambda x, y, i: R(x - 14, y - 14, 28, 28, "#c8321a", "#8a1a0a", 1.5, rx=5, rot=rng.uniform(0, 60)) + E(x - 3, y - 4, 8, 3, "#f08a6a", op=0.6), squash=0.8)
        out += scatter(rng, 200, 150, 84, 9, lambda x, y, i: curry_leaf(x, y, rng.uniform(0, 180), 1.1), squash=0.8)
        out += green_chili(110, 100, 30, 0.9) + green_chili(290, 205, -20, 0.9) + lemon_wedge(300, 95, 14, 20)
    else:  # chilli paneer
        out += scatter(rng, 200, 150, 78, 9, lambda x, y, i: R(x - 14, y - 14, 28, 28, "#c8641e", "#8a3a0e", 1.5, rx=5, rot=rng.uniform(0, 60)), squash=0.8)
        out += scatter(rng, 200, 150, 84, 10, lambda x, y, i: R(x - 10, y - 8, 20, 16, "#5fae3f", "#3f8f2f", 1.2, rx=3, rot=rng.uniform(0, 90)), squash=0.8)
        out += scatter(rng, 200, 150, 84, 5, lambda x, y, i: onion_ring(x, y, 10), squash=0.8)
        out += green_chili(116, 98, 30, 0.9) + red_chili(285, 205, -20, 0.9)
    return out


def momos(code, rng):
    out = shadow(204, 232, 128, 28, 0.25)
    out += C(200, 150, 128, "#c79a52", "#8a6428", 3) + C(200, 150, 116, "#e3be7a", "#b58a42", 2)
    for r in (100, 74, 48):
        out += C(200, 150, r, "none", "#b58a42", 1.6, 0.6)
    for x, y in ((150, 110), (214, 100), (262, 138), (240, 196), (170, 196), (130, 160)):
        pleats = "".join(L(x, y - 3, x + 13 * math.cos(math.radians(a)), y - 3 + 13 * math.sin(math.radians(a)) * 0.8, "#e4dcc6", 1.4) for a in range(200, 345, 24))
        out += E(x, y + 8, 30, 17, "#d9d2bd") + P(f"M{x - 30:.1f} {y + 8:.1f} Q{x:.1f} {y - 42:.1f} {x + 30:.1f} {y + 8:.1f} Z", "#fffefa", "#e4dcc6", 1.8) + pleats
    out += bowl_top(335, 255, 24, "#d9261c") + C(325, 246, 5, "#ffffff", op=0.35)
    return out


# ── Snacks – chicken ────────────────────────────────────────────────────────
def snack_chicken(code, rng, kind="c65"):
    if kind in ("kebab", "tikka"):
        out = plate_black(200, 150, 142)
        n = 3
        for k in range(n):
            y = 92 + k * 52
            out += L(60, y, 340, y + 6, "#c9ced4", 5)
            for j in range(4 if kind == "kebab" else 5):
                x = 100 + j * 52
                if kind == "kebab":
                    out += R(x - 22, y - 13 + j * 1.2, 44, 26, "#a8481c", "#6a2408", 1.8, rx=12) + L(x - 12, y - 6, x + 12, y + 6, "#e08a4a", 2, 0.5)
                else:
                    col = ["#d9421a", "#5fae3f", "#d9421a", "#e8c040", "#d9421a"][j % 5]
                    out += R(x - 17, y - 14 + j * 1.2, 34, 28, col, "#6a2408", 1.6, rx=6, rot=rng.uniform(-8, 8))
                    if j % 5 == 0 or j % 5 == 2 or j % 5 == 4:
                        out += L(x - 12, y - 8, x + 10, y + 8, "#3b1a08", 2.4, 0.6)
        out += lemon_wedge(330, 245, 14, -20) + onion_ring(75, 245, 11)
        return out
    if kind == "lollipop":
        out = plate_white(200, 150, 142)
        for k, (x, y, r) in enumerate(((140, 96, -30), (240, 88, 20), (118, 176, -70), (268, 172, 35), (196, 214, 10), (196, 140, -5))):
            out += G(
                R(14, -4, 44, 8, "#f6efe0", "#d8cdb4", 1, rx=4)
                + C(60, -4.4, 5, "#f6efe0", "#d8cdb4", 1)
                + C(60, 4.4, 5, "#f6efe0", "#d8cdb4", 1)
                + E(0, 0, 30, 24, "#d9421a", "#8a2208", 2)
                + E(-6, -8, 17, 6, "#f08a6a", op=0.65)
                + E(10, 5, 10, 14, "#e8603a", op=0.5)
                + R(12, -9, 6, 18, "#f6efe0", "#d8cdb4", 1, rx=3),
                f"translate({x} {y}) rotate({r + (0 if k < 3 else 150)}) scale(0.95)",
            )
        out += bowl_top(335, 250, 22, "#d9261c") + lemon_wedge(60, 245, 13, 10)
        return out
    out = plate_white(200, 150, 140)
    base, edge = ("#d9421a", "#8a1e08") if kind == "c65" else ("#c8561e", "#7a2e0a")
    out += scatter(rng, 200, 150, 80, 12, lambda x, y, i: R(x - 15, y - 11, 30, 22, base, edge, 1.6, rx=9, rot=rng.uniform(0, 90)) + E(x - 3, y - 4, 9, 3, "#f08a6a", op=0.55), squash=0.8)
    if kind == "c65":
        out += scatter(rng, 200, 150, 86, 9, lambda x, y, i: curry_leaf(x, y, rng.uniform(0, 180), 1.1), squash=0.8)
        out += green_chili(105, 100, 30, 0.9) + green_chili(300, 210, -20, 0.9) + lemon_wedge(300, 92, 14, 20) + onion_ring(100, 215, 11)
    else:
        out += scatter(rng, 200, 150, 84, 10, lambda x, y, i: R(x - 10, y - 8, 20, 16, "#5fae3f", "#3f8f2f", 1.2, rx=3, rot=rng.uniform(0, 90)), squash=0.8)
        out += scatter(rng, 200, 150, 84, 5, lambda x, y, i: onion_ring(x, y, 10), squash=0.8)
        out += red_chili(110, 98, 30, 0.9) + spring_onion(290, 205, rng, 3)
    return out


# ── Seafood ─────────────────────────────────────────────────────────────────
def _fish(x, y, rot, col, edge, s=1.0):
    return G(
        P("M-60 0 C-40 -26 20 -30 52 -4 L74 -22 L74 22 L52 4 C20 30 -40 26 -60 0 Z", col, edge, 2)
        + C(-38, -4, 3.4, "#2b2b2f") + P("M-26 -16 Q-18 0 -26 16", "none", edge, 2, 0.7)
        + "".join(L(-6 + k * 16, -16, -2 + k * 16, 16, edge, 1.4, 0.45) for k in range(4))
        + E(-6, -12, 30, 5, "#ffffff", op=0.2),
        f"translate({x} {y}) rotate({rot}) scale({s})",
    )


def seafood(code, rng, kind="fish_fry"):
    if kind == "tawa":
        out = shadow(204, 232, 140, 22, 0.28) + C(200, 150, 140, "#26262a", "#121214", 3) + C(200, 150, 124, "#34343a")
        out += R(320, 143, 60, 14, "#26262a", rx=7)
        out += _fish(200, 150, -8, "#b9561f", "#6a2c0c", 1.55)
        out += scatter(rng, 200, 150, 100, 18, lambda x, y, i: C(x, y, 3.4, "#7a2a10", op=0.8), squash=0.7)
        out += scatter(rng, 200, 150, 100, 7, lambda x, y, i: curry_leaf(x, y, rng.uniform(0, 180), 1.0), squash=0.7)
        out += red_chili(100, 220, 30, 0.9) + lemon_wedge(300, 225, 13, 20)
        return out
    out = plate_white(200, 150, 140)
    if kind == "fish_fry":
        out += _fish(190, 150, -10, "#e0963a", "#9a5a14", 1.5)
        out += scatter(rng, 190, 150, 90, 12, lambda x, y, i: C(x, y, 2.6, "#7a3a10", op=0.6), squash=0.6)
        out += lemon_wedge(300, 215, 14, -20) + onion_ring(95, 100, 12) + onion_ring(115, 90, 10) + coriander(300, 90, rng)
    elif kind == "prawns":
        for x, y, r in ((140, 120, -20), (225, 110, 25), (170, 185, 160), (252, 178, 200), (200, 150, 70)):
            out += G(
                P("M-36 6 C-36 -30 16 -38 34 -10 C42 4 30 22 14 16 C22 6 20 -10 6 -12 C-14 -14 -22 4 -22 14 Z", "#e2531f", "#9a2808", 1.8)
                + "".join(L(-24 + k * 10, -8 + k * 0.5, -22 + k * 10, 10, "#9a2808", 1.2, 0.5) for k in range(5))
                + P("M34 -10 l12 -10 l2 14 z", "#c8321a", "#8a1e08", 1),
                f"translate({x} {y}) rotate({r})",
            )
        out += scatter(rng, 200, 150, 90, 8, lambda x, y, i: curry_leaf(x, y, rng.uniform(0, 180), 1.0), squash=0.8) + lemon_wedge(310, 220, 14, -20)
    elif kind == "fingers":
        for k in range(6):
            x, y = 112 + (k % 3) * 70, 105 + (k // 3) * 62
            out += R(x - 30, y - 12, 60, 24, "#e8b04a", "#a8741a", 2, rx=10, rot=-8 + (k % 2) * 10) + E(x - 6, y - 4, 20, 4, "#fff0b8", op=0.55, rot=-8)
        out += bowl_top(325, 232, 26, "#fff0d0") + lemon_wedge(76, 232, 14, 10)
    else:  # golden fried prawns
        for x, y, r in ((135, 115, -15), (215, 100, 15), (150, 185, 170), (240, 175, 195), (190, 145, 75), (285, 120, 40)):
            out += G(
                P("M-36 6 C-36 -30 16 -38 34 -10 C42 4 30 22 14 16 C22 6 20 -10 6 -12 C-14 -14 -22 4 -22 14 Z", "#eeb44a", "#a8741a", 1.8)
                + E(-4, -14, 22, 4, "#fff3c0", op=0.55)
                + P("M34 -10 l12 -10 l2 14 z", "#e2531f", "#9a2808", 1),
                f"translate({x} {y}) rotate({r})",
            )
        out += bowl_top(325, 238, 26, "#d9261c") + lemon_wedge(76, 238, 14, 10)
    return out


# ── Rolls & quick bites ─────────────────────────────────────────────────────
def roll(code, rng, kind="veg"):
    out = plate_white(200, 150, 140)
    fill = {"veg": ["#6fbf4f", "#e8742a", "#fff1c9"], "egg": ["#f7d84a", "#6fbf4f", "#e8742a"], "chicken": ["#c0652a", "#6fbf4f", "#fff1c9"]}.get(kind)
    if kind == "shawarma":
        out += G(
            P("M-118 -34 Q-130 0 -118 34 L118 24 Q132 0 118 -24 Z", "#f1d9a0", "#c9a45a", 2.5)
            + "".join(L(-100 + k * 36, -28, -92 + k * 36, 26, "#d9b46a", 2, 0.6) for k in range(6))
            + E(-118, 0, 10, 34, "#c0652a") + C(-118, -10, 5, "#6fbf4f") + C(-118, 8, 5, "#fff1c9")
            + R(-40, -34, 90, 68, "#e8e2d0", rx=4, op=0.85)
            + L(-40, -34, 50, 34, "#d9261c", 0, 0),
            "translate(205 140) rotate(-12)",
        )
        out += bowl_top(305, 228, 24, "#fff7ea") + E(305, 228, 12, 8, "#ffffff", op=0.9) + onion_ring(78, 230, 11)
        return out
    if kind == "burger":
        out = shadow(200, 252, 120, 14, 0.25)
        out += P("M95 175 L305 175 L292 218 Q200 240 108 218 Z", "#e8b05a", "#a8741a", 2.5)
        out += R(98, 160, 204, 22, "#f6d34a", rx=6, stroke="#d9b414", sw=1.5)
        out += E(200, 156, 108, 12, "#6fbf4f", "#3f8f2f", 1.5) + E(200, 146, 104, 12, "#d9421a", "#8a1e08", 1.5)
        out += R(100, 128, 200, 28, "#c0652a", rx=12, stroke="#7a3a10", sw=2)
        out += P("M92 128 Q92 52 200 46 Q308 52 308 128 Z", "#e8b05a", "#a8741a", 3)
        out += E(200, 70, 80, 20, "#f7cf80", op=0.5) + scatter(rng, 200, 90, 70, 16, lambda x, y, i: E(x, y, 3.4, 1.8, "#fff3d0", rot=rng.uniform(0, 180)), squash=0.45)
        return out
    # wrapped roll
    out += G(
        P("M-100 -30 L100 -30 L100 34 L-100 34 Z", "#f2c230", "#c9a01a", 2, op=0.0)
        + E(0, 4, 112, 36, "#e8c27a", "#b8903a", 2.5)
        + E(0, -2, 108, 28, "#f4d794")
        + "".join(L(-90 + k * 30, -22, -80 + k * 30, 22, "#c8a050", 2, 0.5) for k in range(7))
        + E(-112, 4, 14, 30, "#f6e2a8", "#b8903a", 2)
        + C(-113, -6, 6, fill[0]) + C(-110, 8, 6, fill[1]) + C(-117, 12, 4, fill[2]) + C(-107, -2, 4, "#fff6e0"),
        "translate(205 138) rotate(-14)",
    )
    out += P("M120 160 L300 190 L290 222 L108 190 Z", "#fff6e0", "#e3c98a", 2, 0.95) + L(130, 178, 285, 205, "#d9b46a", 2, 0.6)
    out += onion_ring(80, 100, 11) + lime_wedge(320, 96, 13, 15)
    return out


# ── Soups ───────────────────────────────────────────────────────────────────
def soup(code, rng, kind="tomato"):
    liquid = {"tomato": "#d9421a", "corn": "#f4dc84", "veg_clear": "#f0d98a", "chicken_clear": "#f1dc9a", "manchow": "#7a4a22"}[kind]
    out = C(200, 150, 142, "#f3efe6", "#d9d2c2", 2.5) + shadow(206, 168, 130, 120, 0.18)
    out += C(200, 150, 138, "#ffffff", "#e3ddd3", 2)
    out += bowl_top(190, 150, 100, liquid)
    out += R(250, 60, 120, 14, "#c9ced4", rx=7, rot=38, stroke="#9aa1a9", sw=1.2) + E(300, 134, 20, 12, "#c9ced4", "#9aa1a9", 1.5, rot=38)
    if kind == "tomato":
        out += P("M130 150 q30 -22 60 0 t60 0", "none", "#fff2dc", 6, 0.9) + scatter(rng, 190, 150, 52, 6, lambda x, y, i: R(x - 6, y - 6, 12, 12, "#e8c27a", rx=2, rot=rng.uniform(0, 90)), squash=0.8) + coriander(190, 130, rng)
    elif kind == "corn":
        out += scatter(rng, 190, 150, 62, 34, lambda x, y, i: E(x, y, 5, 3.6, "#f7c81e", "#d9a41a", 0.8, rot=rng.uniform(0, 180)), squash=0.85)
        out += scatter(rng, 190, 150, 56, 7, lambda x, y, i: P(f"M{x - 12:.1f} {y:.1f} q6 -8 12 0 t12 0", "none", "#fff8d8", 3), squash=0.85) + spring_onion(190, 150, rng, 4)
    elif kind == "veg_clear":
        out += scatter(rng, 190, 150, 62, 12, lambda x, y, i: R(x - 4, y - 4, 8, 8, "#e8742a", rx=1.5), squash=0.85) + scatter(rng, 190, 150, 62, 10, lambda x, y, i: C(x, y, 3, "#5fae3f"), squash=0.85)
        out += scatter(rng, 190, 150, 62, 6, lambda x, y, i: R(x - 7, y - 2, 14, 4, "#c8e6a8", rx=2, rot=rng.uniform(0, 180)), squash=0.85)
    elif kind == "chicken_clear":
        out += scatter(rng, 190, 150, 60, 9, lambda x, y, i: R(x - 10, y - 2.5, 20, 5, "#f6e6c8", "#d9c49a", 1, rx=2.5, rot=rng.uniform(0, 180)), squash=0.85)
        out += scatter(rng, 190, 150, 62, 6, lambda x, y, i: R(x - 3, y - 3, 6, 6, "#e8742a", rx=1.5), squash=0.85) + spring_onion(190, 150, rng, 5)
    else:  # manchow
        out += E(190, 156, 44, 30, "#e8b04a", "#b8801a", 1.5)
        out += scatter(rng, 190, 156, 40, 30, lambda x, y, i: P(f"M{x - 8:.1f} {y:.1f} q4 -9 8 0", "none", "#c98a2a", 2.4), squash=0.7)
        out += spring_onion(190, 140, rng, 6) + scatter(rng, 190, 150, 70, 8, lambda x, y, i: R(x - 3, y - 3, 6, 6, "#e8742a", rx=1.5), squash=0.8)
    return out


# ── Drinks ──────────────────────────────────────────────────────────────────
def juice(code, rng, kind="lime"):
    a, b, fruit = {
        "lime": ("#f3f6b0", "#d4e46a", "lime"),
        "orange": ("#ffb84a", "#f08a12", "orange"),
        "watermelon": ("#ff7a8a", "#e8344f", "melon"),
        "mosambi": ("#f7f0a0", "#dfd45a", "mosambi"),
        "mixed": ("#ffa86a", "#d9427a", "mixed"),
    }[kind]
    cx = 200
    out = shadow(cx + 6, 262, 70, 12, 0.25)
    out += tall_glass(cx, 70, 252, 118, 84, a, b, 0.14, "j", extras_inside=bubbles(rng, cx, 90, 240, 80, 10) + (ice_cubes(rng, cx, 100, 200, 70, 4, 0.5) if kind in ("lime", "mosambi") else ""))
    out += straw(cx + 14, 30, cx + 6, 200, "#e4572e" if kind != "lime" else "#2f9e44")
    if fruit == "lime":
        out += lime_wedge(cx + 54, 74, 22, -8)
        out += E(cx - 18, 150, 22, 22, "#d6f08a", "#8fcf3f", 2) + "".join(L(cx - 18, 150, cx - 18 + 19 * math.cos(math.radians(k)), 150 + 19 * math.sin(math.radians(k)), "#8fcf3f", 1.2) for k in range(0, 360, 45))
    elif fruit == "orange":
        out += E(cx + 54, 78, 28, 28, "#f08a12", "#c8600a", 2) + E(cx + 54, 78, 22, 22, "#ffc14a") + "".join(L(cx + 54, 78, cx + 54 + 20 * math.cos(math.radians(k)), 78 + 20 * math.sin(math.radians(k)), "#f08a12", 1.4) for k in range(0, 360, 40))
    elif fruit == "melon":
        out += P(f"M{cx + 30} 82 A30 30 0 0 0 {cx + 90} 82 Z", "#e8344f", "#2f9e44", 4) + P(f"M{cx + 34} 82 A26 26 0 0 0 {cx + 86} 82 Z", "#ff6b7e") + scatter(rng, cx + 60, 90, 16, 5, lambda x, y, i: E(x, y, 2, 3.2, "#2b2b2f"), squash=0.6)
    elif fruit == "mosambi":
        out += E(cx + 54, 78, 28, 28, "#c8d85a", "#8fa22a", 2) + E(cx + 54, 78, 22, 22, "#f2f4a0") + "".join(L(cx + 54, 78, cx + 54 + 20 * math.cos(math.radians(k)), 78 + 20 * math.sin(math.radians(k)), "#d7dd7a", 1.4) for k in range(0, 360, 40))
    else:
        out += C(cx - 54, 86, 11, "#c8102e", "#8a0a1e", 1.5) + P(f"M{cx - 54} 76 q6 -16 18 -18", "none", "#3f7d34", 2.4) + E(cx + 56, 80, 26, 26, "#f08a12", "#c8600a", 2) + E(cx + 56, 80, 20, 20, "#ffc14a") + C(cx + 20, 164, 9, "#8fcf3f", op=0.8) + C(cx - 22, 196, 8, "#ffc14a", op=0.8)
    return out


def shake(code, rng, kind="choco"):
    spec = {
        "choco": ("#8a5a3a", "#5a2e14"),
        "oreo": ("#d9d2c6", "#8a8278"),
        "mango": ("#ffd24a", "#f2a20a"),
        "coffee": ("#b98558", "#6a3c1a"),
        "lassi": ("#fffaf0", "#f0e4c8"),
    }[kind]
    cx = 200
    out = shadow(cx + 6, 266, 70, 12, 0.25)
    if kind == "lassi":
        out += tall_glass(cx, 80, 252, 112, 80, "#fffdf5", "#f3e6c8", 0.1, "l")
        out += E(cx, 88, 44, 9, "#fff6da", "#f0e0b0", 1.5) + scatter(rng, cx, 86, 30, 9, lambda x, y, i: E(x, y, 3.4, 1.8, "#8bc34a", rot=rng.uniform(0, 180)), squash=0.25)
        out += E(cx, 82, 20, 6, "#ffe9a8", op=0.95) + C(cx + 22, 82, 3, "#f0a020")
        out += P(f"M{cx - 50} 120 q50 14 100 0", "none", "#f3e6c8", 3, 0.7) + straw(cx + 30, 34, cx + 18, 180, "#e4572e")
        return out
    out += tall_glass(cx, 76, 252, 118, 86, spec[0], spec[1], 0.16, "s")
    if kind == "choco":
        out += "".join(P(f"M{cx - 54 + k * 24} 96 q2 28 6 40 q4 -10 8 -40", "#3a1c0a", "#3a1c0a", 4, 0.85) for k in range(5))
        out += whipped_cream(cx, 62, 80) + E(cx - 2, 50, 6, 4, "#3a1c0a") + straw(cx + 30, 26, cx + 16, 170, "#e4572e")
    elif kind == "oreo":
        out += scatter(rng, cx, 130, 38, 14, lambda x, y, i: C(x, y, 3.2, "#2b2b2f", op=0.9), squash=2.2)
        out += whipped_cream(cx, 62, 80) + C(cx + 24, 40, 15, "#2b2b2f", "#14100c", 1.5) + C(cx + 24, 40, 8, "#f4efe6") + straw(cx - 30, 30, cx - 18, 170, "#2f7fe4")
    elif kind == "mango":
        out += scatter(rng, cx, 160, 40, 6, lambda x, y, i: R(x - 7, y - 7, 14, 14, "#ffb81a", rx=3, op=0.55, rot=rng.uniform(0, 90)), squash=1.8)
        out += P(f"M{cx + 30} 76 q24 -34 54 -4 q-20 26 -54 4 Z", "#ffb81a", "#d98a0a", 2) + straw(cx - 20, 26, cx - 8, 170, "#2f9e44")
    else:  # cold coffee
        out += E(cx, 98, 48, 9, "#f3dcc0", op=0.9) + whipped_cream(cx, 66, 76) + "".join(P(f"M{cx - 20 + k * 14} 54 l4 -8", "none", "#5a2e14", 3) for k in range(3))
        out += ice_cubes(rng, cx, 120, 220, 60, 3, 0.35) + straw(cx + 30, 26, cx + 16, 170, "#2b2b2f")
    out += shine(cx - 34, 154, 5, 60, 0.4, 4)
    return out


def can_drink(code, rng, kind="sprite"):
    # Generic cans & clear glasses – plain colour coding, no brand marks.
    spec = {
        "sprite": ("#2f9e44", "#1a6b2a", "#eaf7ee", "SPRITE", "#dff6e6", "#c8efd2"),
        "cola": ("#d9261c", "#9a140c", "#ffffff", "COLA", "#5a2e14", "#2b1408"),
        "thums": ("#1f1f24", "#0c0c0e", "#f4b400", "THUMS UP", "#4a2410", "#1f0f06"),
    }[kind]
    can, edge, txt, label, la, lb = spec
    out = shadow(250, 262, 90, 12, 0.25)
    # can
    out += R(212, 92, 76, 160, can, rx=12, stroke=edge, sw=2.5) + E(250, 92, 38, 8, "#c9ced4", "#9aa1a9", 2) + E(250, 92, 30, 5, "#aeb4bb")
    out += R(212, 128, 76, 54, edge, op=0.35) + T(250, 163, label, 15 if len(label) < 7 else 12, txt, 900)
    out += R(222, 100, 8, 146, "#ffffff", rx=4, op=0.25)
    # glass
    out += tall_glass(130, 110, 252, 100, 74, la, lb, 0.12, "d", extras_inside=bubbles(rng, 130, 130, 240, 60, 14) + ice_cubes(rng, 130, 130, 210, 56, 3, 0.45))
    if kind == "sprite":
        out += lime_wedge(176, 112, 20, -20) + straw(146, 66, 138, 200, "#2f9e44")
    elif kind == "cola":
        out += straw(146, 66, 138, 200, "#e4572e") + lemon_wedge(176, 112, 18, -20)
    else:
        out += straw(146, 66, 138, 200, "#f4b400") + lemon_wedge(176, 112, 18, -20)
    return out


def hot_drink(code, rng, kind="tea"):
    col = {"tea": ("#c98a4a", "#a8662a"), "coffee": ("#5a2e14", "#3a1c0a")}[kind]
    out = shadow(200, 232, 130, 22, 0.28) + E(200, 214, 124, 30, "#ffffff", "#d9d2c2", 2.5) + E(200, 210, 96, 20, "#f4f0e6", "#e3ddd3", 1.5)
    out += P("M268 150 q50 -6 40 34 q-8 26 -44 18", "none", "#ffffff", 14) + P("M268 150 q50 -6 40 34 q-8 26 -44 18", "none", "#d9d2c2", 2.5)
    out += P("M118 120 L282 120 Q282 214 200 218 Q118 214 118 120 Z", "#ffffff", "#d9d2c2", 2.5)
    out += E(200, 120, 82, 17, "#ffffff", "#d9d2c2", 2.5) + E(200, 122, 74, 13, col[0])
    out += E(200, 124, 52, 7, col[1], op=0.55)
    if kind == "coffee":
        out += E(200, 122, 40, 8, "#e0c09a", op=0.85) + P("M170 122 q14 -9 30 0 q14 9 30 0", "none", "#5a2e14", 3, 0.9)
        out += E(126, 236, 8, 5, "#4a2410", rot=20) + E(146, 242, 8, 5, "#4a2410", rot=-10)
    else:
        out += E(176, 118, 14, 3.6, "#e0a860", op=0.8)
    out += shine(150, 160, 7, 34, 0.5, 8) + steam(200, 96, 3)
    return out


# ── Desserts ────────────────────────────────────────────────────────────────
def dessert(code, rng, kind="vanilla"):
    cx = 200
    if kind in ("vanilla", "chocolate"):
        c1, c2 = ("#fff1c9", "#e8d49a") if kind == "vanilla" else ("#6a3a1e", "#3e1c0a")
        out = shadow(cx + 4, 262, 96, 14, 0.25)
        out += P("M120 160 L280 160 L262 236 Q200 252 138 236 Z", "#e8ebef", "#aeb4bb", 2.5)
        out += E(200, 236, 66, 12, "#c9ced4", op=0.0) + R(172, 238, 56, 14, "#c9ced4", rx=4, stroke="#9aa1a9", sw=1.5) + E(200, 256, 56, 9, "#c9ced4", "#9aa1a9", 1.5)
        out += soft_scoop(165, 140, 48, c1, c2) + soft_scoop(238, 142, 46, c1, c2)
        out += E(200, 160, 82, 10, "#ffffff", "#aeb4bb", 2, op=0.0)
        if kind == "vanilla":
            out += scatter(rng, 200, 134, 66, 10, lambda x, y, i: C(x, y, 1.6, "#8a6a3a", op=0.7), squash=0.6) + R(244, 62, 22, 70, "#e8c27a", rx=3, stroke="#c99a52", sw=1.5, rot=18) + "".join(L(236 + k * 4, 70 + k * 12, 262 + k * 4, 62 + k * 12, "#c99a52", 1.2) for k in range(4))
        else:
            out += "".join(P(f"M{135 + k * 26} 140 q2 24 8 34", "none", "#2a1206", 5, 0.8) for k in range(5)) + C(165, 92, 7, "#c8102e", "#8a0a1e", 1) + R(244, 62, 22, 70, "#e8c27a", rx=3, stroke="#c99a52", sw=1.5, rot=18)
        return out
    if kind == "brownie":
        out = plate_white(200, 150, 142)
        out += R(100, 104, 126, 100, "#4a2410", rx=10, stroke="#2a1206", sw=2.5, rot=-6) + R(106, 110, 114, 40, "#6a3a1e", rx=8, rot=-6)
        out += scatter(rng, 160, 150, 46, 10, lambda x, y, i: R(x - 5, y - 5, 10, 10, "#8a5a3a", rx=2, rot=rng.uniform(0, 90)), squash=0.8)
        out += soft_scoop(242, 140, 46, "#fff1c9", "#e8d49a")
        out += "".join(P(f"M{110 + k * 24} 120 q8 30 4 52", "none", "#2a1206", 5, 0.85) for k in range(5)) + E(240, 150, 56, 12, "#3a1c0a", op=0.0)
        out += C(246, 100, 7, "#c8102e", "#8a0a1e", 1) + scatter(rng, 260, 190, 30, 8, lambda x, y, i: C(x, y, 2, "#6a3a1e"), squash=0.4)
        return out
    if kind == "jamun":
        out = bowl_top(200, 150, 138, "#e8a23a")
        out += E(200, 150, 100, 78, "#f0b24a", "#c8821a", 1.5) + shine(160, 100, 40, 10, 0.5)
        for x, y in ((170, 140), (232, 152)):
            out += C(x, y + 3, 44, "#2a0e06", op=0.35) + C(x, y, 44, "#6a2410", "#3e1608", 2) + E(x - 12, y - 14, 18, 8, "#b86a3a", op=0.7, rot=-30)
        out += scatter(rng, 200, 150, 90, 14, lambda x, y, i: E(x, y, 4, 2.2, "#8bc34a", rot=rng.uniform(0, 180)), squash=0.75, inner=0.55)
        out += scatter(rng, 200, 150, 90, 6, lambda x, y, i: C(x, y, 2.4, "#f4efe0"), squash=0.75, inner=0.6)
        return out
    # falooda
    cx = 200
    out = shadow(cx + 6, 268, 66, 11, 0.25)
    out += tall_glass(cx, 70, 248, 108, 72, "#ffb6c8", "#e8527a", 0.1, "f", extras_inside=(
        R(cx - 60, 150, 120, 22, "#ffffff", op=0.55) + R(cx - 56, 120, 112, 22, "#e8527a", op=0.55)
        + scatter(rng, cx, 196, 40, 12, lambda x, y, i: R(x - 7, y - 2, 14, 4, ["#ffffff", "#d9427a", "#8fcf3f"][i % 3], rx=2, rot=rng.uniform(0, 90), op=0.9), squash=0.9)
        + R(cx - 60, 220, 120, 26, "#f4e6c4", op=0.65)))
    out += soft_scoop(cx, 56, 42, "#fff1c9", "#e8d49a") + scatter(rng, cx, 38, 28, 12, lambda x, y, i: R(x - 3, y - 3, 6, 6, "#b2d98a" if i % 2 else "#e8c27a", rx=1.5, rot=rng.uniform(0, 90)), squash=0.6) + C(cx + 16, 30, 6, "#c8102e", "#8a0a1e", 1)
    out += straw(cx + 36, 18, cx + 22, 200, "#e4572e")
    return out


# ── Indo-Chinese ────────────────────────────────────────────────────────────
def chinese(code, rng, kind="noodles"):
    if kind == "noodles":
        out = plate_white(200, 150, 142)
        for k in range(16):
            a = rng.uniform(0, 360)
            out += P(f"M{200 + 70 * math.cos(math.radians(a)):.1f} {150 + 52 * math.sin(math.radians(a)):.1f} q{rng.uniform(-40, 40):.1f} {rng.uniform(-30, 30):.1f} {rng.uniform(-90, 90):.1f} {rng.uniform(-60, 60):.1f}", "none", "#e8c060", 5, 0.95)
        out += E(200, 150, 70, 48, "none", "#e8c060", 5, 0.8)
        out += scatter(rng, 200, 150, 70, 16, lambda x, y, i: R(x - 10, y - 2, 20, 4, ["#e8742a", "#5fae3f", "#d9d2b0"][i % 3], rx=2, rot=rng.uniform(0, 180)), squash=0.75)
        out += scatter(rng, 200, 150, 66, 7, lambda x, y, i: R(x - 7, y - 5, 14, 10, "#c0793a", rx=3, rot=rng.uniform(0, 90)), squash=0.75) + spring_onion(200, 150, rng, 8)
        out += L(300, 74, 350, 124, "#7a4a22", 4) + L(312, 68, 360, 116, "#7a4a22", 4)
        return out
    out = plate_black(200, 150, 142)
    out += scatter(rng, 200, 150, 82, 11, lambda x, y, i: C(x, y, 19, "#5a1c0a", "#33100a", 1.5) + E(x - 5, y - 6, 9, 4, "#c8603a", op=0.55), squash=0.8)
    out += scatter(rng, 200, 150, 88, 10, lambda x, y, i: R(x - 10, y - 8, 20, 16, "#5fae3f", "#3f8f2f", 1.2, rx=3, rot=rng.uniform(0, 90)), squash=0.8)
    out += scatter(rng, 200, 150, 88, 12, lambda x, y, i: spring_onion(x, y, rng, 2), squash=0.8) + red_chili(96, 100, 30, 0.9)
    return out
