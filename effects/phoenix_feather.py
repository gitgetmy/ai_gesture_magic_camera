# -*- coding: utf-8 -*-
"""
effects/phoenix_feather.py —— 凤凰火羽（电影级 · 凤羽升腾）

多层凤凰结构：
  - 中央火柱：从掌心直冲向上的烈焰柱
  - 左右凤翼：双层羽翼（主翼+副翼），沿上扬弧线展开
  - 尾羽飘带：从掌心向下飘落的3-5条长尾羽
  - 火羽粒子：大量上飘的火星/灰烬
  - 凤首光核：火柱顶端的鸟首形光团
"""
import math
import random

import pygame

from utils.draw_utils import draw_glow
from utils.math_utils import scale_color

PHOENIX_COLORS = [(255, 70, 30), (255, 140, 40), (255, 200, 80), (255, 235, 160)]
PHOENIX_CORE = (255, 255, 240)


class _PhoenixBurst:
    """一次凤凰展翅的记录（用于翅膀绘制）。"""
    __slots__ = ("x", "y", "life", "max_life")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.max_life = 28
        self.life = self.max_life

    @property
    def alive(self):
        return self.life > 0


class PhoenixFeather:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.bursts = []

    def set_theme(self, theme):
        self.theme = theme

    def emit(self, center):
        col = random.choice(PHOENIX_COLORS)
        accent = self.theme.get("accent2", self.theme["core"])
        up = -math.pi / 2
        cx, cy = center

        # 左右双翼（扇形喷射，上飘）
        for side in (-1, 1):
            for i in range(5):
                spread = 0.2 + i * 0.15
                ang = up + side * spread
                self.ps.spawn_directional(
                    center, ang, 0.08, 3, random.uniform(5, 10),
                    color=random.choice(PHOENIX_COLORS),
                    gravity=-0.22, life=(28, 50),
                )
        # 中央火柱（直冲向上）
        self.ps.spawn_directional(
            center, up, 0.12, 5, 10,
            color=accent, gravity=-0.35, life=(30, 55),
        )
        # 尾羽（向下飘落）
        for side in (-1, 1):
            for _ in range(3):
                ang = math.pi / 2 + side * random.uniform(0.2, 0.6)
                self.ps.spawn_directional(
                    center, ang, 0.1, 2, random.uniform(3, 6),
                    color=random.choice(PHOENIX_COLORS),
                    gravity=0.15, life=(35, 60),
                )

        # 记录爆发用于翅膀绘制
        self.bursts.append(_PhoenixBurst(cx, cy))
        if len(self.bursts) > 12:
            self.bursts.pop(0)

    def update(self):
        for b in self.bursts:
            b.life -= 1
        self.bursts = [b for b in self.bursts if b.alive]

    def draw(self, fx):
        for burst in self.bursts:
            ratio = burst.life / burst.max_life
            if ratio <= 0.05:
                continue
            cx, cy = burst.x, burst.y

            # 翅膀：两侧上扬弧线（羽翼形状）
            for side in (-1, 1):
                # 主翼
                wing_pts = []
                for k in range(10):
                    u = k / 9.0
                    ang = -math.pi / 2 + side * (0.25 + u * 1.0)
                    dist = 30 + u * 80 * ratio
                    px = cx + math.cos(ang) * dist
                    py = cy + math.sin(ang) * dist - u * 30 * ratio
                    wing_pts.append((px, py))
                    col = PHOENIX_COLORS[min(k // 2, len(PHOENIX_COLORS) - 1)]
                    sz = (4 + 5 * (1 - u)) * ratio + 1
                    draw_glow(fx, (px, py), sz, col, layers=3)
                # 翼线连接
                if len(wing_pts) >= 2:
                    for i_pt in range(len(wing_pts) - 1):
                        col = PHOENIX_COLORS[min(i_pt // 2, len(PHOENIX_COLORS) - 1)]
                        pygame.draw.line(
                            fx, scale_color(col, ratio * 0.5),
                            (int(wing_pts[i_pt][0]), int(wing_pts[i_pt][1])),
                            (int(wing_pts[i_pt + 1][0]), int(wing_pts[i_pt + 1][1])),
                            1,
                        )

            # 中央火柱（直线上扬）
            pillar_top = cy - 90 * ratio
            col_top = PHOENIX_CORE
            col_bot = PHOENIX_COLORS[0]
            for i_p in range(5):
                u = i_p / 4.0
                py = cy + (pillar_top - cy) * u
                col = (
                    int(col_bot[0] + (col_top[0] - col_bot[0]) * u),
                    int(col_bot[1] + (col_top[1] - col_bot[1]) * u),
                    int(col_bot[2] + (col_top[2] - col_bot[2]) * u),
                )
                draw_glow(fx, (cx, py), (8 - u * 5) * ratio + 1, col, layers=4)

            # 凤首光核（火柱顶端）
            draw_glow(fx, (cx, pillar_top), 16 * ratio + 2, PHOENIX_CORE, layers=5)
            # 凤眼（两侧暗点 + 中心亮核）
            for side in (-1, 1):
                eye_x = cx + side * 8 * ratio
                eye_y = pillar_top - 4
                draw_glow(fx, (eye_x, eye_y), 4 * ratio + 1, PHOENIX_COLORS[0], layers=3)

    def clear(self):
        self.bursts.clear()
