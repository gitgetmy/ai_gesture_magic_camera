# -*- coding: utf-8 -*-
"""
effects/ink_trail.py —— 水墨拖尾（凌空画符 / 水墨山水）

手指划过处留下墨痕：深色半透明圆点，随时间扩散、变淡，边缘略不规则。
墨色是深色，加色混合画不出来，所以水墨层用「正常透明度」直接叠到屏幕上
（在压暗的摄像头画面上形成压暗的墨韵）。配合朱砂/金色符点（这部分走加色发光）。
"""
import random

import pygame

from utils.draw_utils import draw_glow


class _Ink:
    __slots__ = ("x", "y", "radius", "max_radius", "life", "max_life")

    def __init__(self, x, y, max_radius):
        self.x = x
        self.y = y
        self.radius = max_radius * 0.3
        self.max_radius = max_radius
        self.max_life = random.randint(40, 80)
        self.life = self.max_life

    @property
    def alive(self):
        return self.life > 0

    def update(self):
        # 先快后慢地扩散
        self.radius += (self.max_radius - self.radius) * 0.08
        self.life -= 1


class InkTrail:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.blobs = []

    def set_theme(self, theme):
        self.theme = theme

    def emit(self, pos, big=False):
        """在 pos 处落墨。big=True 用于挥手的大片山水扩散。"""
        mr = random.uniform(26, 46) if big else random.uniform(10, 20)
        # 主墨点 + 周围几滴小墨点（飞白感）
        self.blobs.append(_Ink(pos[0], pos[1], mr))
        for _ in range(2 if big else 1):
            ox = random.uniform(-mr, mr)
            oy = random.uniform(-mr, mr)
            self.blobs.append(_Ink(pos[0] + ox, pos[1] + oy, mr * random.uniform(0.3, 0.6)))
        # 朱砂/金色符点（加色发光，作画符的高亮点）
        self.ps.spawn_trail(pos, velocity=0.6)

    def update(self):
        for b in self.blobs:
            b.update()
        self.blobs = [b for b in self.blobs if b.alive]
        # 防止墨点无限堆积
        if len(self.blobs) > 400:
            self.blobs = self.blobs[-400:]

    def draw(self, screen):
        """墨痕用正常透明度画到屏幕（深色压暗成墨韵）"""
        ink = self.theme["ink"]
        for b in self.blobs:
            ratio = b.life / b.max_life
            alpha = int(150 * ratio)
            if alpha <= 2 or b.radius < 1:
                continue
            r = int(b.radius)
            tmp = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*ink, alpha), (r, r), r)
            screen.blit(tmp, (int(b.x - r), int(b.y - r)))

    def draw_glow_points(self, fx):
        """符线高亮点（加色层），朱砂/金色，跟随最近的墨点闪烁"""
        accent = self.theme.get("accent", self.theme["core"])
        for b in self.blobs[-12:]:
            if b.life > b.max_life * 0.7:    # 只点亮新落的墨
                draw_glow(fx, (b.x, b.y), 4, accent, layers=3)

    def clear(self):
        self.blobs.clear()
