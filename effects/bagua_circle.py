# -*- coding: utf-8 -*-
"""
effects/bagua_circle.py —— 八卦阵特效（后天八卦 · 传统国风方位）

严格采用【后天八卦】排列，传统国风显示方式：上南、下北、左东、右西。
Pygame 坐标系：x 向右、y 向下；angle_deg=0 在右、90 在下、-90 在上。

屏幕方位与卦象（必须严格对应）：
  上方  离 ☲ (南)  -90°
  下方  坎 ☵ (北)   90°
  左方  震 ☳ (东)  180°
  右方  兑 ☱ (西)    0°
  左上  巽 ☴ (东南) -135°
  右上  坤 ☷ (西南)  -45°
  左下  艮 ☶ (东北)  135°
  右下  乾 ☰ (西北)   45°

三层结构：内圈太极/能量核心、中圈旋转粒子刻度、外圈后天八卦符号。
圆环、刻度可旋转，但【卦象与卦名保持正向、不随圆环倒转】，始终可读。
"""
import math

import pygame

from utils.draw_utils import draw_ring, draw_glow
from utils.math_utils import scale_color

# 后天八卦：name 卦名；angle_deg 屏幕角度；lines 三爻(自下而上, True=阳实, False=阴断)
BAGUA_HOUTIAN = [
    {"name": "离", "angle": -90,  "lines": [True,  False, True]},   # 上 / 南
    {"name": "坎", "angle":  90,  "lines": [False, True,  False]},  # 下 / 北
    {"name": "震", "angle": 180,  "lines": [True,  False, False]},  # 左 / 东
    {"name": "兑", "angle":   0,  "lines": [True,  True,  False]},  # 右 / 西
    {"name": "巽", "angle": -135, "lines": [False, True,  True]},   # 左上 / 东南
    {"name": "坤", "angle": -45,  "lines": [False, False, False]},  # 右上 / 西南
    {"name": "艮", "angle": 135,  "lines": [False, False, True]},   # 左下 / 东北
    {"name": "乾", "angle":  45,  "lines": [True,  True,  True]},   # 右下 / 西北
]


class BaguaCircle:
    def __init__(self, theme, font=None, base_radius=130):
        self.theme = theme
        self.font = font           # 用于绘制卦名（中文字体）
        self.base_radius = base_radius
        self.rotation = 0.0
        self.scale = 0.0
        self.center = (0, 0)
        self._label_cache = {}     # 卦名文字渲染缓存 (name,color)->Surface

    def set_theme(self, theme):
        self.theme = theme
        self._label_cache.clear()

    def update(self, center=None, scale_mul=1.0, rot_speed=0.02):
        self.rotation += rot_speed
        if center is not None:
            self.center = center
            self.scale += (scale_mul - self.scale) * 0.15
        else:
            self.scale += (0.0 - self.scale) * 0.12
            if self.scale < 0.02:
                self.scale = 0.0

    @property
    def visible(self):
        return self.scale >= 0.02

    def _draw_trigram_upright(self, fx, px, py, lines, color, half, dy, width=2):
        """在 (px,py) 画一个正向（水平）卦象：三条爻，自下而上。阴爻中断。"""
        c = scale_color(color, 0.95)
        # i=0 为最下爻；屏幕 y 向下，所以下爻 y 更大
        for i, yang in enumerate(lines):
            ly = py + (1 - i) * dy        # i=0 在下、i=2 在上
            if yang:
                pygame.draw.line(fx, c, (px - half, ly), (px + half, ly), width)
            else:
                seg = half * 0.4
                pygame.draw.line(fx, c, (px - half, ly), (px - seg, ly), width)
                pygame.draw.line(fx, c, (px + seg, ly), (px + half, ly), width)

    def _label(self, name, color):
        if self.font is None:
            return None
        key = (name, color)
        s = self._label_cache.get(key)
        if s is None:
            s = self.font.render(name, True, color)
            self._label_cache[key] = s
        return s

    def draw(self, fx):
        if not self.visible:
            return
        cx, cy = self.center
        R = self.base_radius * self.scale
        core = self.theme["core"]
        pal = self.theme["palette"]

        # 三层圆环
        draw_ring(fx, self.center, R * 1.34, pal[0], thickness=2, alpha=0.55)  # 外圈
        draw_ring(fx, self.center, R,        core,  thickness=2, alpha=0.9)    # 中圈
        draw_ring(fx, self.center, R * 0.5,  pal[-1], thickness=1, alpha=0.6)  # 内圈

        # 旋转刻度（外环一圈短线，随阵法旋转）
        ticks = 36
        for i in range(ticks):
            a = self.rotation + i * (math.tau / ticks)
            x1 = cx + math.cos(a) * R * 1.34
            y1 = cy + math.sin(a) * R * 1.34
            x2 = cx + math.cos(a) * R * 1.24
            y2 = cy + math.sin(a) * R * 1.24
            pygame.draw.line(fx, scale_color(core, 0.5), (x1, y1), (x2, y2), 1)

        # 中圈发光粒子点（顺时针）/ 内圈点（逆时针），制造内外反向旋转感
        for i in range(12):
            a = self.rotation + i * (math.tau / 12)
            x = cx + math.cos(a) * R
            y = cy + math.sin(a) * R
            draw_glow(fx, (x, y), 3 * self.scale + 1, core, layers=3)
        for i in range(8):
            a = -self.rotation * 1.3 + i * (math.tau / 8)
            x = cx + math.cos(a) * R * 0.5
            y = cy + math.sin(a) * R * 0.5
            draw_glow(fx, (x, y), 3 * self.scale + 1, pal[i % len(pal)], layers=3)

        # 后天八卦：固定方位、正向不倒转
        half = max(5, R * 0.085)
        dy = max(3, R * 0.05)
        for k, g in enumerate(BAGUA_HOUTIAN):
            a = math.radians(g["angle"])
            tx = cx + math.cos(a) * R * 1.5
            ty = cy + math.sin(a) * R * 1.5
            col = pal[k % len(pal)]
            # 卦象（爻线，正向）
            self._draw_trigram_upright(fx, tx, ty, g["lines"], col, half, dy, width=2)
            # 方位光点
            px = cx + math.cos(a) * R * 1.18
            py = cy + math.sin(a) * R * 1.18
            draw_glow(fx, (px, py), 4 * self.scale + 1, core, layers=3)

        # 中心能量核心
        draw_glow(fx, self.center, R * 0.2, core, layers=5)

    def emit_release_beams(self, particle_system):
        """释放阶段：八个后天方位射出粒子光束（在 main 蓄满时调用）"""
        cx, cy = self.center
        for g in BAGUA_HOUTIAN:
            a = math.radians(g["angle"])
            dx, dy = math.cos(a), math.sin(a)
            for t in range(6):
                particle_system.spawn_burst(
                    (cx + dx * 20, cy + dy * 20), count=1, speed=12 + t,
                    color=self.theme["core"])
