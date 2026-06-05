# -*- coding: utf-8 -*-
"""
effects/magic_circle.py —— 魔法阵特效

在手掌中心绘制多层旋转圆环，带刻度线、符文点和围绕圆周运动的发光点。
张开手掌时逐渐放大显现，手移开时逐渐淡出（用 scale 在 0~1 间平滑过渡）。
"""
import math

import pygame

import config
from utils.draw_utils import draw_ring, draw_glow
from utils.math_utils import scale_color


class MagicCircle:
    def __init__(self, theme, base_radius=None):
        self.theme = theme
        self.base_radius = base_radius or config.MAGIC_CIRCLE_RADIUS
        self.rotation = 0.0
        self.scale = 0.0          # 0=隐藏，1=完全显现
        self.center = (0, 0)
        self.active = False

    def set_theme(self, theme):
        self.theme = theme

    def update(self, center=None, scale_mul=1.0):
        """
        center 不为 None 表示本帧应显现魔法阵（手在）。
        scale 平滑趋近目标值，实现淡入淡出。
        """
        self.rotation += config.MAGIC_CIRCLE_ROT_SPEED
        if center is not None:
            self.center = center
            self.active = True
            self.scale += (1.0 * scale_mul - self.scale) * 0.15
        else:
            self.scale += (0.0 - self.scale) * 0.12
            if self.scale < 0.02:
                self.active = False

    def draw(self, fx_surface):
        if self.scale < 0.02:
            return
        cx, cy = self.center
        R = self.base_radius * self.scale
        color = self.theme["core"]
        pal = self.theme["palette"]

        # 外圈 + 内圈两个主圆环
        draw_ring(fx_surface, self.center, R, color, thickness=2, alpha=0.9)
        draw_ring(fx_surface, self.center, R * 0.72, pal[0], thickness=2, alpha=0.7)
        draw_ring(fx_surface, self.center, R * 0.45, pal[-1], thickness=1, alpha=0.6)

        # 刻度线：沿外圈一圈短线（随魔法阵反向旋转）
        ticks = 24
        for i in range(ticks):
            a = self.rotation * -1.0 + i * (math.tau / ticks)
            x1 = cx + math.cos(a) * R
            y1 = cy + math.sin(a) * R
            x2 = cx + math.cos(a) * (R * 0.9)
            y2 = cy + math.sin(a) * (R * 0.9)
            pygame.draw.line(fx_surface, scale_color(color, 0.6),
                             (x1, y1), (x2, y2), 1)

        # 符文 / 发光点：沿中圈圆周运动
        dots = 8
        for i in range(dots):
            a = self.rotation + i * (math.tau / dots)
            x = cx + math.cos(a) * (R * 0.72)
            y = cy + math.sin(a) * (R * 0.72)
            draw_glow(fx_surface, (x, y), 5 * self.scale, pal[i % len(pal)], layers=4)
