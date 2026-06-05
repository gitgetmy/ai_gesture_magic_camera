# -*- coding: utf-8 -*-
"""
effects/bronze_shield.py —— 青铜护盾（电影级 · 玄金护体）

电影级护盾结构：
  - 多层同心环（外金内铜，带金属反光渐变）
  - 放射辐条 + 旋转内圈铭文带
  - 青铜饕餮纹（简化几何纹样：菱形 + 三角 + 短弧）
  - 盾心高亮（能量核心）
  - 护盾破碎时：碎片沿切线飞出 + 金属火花
  - 激活时短暂的六边形光栅扫描线
"""
import math

import pygame

from utils.draw_utils import draw_ring, draw_glow, draw_beams
from utils.math_utils import scale_color

GOLD = (255, 215, 120)
BRONZE = (210, 155, 85)
DARK_BRONZE = (150, 110, 55)


class BronzeShield:
    def __init__(self, particle_system, theme, base_radius=160):
        self.ps = particle_system
        self.theme = theme
        self.base_radius = base_radius
        self.scale = 0.0
        self.center = (0, 0)
        self.rotation = 0.0
        self._was_visible = False
        self._activate_phase = 0.0

    def set_theme(self, theme):
        self.theme = theme

    def update(self, center=None):
        self.rotation += 0.01
        if center is not None:
            self.center = center
            self.scale += (1.0 - self.scale) * 0.16
            self._was_visible = True
            self._activate_phase = min(1.0, self._activate_phase + 0.05)
        else:
            if self._was_visible and self.scale > 0.5:
                self._shatter()
            self._was_visible = False
            self.scale += (0.0 - self.scale) * 0.18
            self._activate_phase = max(0.0, self._activate_phase - 0.08)
            if self.scale < 0.02:
                self.scale = 0.0

    def _shatter(self):
        """护盾破碎：碎片沿切线飞出。"""
        cx, cy = self.center
        R = self.base_radius * self.scale
        for _ in range(60):
            ang = math.radians(random.uniform(0, 360))
            # 碎片从环带位置沿切线飞出
            r = R * random.uniform(0.5, 1.1)
            sx = cx + math.cos(ang) * r
            sy = cy + math.sin(ang) * r
            # 切线方向
            tx = -math.sin(ang)
            ty = math.cos(ang)
            spd = random.uniform(6, 14)
            import random as _rnd
            col = _rnd.choice([GOLD, BRONZE])
            self.ps.spawn_burst((sx, sy), count=1, speed=spd, color=col)
        # 中心爆破
        self.ps.spawn_burst(self.center, count=25, speed=9, color=GOLD)

    @property
    def visible(self):
        return self.scale >= 0.02

    def draw(self, fx):
        if not self.visible:
            return
        cx, cy = self.center
        R = self.base_radius * self.scale

        # 最外环（金，带辉光）
        draw_ring(fx, self.center, R, GOLD, thickness=3, alpha=0.95)
        draw_ring(fx, self.center, R * 1.04, scale_color(GOLD, 0.3),
                  thickness=6, alpha=0.5)
        # 中层青铜环
        draw_ring(fx, self.center, R * 0.84, BRONZE, thickness=2, alpha=0.7)
        # 内层暗青铜环
        draw_ring(fx, self.center, R * 0.6, DARK_BRONZE, thickness=1, alpha=0.55)
        # 内核金环
        draw_ring(fx, self.center, R * 0.38, GOLD, thickness=2, alpha=0.8)

        # 放射辐条（12根，旋转）
        draw_beams(fx, self.center, R * 0.95, scale_color(BRONZE, 0.7),
                   count=12, rotation=self.rotation, width=2, alpha=0.7)
        # 次级辐条（24根，更细）
        draw_beams(fx, self.center, R * 0.82, scale_color(GOLD, 0.35),
                   count=24, rotation=-self.rotation * 0.6, width=1, alpha=0.5)

        # 青铜纹样：外环一圈菱形
        motifs = 16
        for i in range(motifs):
            a = self.rotation * 0.3 + i * math.tau / motifs
            mx = cx + math.cos(a) * R * 0.9
            my = cy + math.sin(a) * R * 0.9
            d = max(2, R * 0.05)
            pts = [(mx, my - d), (mx + d, my), (mx, my + d), (mx - d, my)]
            pygame.draw.polygon(fx, scale_color(GOLD, 0.75), pts, 1)
            # 小三角（指向圆心）
            inner_pts = [
                (mx, my - d * 0.7),
                (mx - d * 0.5, my + d * 0.5),
                (mx + d * 0.5, my + d * 0.5),
            ]
            pygame.draw.polygon(fx, scale_color(BRONZE, 0.5), inner_pts, 1)

        # 内圈铭文带（旋转的小刻度标记）
        ticks = 36
        for i in range(ticks):
            a = -self.rotation * 1.5 + i * math.tau / ticks
            x1 = cx + math.cos(a) * R * 0.62
            y1 = cy + math.sin(a) * R * 0.62
            x2 = cx + math.cos(a) * R * 0.56
            y2 = cy + math.sin(a) * R * 0.56
            pygame.draw.line(fx, scale_color(GOLD, 0.6),
                             (int(x1), int(y1)), (int(x2), int(y2)), 1)

        # 六边形光栅扫描线（激活时）
        if self._activate_phase > 0.05:
            hex_pts = []
            for i in range(6):
                a = -self.rotation * 0.8 + i * math.tau / 6
                hex_pts.append((cx + math.cos(a) * R * 0.7,
                                cy + math.sin(a) * R * 0.7))
            if len(hex_pts) >= 3:
                pygame.draw.polygon(fx,
                                    scale_color(self.theme["core"],
                                                self._activate_phase * 0.2),
                                    hex_pts, 1)

        # 盾心高亮
        draw_glow(fx, self.center, R * 0.2, GOLD, layers=5)
        draw_glow(fx, self.center, R * 0.08, (255, 255, 255), layers=4)

    def clear(self):
        pass
