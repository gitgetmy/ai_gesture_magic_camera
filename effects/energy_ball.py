# -*- coding: utf-8 -*-
"""
effects/energy_ball.py —— 能量球特效（电影级）

多层等离子能量结构：
  - 内核心：白热高亮球体（多层辉光叠出核聚变感）
  - 等离子弧：在球面上随机游走的电弧/耀斑（类似太阳表面）
  - 外旋光环：2-3条在不同角度/速度旋转的光粒子环
  - 能量触须：从核心偶尔伸出的等离子触手
"""
import math
import random

import pygame

from utils.draw_utils import draw_glow
from utils.math_utils import scale_color


class _PlasmaArc:
    """球面上的一条短电弧。"""
    __slots__ = ("angle", "arc_len", "life", "max_life", "offset_angle")

    def __init__(self):
        self.angle = random.uniform(0, math.tau)
        self.arc_len = random.uniform(0.4, 1.2)
        self.offset_angle = random.uniform(0, math.tau)
        self.max_life = random.randint(8, 20)
        self.life = self.max_life

    @property
    def alive(self):
        return self.life > 0


class EnergyBall:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.arcs = []
        self._max_arcs = 14
        self._phase = 0.0

    def set_theme(self, theme):
        self.theme = theme

    def emit(self, center, radius=None, intensity=1.0):
        radius = radius or 40
        # 多层轨道粒子（不同半径、不同速度、不同颜色，营造深度感）
        palette = self.theme.get("spectrum", self.theme["palette"])
        for layer in range(3):
            r_mul = 1.0 + layer * 0.3
            speed = 0.04 * (1.0 if layer % 2 == 0 else -0.7)
            col = palette[layer % len(palette)]
            self.ps.spawn_orbit(
                center,
                count=int(4 * intensity) + 2,
                radius=radius * r_mul,
                speed=speed,
                color=col,
            )
        # 新增等离子弧
        new_arcs = min(int(3 * intensity) + 1, self._max_arcs - len(self.arcs))
        for _ in range(new_arcs):
            self.arcs.append(_PlasmaArc())
        while len(self.arcs) > self._max_arcs:
            self.arcs.pop(0)

        self._pending_core = (center, radius, intensity)

    def update(self):
        self._phase += 0.05
        for a in self.arcs:
            a.angle += 0.06
            a.life -= 1
        self.arcs = [a for a in self.arcs if a.alive]

    def draw_core(self, fx):
        """绘制能量核心 + 等离子弧 + 旋转光环。"""
        core_data = getattr(self, "_pending_core", None)
        if core_data is None:
            # 无新emit时也绘制残留弧光
            self._draw_arcs(fx, (0, 0), 40)
            return
        center, radius, intensity = core_data
        core = self.theme["core"]
        accent = self.theme.get("accent", core)
        cx, cy = center
        R = radius * intensity

        # 最外层柔光晕（超宽 bloom）
        draw_glow(fx, center, R * 2.4, scale_color(accent, 0.18), layers=6)
        # 中层辉光
        draw_glow(fx, center, R * 1.5, scale_color(core, 0.45), layers=6)
        # 内层辉光
        draw_glow(fx, center, R * 0.7, core, layers=6)
        # 白热核心
        draw_glow(fx, center, R * 0.25, (255, 255, 255), layers=5)

        # 等离子弧
        self._draw_arcs(fx, center, R)

        # 双环光环（加色，绕核心旋转）
        for i, (rm, sp, w) in enumerate(((1.25, 0.04, 2), (0.85, -0.06, 1))):
            ring_r = R * rm
            # 用发光点近似光环
            dots = 24
            for j in range(dots):
                a = self._phase * sp * 10 + j * math.tau / dots
                px = cx + math.cos(a) * ring_r
                py = cy + math.sin(a) * ring_r
                draw_glow(fx, (px, py), 3, core, layers=3)

        self._pending_core = None

    def _draw_arcs(self, fx, center, R):
        """绘制球面等离子弧。"""
        if not self.arcs:
            return
        cx, cy = center
        core = self.theme["core"]
        for a in self.arcs:
            ratio = a.life / a.max_life
            if ratio <= 0.05:
                continue
            col = scale_color(core, ratio)
            # 弧：沿球面一段
            num_segs = 6
            pts = []
            for i in range(num_segs + 1):
                t = i / num_segs
                ang = a.angle + t * a.arc_len
                # 添加抖动模拟等离子体不稳定性
                jitter = math.sin(self._phase * 8 + ang * 5) * R * 0.12 * ratio
                r = R + jitter
                pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
            if len(pts) >= 2:
                w = max(1, int(3 * ratio))
                pygame.draw.lines(fx, col, False,
                                  [(int(p[0]), int(p[1])) for p in pts], w)

    def clear(self):
        self.arcs.clear()
