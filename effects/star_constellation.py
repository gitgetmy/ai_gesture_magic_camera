# -*- coding: utf-8 -*-
"""
effects/star_constellation.py —— 星宿阵图（电影级 · 星河入掌）

电影级星图结构：
  - 北斗七星：大星点 + 十字星芒 + 连线
  - 辅星群：在七星周围散布小星
  - 星云底光：柔和的蓝紫渐变底光（加色层圆盘）
  - 星光粒子：从星点飘落的小型星屑
  - 外围星环：两层旋转星环（快慢不同）
"""
import math
import random

import pygame

from utils.draw_utils import draw_glow, draw_ring
from utils.math_utils import scale_color

BIG_DIPPER = [
    (-0.95, 0.35), (-0.55, 0.45), (-0.15, 0.40), (0.15, 0.20),
    (0.45, 0.30), (0.55, -0.10), (0.95, -0.30),
]
# 辅星（在七星周围）
COMPANION_STARS = [
    (-0.75, 0.05), (-0.35, 0.15), (0.0, 0.55), (0.3, 0.0),
    (0.6, 0.1), (-0.55, 0.6), (0.1, -0.25), (0.7, -0.15),
    (-0.2, 0.7), (-0.8, 0.5), (0.4, -0.4),
]


class StarConstellation:
    def __init__(self, particle_system, theme, base_radius=180):
        self.ps = particle_system
        self.theme = theme
        self.base_radius = base_radius
        self.scale = 0.0
        self.center = (0, 0)
        self.rotation = 0.0
        self.phase = 0.0

    def set_theme(self, theme):
        self.theme = theme

    def update(self, center=None):
        self.rotation += 0.008
        self.phase += 0.12
        if center is not None:
            self.center = center
            self.scale += (1.0 - self.scale) * 0.1
            if self.scale > 0.4:
                self.ps.spawn_trail(center, velocity=0.3)
        else:
            self.scale += (0.0 - self.scale) * 0.08
            if self.scale < 0.02:
                self.scale = 0.0

    @property
    def visible(self):
        return self.scale >= 0.02

    def _transform(self, sx, sy):
        cx, cy = self.center
        R = self.base_radius * self.scale
        cos_r, sin_r = math.cos(self.rotation), math.sin(self.rotation)
        rx = sx * cos_r - sy * sin_r
        ry = sx * sin_r + sy * cos_r
        return (cx + rx * R, cy + ry * R)

    def draw(self, fx):
        if not self.visible:
            return
        core = self.theme["core"]
        pal = self.theme.get("spectrum", self.theme["palette"])
        accent = self.theme.get("accent", core)
        cx, cy = self.center
        R = self.base_radius * self.scale

        # ---- 星云底光（柔和的扩散辉光） ----
        # 用多圈不同半径/颜色的超柔辉光模拟星云
        nebula_colors = [
            scale_color(accent, 0.12),
            scale_color(pal[1 % len(pal)], 0.08),
            scale_color(pal[2 % len(pal)], 0.06),
        ]
        for i, nc in enumerate(nebula_colors):
            rr = R * (0.6 + i * 0.25)
            draw_glow(fx, self.center, rr, nc, layers=8)

        # ---- 七星连线 ----
        pts = [self._transform(sx, sy) for (sx, sy) in BIG_DIPPER]
        for i in range(len(pts) - 1):
            # 宽辉光线
            pygame.draw.line(fx, scale_color(accent, 0.3), pts[i], pts[i + 1], 3)
            # 主线
            pygame.draw.line(fx, scale_color(core, 0.7), pts[i], pts[i + 1], 1)

        # ---- 七星（大星点 + 十字星芒） ----
        for i, p in enumerate(pts):
            twinkle = 0.65 + 0.35 * math.sin(self.phase + i * 1.3)
            col = pal[i % len(pal)]
            sz = (7 + 3 * math.sin(self.phase + i)) * self.scale * twinkle + 2
            # 星芒（十字线）
            flare_len = sz * 2.5
            for ang in (0, math.pi / 2):
                fx_x1 = p[0] + math.cos(ang) * flare_len
                fy_y1 = p[1] + math.sin(ang) * flare_len
                fx_x2 = p[0] - math.cos(ang) * flare_len
                fy_y2 = p[1] - math.sin(ang) * flare_len
                pygame.draw.line(fx, scale_color(col, 0.4 * twinkle),
                                 (int(fx_x1), int(fy_y1)),
                                 (int(fx_x2), int(fy_y2)), 1)
            # 对角星芒
            for ang in (math.pi / 4, -math.pi / 4):
                dl = flare_len * 0.6
                fx_x1 = p[0] + math.cos(ang) * dl
                fy_y1 = p[1] + math.sin(ang) * dl
                fx_x2 = p[0] - math.cos(ang) * dl
                fy_y2 = p[1] - math.sin(ang) * dl
                pygame.draw.line(fx, scale_color(col, 0.2 * twinkle),
                                 (int(fx_x1), int(fy_y1)),
                                 (int(fx_x2), int(fy_y2)), 1)
            # 星点辉光
            draw_glow(fx, p, sz, col, layers=5)
            draw_glow(fx, p, sz * 0.35, (255, 255, 255), layers=3)

        # ---- 辅星（小星点，微闪） ----
        for i, (sx, sy) in enumerate(COMPANION_STARS):
            p = self._transform(sx, sy)
            twinkle = 0.5 + 0.5 * math.sin(self.phase * 1.5 + i * 2.1)
            col = pal[(i + 3) % len(pal)]
            sz = 2.5 * self.scale * twinkle + 0.5
            draw_glow(fx, p, sz, col, layers=3)

        # ---- 外围星环（双层，快慢不同） ----
        for layer, (rm, alpha, spd) in enumerate(((1.15, 0.4, 1.0), (0.92, 0.25, -0.7))):
            dots = 32
            for i in range(dots):
                a = self.rotation * spd + i * math.tau / dots
                px = cx + math.cos(a) * R * rm
                py = cy + math.sin(a) * R * rm
                twinkle = 0.6 + 0.4 * math.sin(self.phase * 0.7 + i)
                draw_glow(fx, (px, py), 2 * self.scale * twinkle + 1,
                          pal[i % len(pal)], layers=3)

        # 外环线
        draw_ring(fx, self.center, R * 1.15, core,
                  thickness=1, alpha=0.25 * self.scale)

    def clear(self):
        pass
