#!/usr/bin/env python3
"""Generate abstract_cover.png — Deep blue bloom for cover backgrounds.

Run from any directory:
    python assets/generate_abstract.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
from pathlib import Path

OUT = Path(__file__).parent / "abstract_cover.png"

rng = np.random.default_rng(7)

FIG_W, FIG_H = 8.27, 11.69  # A4 portrait inches
DPI = 150

fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor="#020c1a")
ax = fig.add_axes([0, 0, 1, 1])

aspect = FIG_H / FIG_W
ax.set_xlim(-1, 1)
ax.set_ylim(-aspect, aspect)
ax.axis("off")
ax.set_facecolor("#020c1a")

CX, CY = 0.0, 0.08  # bloom center, slightly above mid

# ── Outer atmosphere — diffuse blue glow ─────────────────────────────────────
for r, c, alpha in [
    (1.6, "#002147", 0.18),
    (1.2, "#003070", 0.22),
    (0.90, "#004a9e", 0.28),
]:
    ax.add_patch(Circle((CX, CY), r, facecolor=c, edgecolor="none",
                         alpha=alpha, zorder=1))

# ── Petal layers — (n, rot_offset°, reach, ell_w, ell_h, colors, alpha) ──────
# Deep blue palette: deep navy → royal blue → bright cerulean → pale sky + gold
layers = [
    # outermost — deep navy, visible against the dark bg
    ( 6,  0.0, 0.90, 0.52, 1.00, ["#002c6e", "#003a8a"], 0.55),
    ( 6, 30.0, 0.85, 0.48, 0.95, ["#003a8a", "#0048a4"], 0.50),
    # mid — royal blue
    ( 8,  0.0, 0.76, 0.40, 0.88, ["#0058c0", "#0068d8"], 0.58),
    ( 8, 22.5, 0.70, 0.36, 0.82, ["#1070e0", "#2080f0"], 0.55),
    # inner — bright cerulean
    (10,  0.0, 0.58, 0.29, 0.72, ["#3090f8", "#40a4ff"], 0.62),
    (10, 18.0, 0.52, 0.25, 0.66, ["#50b0ff", "#68c0ff"], 0.60),
    # innermost — pale sky
    (12,  0.0, 0.40, 0.19, 0.54, ["#88d0ff", "#a8e0ff"], 0.68),
    (12, 15.0, 0.36, 0.16, 0.48, ["#b8e8ff", "#d0f0ff"], 0.65),
    (16,  0.0, 0.25, 0.11, 0.36, ["#dff4ff", "#eef8ff"], 0.72),
    # innermost — gold-tipped highlights
    ( 8,  0.0, 0.14, 0.14, 0.22, ["#f0d060", "#fce890"], 0.78),
    ( 8, 22.5, 0.12, 0.12, 0.18, ["#ffffff", "#fffbe8"], 0.70),
]

for n, rot, reach, ew, eh, colors, alpha in layers:
    for i in range(n):
        ang_deg = rot + i * 360.0 / n
        ang_rad = np.radians(ang_deg)
        ex = CX + np.cos(ang_rad) * reach * 0.52
        ey = CY + np.sin(ang_rad) * reach * 0.52
        color = colors[i % len(colors)]
        ax.add_patch(Ellipse(
            (ex, ey), width=ew, height=eh,
            angle=ang_deg - 90,
            facecolor=color, edgecolor="none",
            alpha=alpha, zorder=2,
        ))

# ── Stamen filaments ──────────────────────────────────────────────────────────
for _ in range(80):
    ang = rng.uniform(0, 2 * np.pi)
    r0  = rng.uniform(0.0, 0.04)
    r1  = rng.uniform(0.08, 0.22)
    ax.plot(
        [CX + np.cos(ang) * r0, CX + np.cos(ang) * r1],
        [CY + np.sin(ang) * r0, CY + np.sin(ang) * r1],
        color="#c8e8ff",
        linewidth=rng.uniform(0.3, 0.9),
        alpha=rng.uniform(0.30, 0.65),
        zorder=3,
    )

# ── Glow rings ────────────────────────────────────────────────────────────────
for r, c, a in [
    (0.30, "#0040a0", 0.30),
    (0.22, "#1068d8", 0.40),
    (0.15, "#40a0ff", 0.55),
    (0.08, "#90d0ff", 0.65),
    (0.04, "#e8c040", 0.75),  # gold centre glow
    (0.02, "#ffffff", 0.90),
]:
    ax.add_patch(Circle((CX, CY), r, facecolor=c, edgecolor="none", alpha=a, zorder=4))

# ── Pollen specks ─────────────────────────────────────────────────────────────
for _ in range(60):
    ang  = rng.uniform(0, 2 * np.pi)
    dist = rng.uniform(0.0, 0.08)
    ax.plot(
        CX + np.cos(ang) * dist,
        CY + np.sin(ang) * dist,
        "o",
        color="#ffe880",
        markersize=rng.uniform(0.4, 2.2),
        alpha=rng.uniform(0.55, 0.95),
        zorder=5,
    )

fig.savefig(str(OUT), dpi=DPI, bbox_inches=None, pad_inches=0, facecolor="#020c1a")
print(f"Written: {OUT}")
