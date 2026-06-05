# -*- coding: utf-8 -*-
"""Circular talisman and Taiji vortex for two-hand circle gestures."""
import math

import pygame

import config
from utils.math_utils import scale_color


class TaijiVortex:
    def __init__(self, theme):
        self.theme = theme
        self.center = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        self.level = 0.0
        self.radius = 80.0
        self.rotation = 0.0
        self.spin_dir = 1.0
        self.runes = ["乾", "坤", "坎", "离", "震", "巽", "艮", "兑"]
        self.font = pygame.font.SysFont("microsoftyahei,simhei,arial", 20, bold=True)
        self.small_font = pygame.font.SysFont("microsoftyahei,simhei,arial", 15)

    def set_theme(self, theme):
        self.theme = theme

    def clear(self):
        self.level = 0.0

    @property
    def active(self):
        return self.level > 0.02

    def emit(self, center, direction=1.0, radius=210):
        self.center = center
        self.spin_dir = 1.0 if direction >= 0 else -1.0
        self.radius = max(120, min(285, radius))
        self.level = 1.0

    def update(self):
        self.rotation += 0.045 * self.spin_dir * (0.45 + self.level)
        self.level = max(0.0, self.level - 0.018)

    def draw(self, fx):
        if self.level <= 0.02:
            return

        cx, cy = self.center
        r = self.radius * (0.94 + 0.06 * math.sin(self.rotation * 2.0))
        core = self.theme["core"]
        blue = self.theme["palette"][0]
        gold = self.theme["palette"][1] if len(self.theme["palette"]) > 1 else core

        layer = pygame.Surface(fx.get_size(), pygame.SRCALPHA)

        # Soft vortex well, kept low so it feels cinematic rather than like a flat disk.
        for i, mul in enumerate((1.28, 1.02, 0.76, 0.48)):
            alpha = int((42 - i * 7) * self.level)
            pygame.draw.circle(layer, (*scale_color(blue, 0.9 - i * 0.12), alpha),
                               (int(cx), int(cy)), int(r * mul), 1)

        # Talisman rings and segmented ticks.
        for i, mul in enumerate((1.0, 0.82, 0.62)):
            pygame.draw.circle(layer, (*scale_color(core, 0.95 - i * 0.18), int(120 * self.level)),
                               (int(cx), int(cy)), int(r * mul), 2 if i == 0 else 1)

        tick_count = 48
        for i in range(tick_count):
            a = self.rotation + i * math.tau / tick_count
            long_tick = i % 6 == 0
            r1 = r * (0.94 if long_tick else 0.97)
            r2 = r * 1.02
            x1, y1 = cx + math.cos(a) * r1, cy + math.sin(a) * r1
            x2, y2 = cx + math.cos(a) * r2, cy + math.sin(a) * r2
            col = scale_color(core if long_tick else blue, 0.85)
            pygame.draw.line(layer, (*col, int((92 if long_tick else 44) * self.level)),
                             (x1, y1), (x2, y2), 1)

        # Yin-yang spiral arms.
        for arm, col in enumerate((core, gold)):
            offset = arm * math.pi
            pts = []
            for k in range(88):
                t = k / 87
                rr = r * (0.12 + 0.78 * t)
                a = self.rotation * 1.8 + offset + t * math.tau * 1.45 * self.spin_dir
                pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            if len(pts) > 1:
                pygame.draw.lines(layer, (*scale_color(col, 0.95), int(120 * self.level)),
                                  False, pts, 2)

        # Minimal bagua/rune nodes around the circle.
        for i, rune in enumerate(self.runes):
            a = -self.rotation * 0.45 + i * math.tau / len(self.runes)
            x = cx + math.cos(a) * r * 1.13
            y = cy + math.sin(a) * r * 1.13
            pygame.draw.circle(layer, (*scale_color(blue, 0.8), int(70 * self.level)),
                               (int(x), int(y)), 8, 1)
            text = self.font.render(rune, True, core)
            text.set_alpha(int(120 * self.level))
            layer.blit(text, text.get_rect(center=(int(x), int(y))))

        label = self.small_font.render("太极旋涡", True, core)
        label.set_alpha(int(105 * self.level))
        layer.blit(label, label.get_rect(center=(int(cx), int(cy + r * 0.38))))

        fx.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
