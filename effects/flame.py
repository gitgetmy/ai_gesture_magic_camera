# -*- coding: utf-8 -*-
"""
effects/flame.py —— 火焰掌特效（电影级）

多层火焰结构：
  - 内核白热火球（掌心位置，脉冲式缩放）
  - 中层橙红火焰舌（多条扭曲上升的火舌，随机摆动）
  - 外层上升粒子（烟/灰烬向上飘散）
  - 地面/手周热力扭曲光晕
"""
import math
import random

import pygame

from utils.draw_utils import draw_glow
from utils.math_utils import scale_color

# 火焰色阶：白热 → 亮黄 → 橙 → 红 → 暗红
FIRE_GRADE = [
    (255, 255, 240), (255, 240, 160), (255, 200, 60),
    (255, 130, 30), (255, 70, 20), (200, 35, 10),
]


class _FlameTongue:
    """一条火舌：从底部扭动上升到顶端，生命周期内形态随机摆动。"""
    __slots__ = ("x", "y", "height", "phase", "speed", "life", "max_life",
                 "sway_amp", "width")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.height = random.uniform(40, 95)
        self.phase = random.uniform(0, math.tau)
        self.speed = random.uniform(0.08, 0.18)
        self.sway_amp = random.uniform(8, 22)
        self.width = random.uniform(6, 14)
        self.max_life = random.randint(16, 32)
        self.life = self.max_life

    @property
    def alive(self):
        return self.life > 0


class Flame:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.tongues = []
        self._max_tongues = 20

    def set_theme(self, theme):
        self.theme = theme

    def emit(self, center, intensity=1.0):
        """在 center 处喷发火焰（粒子 + 火舌 + 热力光晕）。"""
        cx, cy = center
        # 火焰粒子（上飘 + 随机扩散）
        flame_count = max(3, int(12 * intensity))
        self.ps.spawn_flame(center, count=flame_count)

        # 新增火舌
        room = self._max_tongues - len(self.tongues)
        new_tongues = min(max(1, int(5 * intensity)), room)
        for _ in range(new_tongues):
            tx = cx + random.uniform(-28, 28)
            ty = cy + random.uniform(-6, 10)
            self.tongues.append(_FlameTongue(tx, ty))
        # 清理超出上限的旧火舌
        while len(self.tongues) > self._max_tongues:
            self.tongues.pop(0)

    def update(self):
        for t in self.tongues:
            t.phase += t.speed
            t.life -= 1
        self.tongues = [t for t in self.tongues if t.alive]

    def draw(self, fx, center=None):
        """绘制火焰——先画火舌，再画内核辉光。"""
        # 火舌：多条扭动上升的线段（用多点折线近似扭动）
        for t in self.tongues:
            ratio = t.life / t.max_life
            alpha = ratio
            if alpha <= 0.05:
                continue
            # 从底部到顶部采样颜色
            segments = 8
            prev = (t.x, t.y)
            for i in range(1, segments + 1):
                u = i / segments
                # 扭动偏移
                sway = math.sin(t.phase + u * 4.5) * t.sway_amp * u
                px = t.x + sway
                py = t.y - t.height * u
                # 颜色沿高度变化：底部更亮（白热），顶部更暗（红/烟）
                color_idx = int((1 - u) * (len(FIRE_GRADE) - 1))
                col = FIRE_GRADE[min(color_idx, len(FIRE_GRADE) - 1)]
                col = scale_color(col, alpha)
                w = max(1, int(t.width * (1 - u * 0.7) * alpha))
                if w >= 1:
                    pygame.draw.line(fx, col,
                                     (int(prev[0]), int(prev[1])),
                                     (int(px), int(py)), w)
                # 顶部火星散开
                if i == segments and random.random() < 0.5:
                    draw_glow(fx, (px, py), 3 * alpha + 1,
                              FIRE_GRADE[2], layers=2)
                prev = (px, py)

    def clear(self):
        self.tongues.clear()
