# -*- coding: utf-8 -*-
"""
effects/lotus_bloom.py —— 莲花绽放（电影级 · 掌中生莲）

多层莲花结构：
  - 外层花瓣：8片大花瓣先展开，向外弯曲
  - 内层花瓣：8片小花瓣交错后开，向内微卷
  - 花心：金色光核 + 花粉粒子上升
  - 水波纹：莲花底部扩散的涟漪光环
  - 佛光：花瓣完全展开后短暂的放射柔光
"""
import math
import random

import pygame

from utils.draw_utils import draw_glow
from utils.math_utils import scale_color

LOTUS_COLORS = [(255, 220, 130), (255, 180, 200), (245, 245, 255)]
LOTUS_CORE = (255, 235, 160)


class _Lotus:
    __slots__ = ("x", "y", "progress", "life", "max_life",
                 "radius", "ring_r", "pollen_timer")

    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.progress = 0.0
        self.max_life = 100
        self.life = self.max_life
        self.ring_r = 0.0
        self.pollen_timer = 0

    @property
    def alive(self):
        return self.life > 0

    def update(self):
        self.progress = min(1.0, self.progress + 0.03)
        if self.progress >= 1.0:
            self.ring_r += 7
        self.life -= 1
        self.pollen_timer += 1


class LotusBloom:
    def __init__(self, theme):
        self.theme = theme
        self.flowers = []

    def set_theme(self, theme):
        self.theme = theme

    def trigger(self, center, radius=80):
        if len(self.flowers) < 4:
            self.flowers.append(_Lotus(center[0], center[1], radius))

    def update(self):
        for f in self.flowers:
            f.update()
        self.flowers = [f for f in self.flowers if f.alive]

    def draw(self, fx):
        for f in self.flowers:
            life_r = f.life / f.max_life
            cx, cy = f.x, f.y
            petals = 8
            R = f.radius * f.progress
            openness = f.progress

            # 外层花瓣（大，先展开）
            for i in range(petals):
                a_base = i * math.tau / petals
                # 花瓣从中心向外伸展，带弯曲
                tip_dist = R * 1.0
                mid_dist = R * 0.45
                # 微微向外弯曲
                bend = math.sin(i * 1.2) * 0.25
                a_mid = a_base + bend * openness
                a_tip = a_base + bend * 1.6 * openness

                mid_x = cx + math.cos(a_mid) * mid_dist
                mid_y = cy + math.sin(a_mid) * mid_dist
                tip_x = cx + math.cos(a_tip) * tip_dist
                tip_y = cy + math.sin(a_tip) * tip_dist

                col = LOTUS_COLORS[0]
                col = scale_color(col, life_r * openness)
                # 花瓣：用两点辉光 + 连线
                draw_glow(fx, (tip_x, tip_y), 6 * openness + 1, col, layers=4)
                draw_glow(fx, (mid_x, mid_y), 4 * openness + 1, col, layers=3)
                if openness > 0.3:
                    pygame.draw.line(fx, scale_color(col, 0.6),
                                     (int(mid_x), int(mid_y)),
                                     (int(tip_x), int(tip_y)), 1)

            # 内层花瓣（小，错开，后展开）
            inner_open = max(0, (openness - 0.25) / 0.75)
            for i in range(petals):
                a_base = math.pi / petals + i * math.tau / petals
                tip_dist = R * 0.55 * inner_open
                mid_dist = R * 0.25 * inner_open

                tip_x = cx + math.cos(a_base) * tip_dist
                tip_y = cy + math.sin(a_base) * tip_dist
                mid_x = cx + math.cos(a_base) * mid_dist
                mid_y = cy + math.sin(a_base) * mid_dist

                col = LOTUS_COLORS[1]
                col = scale_color(col, life_r * inner_open)
                draw_glow(fx, (tip_x, tip_y), 4 * inner_open + 1, col, layers=3)

            # 花心（金色光核）
            core_glow = scale_color(LOTUS_CORE, life_r)
            draw_glow(fx, (cx, cy), 10 * openness + 3, core_glow, layers=5)
            draw_glow(fx, (cx, cy), 4 * openness + 1,
                      (255, 255, 255), layers=4)

            # 花粉粒子（从花心飘出）
            if openness > 0.5 and f.pollen_timer % 6 == 0:
                for _ in range(2):
                    a = random.uniform(0, math.tau)
                    d = random.uniform(5, 18)
                    px = cx + math.cos(a) * d
                    py = cy + math.sin(a) * d - random.uniform(0, 15)
                    draw_glow(fx, (px, py), 2,
                              random.choice(LOTUS_COLORS), layers=2)

            # 水波纹（扩散光环）
            if f.ring_r > 1:
                ring_ratio = max(0, 1 - f.ring_r / 250)
                if ring_ratio > 0:
                    pygame.draw.circle(
                        fx, scale_color(self.theme["core"], ring_ratio * 0.7),
                        (int(cx), int(cy)), int(f.ring_r),
                        max(1, int(5 * ring_ratio)),
                    )
                    # 第二圈
                    r2 = f.ring_r * 0.65
                    if r2 > 2:
                        pygame.draw.circle(
                            fx, scale_color(self.theme["accent"], ring_ratio * 0.5),
                            (int(cx), int(cy)), int(r2),
                            max(1, int(3 * ring_ratio)),
                        )

    def clear(self):
        self.flowers.clear()
