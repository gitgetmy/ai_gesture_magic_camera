# -*- coding: utf-8 -*-
"""
effects/shockwave.py —— 冲击波特效（电影级）

电影级冲击波结构：
  - 白热主环（快速膨胀，逐渐变宽变暗）
  - 彩色外环（略慢，带粒子拖尾）
  - 粒子环：冲击波前沿带动一圈粒子
  - 内回响环：延迟的内圈二次波
  - 地面裂纹感：从中心向外辐射的短促亮线
"""
import math
import random

import pygame

import config
from utils.draw_utils import draw_ring, draw_glow, draw_beams
from utils.math_utils import scale_color


class _Wave:
    __slots__ = ("x", "y", "radius", "color", "alive", "particle_timer")

    def __init__(self, x, y, color, start_radius=4):
        self.x = x
        self.y = y
        self.radius = start_radius
        self.color = color
        self.alive = True
        self.particle_timer = 0

    def update(self):
        self.radius += config.SHOCKWAVE_SPEED
        self.particle_timer += 1
        if self.radius > config.SHOCKWAVE_MAX_RADIUS:
            self.alive = False

    def draw(self, fx):
        ratio = 1.0 - self.radius / config.SHOCKWAVE_MAX_RADIUS
        if ratio <= 0:
            return
        cx, cy = self.x, self.y
        r = self.radius
        # 白热主环
        white = (min(255, self.color[0] + 80),
                 min(255, self.color[1] + 80),
                 min(255, self.color[2] + 80))
        thickness = max(1, int((config.SHOCKWAVE_THICKNESS + 5) * ratio))
        draw_ring(fx, (cx, cy), r, white, thickness=thickness, alpha=ratio)
        # 同色中层
        draw_ring(fx, (cx, cy), r * 1.03, self.color,
                  thickness=max(1, thickness // 2), alpha=ratio * 0.65)
        # 外色光晕（更宽更大）
        draw_ring(fx, (cx, cy), r * 0.94, scale_color(self.color, 0.35),
                  thickness=thickness * 2, alpha=ratio * 0.4)
        # 内回响（延迟出现）
        if r > 80:
            inner_r = r * 0.45
            if inner_r > 2:
                draw_ring(fx, (cx, cy), inner_r, self.color,
                          thickness=1, alpha=ratio * 0.5)
        # 粒子环（在波前带一带粒子）
        if self.particle_timer % 3 == 0 and r > 10:
            for _ in range(2):
                a = random.uniform(0, math.tau)
                px = cx + math.cos(a) * r
                py = cy + math.sin(a) * r
                draw_glow(fx, (px, py), 3 * ratio + 1,
                          self.color, layers=3)
        # 辐射裂纹（短亮线从中心向外）
        if self.particle_timer < 6:
            for _ in range(6):
                a = random.uniform(0, math.tau)
                dist = r * random.uniform(0.3, 0.9)
                lx1 = cx + math.cos(a) * dist
                ly1 = cy + math.sin(a) * dist
                lx2 = cx + math.cos(a) * (dist + 18 * ratio)
                ly2 = cy + math.sin(a) * (dist + 18 * ratio)
                pygame.draw.line(fx, scale_color(white, ratio * 0.4),
                                 (int(lx1), int(ly1)),
                                 (int(lx2), int(ly2)), 1)


class ShockwaveManager:
    def __init__(self, theme):
        self.theme = theme
        self.waves = []

    def set_theme(self, theme):
        self.theme = theme

    def trigger(self, center, color=None, start_radius=4):
        self.waves.append(_Wave(center[0], center[1],
                                color or self.theme["core"], start_radius))

    def trigger_multi(self, center, rings=3, color=None):
        base = color or self.theme["core"]
        spectrum = self.theme.get("spectrum", [base])
        for i in range(rings):
            c = spectrum[i % len(spectrum)]
            self.waves.append(_Wave(center[0], center[1], c,
                                    start_radius=4 + i * 70))

    def update(self):
        for w in self.waves:
            w.update()
        self.waves = [w for w in self.waves if w.alive]

    def draw(self, fx):
        for w in self.waves:
            w.draw(fx)

    def clear(self):
        self.waves.clear()
