# -*- coding: utf-8 -*-
"""
effects/ice.py —— 冰晶凝华特效（电影级）

多层冰晶结构：
  - 中央六角冰核（多层叠放、缓慢旋转的六边形阵）
  - 晶格枝杈（从中心向外辐射的分形冰晶枝，Kepler 雪花感）
  - 冷雾粒子（缓慢向中心聚集 + 向外扩散的冰雾）
  - 棱镜折射闪光（随机方向的短促虹彩闪光）
"""
import math
import random

import pygame

from utils.draw_utils import draw_glow
from utils.math_utils import scale_color

ICE_COLORS = [(200, 235, 255), (170, 220, 255), (220, 245, 255), (140, 200, 250)]
ICE_CORE = (235, 250, 255)


class _CrystalBranch:
    """一条冰晶枝杈：从中心向外生长，带分叉。"""
    __slots__ = ("angle", "length", "life", "max_life", "parent_angle")

    def __init__(self, angle, length):
        self.angle = angle
        self.length = length
        self.parent_angle = angle
        self.max_life = random.randint(50, 90)
        self.life = self.max_life

    @property
    def alive(self):
        return self.life > 0


class Ice:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.branches = []
        self._centers = []          # 当前活跃的冰晶中心
        self._max_branches = 80
        self._phase = 0.0

    def set_theme(self, theme):
        self.theme = theme

    def emit(self, center):
        """在 center 处生成冰晶簇。"""
        self.ps.spawn_attract(center, count=8, ice=True)
        # 记录中心
        self._centers.append([*center, 30])   # [x, y, remaining_life] mutable
        # 生成辐射冰晶枝杈
        for _ in range(random.randint(4, 7)):
            ang = random.uniform(0, math.tau)
            length = random.uniform(25, 60)
            self.branches.append(_CrystalBranch(ang, length))
        # 保持上限
        while len(self.branches) > self._max_branches:
            self.branches.pop(0)

    def update(self):
        self._phase += 0.03
        for b in self.branches:
            b.life -= 1
        self.branches = [b for b in self.branches if b.alive]
        # 中心衰减
        for c in self._centers:
            c[2] -= 1    # remaining_life -= 1
        self._centers = [c for c in self._centers if c[2] > 0]

    def draw_crystals(self, fx, center, t):
        """
        绘制当前帧的冰晶簇（加色层）。
        - 中心六角冰核
        - 辐射晶格枝杈
        - 冷光闪光点
        """
        cx, cy = center
        core = ICE_CORE

        # 中央多层六边形（缓慢旋转）
        for layer, (size, rot_off) in enumerate(((18, 0), (12, math.pi / 6), (8, -math.pi / 12))):
            ang_offset = self._phase * 0.3 + rot_off
            pts = []
            for i in range(6):
                a = ang_offset + i * math.tau / 6
                pts.append((cx + math.cos(a) * size, cy + math.sin(a) * size))
            if len(pts) >= 3:
                alpha = 0.5 + layer * 0.2
                pygame.draw.polygon(fx, scale_color(core, alpha), pts, 1)
                # 内层填充
                if layer == 2:
                    pygame.draw.polygon(fx, scale_color(core, 0.18), pts)

        # 中央冰核辉光
        draw_glow(fx, (cx, cy), 20, core, layers=5)
        draw_glow(fx, (cx, cy), 8, (255, 255, 255), layers=4)

        # 辐射冰晶枝杈
        for b in self.branches:
            ratio = b.life / b.max_life
            if ratio <= 0.05:
                continue
            col = scale_color(random.choice(ICE_COLORS), ratio)
            # 主线
            ex = cx + math.cos(b.angle) * b.length * ratio
            ey = cy + math.sin(b.angle) * b.length * ratio
            pygame.draw.line(fx, col, (int(cx), int(cy)), (int(ex), int(ey)), 2)
            # 一级分叉（从主枝中段分出）
            mid_x = cx + math.cos(b.angle) * b.length * 0.55 * ratio
            mid_y = cy + math.sin(b.angle) * b.length * 0.55 * ratio
            for side in (-1, 1):
                sub_ang = b.angle + side * 0.45
                sub_len = b.length * 0.3 * ratio
                sub_x = mid_x + math.cos(sub_ang) * sub_len
                sub_y = mid_y + math.sin(sub_ang) * sub_len
                pygame.draw.line(fx, scale_color(col, 0.6),
                                 (int(mid_x), int(mid_y)),
                                 (int(sub_x), int(sub_y)), 1)

        # 梭形折射闪光（随机时间、随机方向）
        if random.random() < 0.25:
            for _ in range(2):
                a = random.uniform(0, math.tau)
                d = random.uniform(10, 30)
                fx_x = cx + math.cos(a) * d
                fy_y = cy + math.sin(a) * d
                flash_col = (255, 255, 255)
                # 十字闪光
                cross = 6
                pygame.draw.line(fx, scale_color(flash_col, 0.7),
                                 (int(fx_x - cross), int(fy_y)),
                                 (int(fx_x + cross), int(fy_y)), 1)
                pygame.draw.line(fx, scale_color(flash_col, 0.7),
                                 (int(fx_x), int(fy_y - cross)),
                                 (int(fx_x), int(fy_y + cross)), 1)
                draw_glow(fx, (fx_x, fy_y), 3, flash_col, layers=2)

    def clear(self):
        self.branches.clear()
        self._centers.clear()
