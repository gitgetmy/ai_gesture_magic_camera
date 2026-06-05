# -*- coding: utf-8 -*-
"""
effects/dragon_flow.py —— 龙形粒子流（电影级 · 龙游云海）

多层龙形结构：
  - 龙脊柱：轨迹点队列，从尾到头逐渐变粗变亮
  - 龙身波纹：脊柱两侧交替偏移的正弦波，模拟龙身蜿蜒扭动
  - 龙鳞光点：沿脊柱两侧散布的细小鳞片状粒子
  - 龙头高亮：带龙角/龙须感的发光结构
  - 云气：龙身周围随机飘散的云状柔光粒子
"""
from collections import deque

import pygame
import math
import random

from utils.draw_utils import draw_glow
from utils.math_utils import lerp_color, scale_color


class DragonFlow:
    def __init__(self, particle_system, theme, max_nodes=32):
        self.ps = particle_system
        self.theme = theme
        self.spine = deque(maxlen=max_nodes)
        self._idle = 0
        self._phase = 0.0

    def set_theme(self, theme):
        self.theme = theme

    def feed(self, pos):
        """喂入当前手部位置作为龙头节点。"""
        self.spine.append((pos[0], pos[1]))
        self._idle = 0
        self._phase += 0.15
        # 龙头周围散出云气粒子
        self.ps.spawn_trail(pos, velocity=0.9)

    def update(self):
        self._idle += 1
        if self._idle > 3 and self.spine:
            self.spine.popleft()

    def draw(self, fx):
        n = len(self.spine)
        if n < 2:
            return
        head_col = self.theme["core"]
        accent = self.theme.get("accent", self.theme["core"])
        palette = self.theme.get("palette", [head_col])
        pts = list(self.spine)

        # ---- 龙身蜿蜒 ----
        for i in range(n - 1):
            t = i / max(1, n - 2)
            # 颜色渐变：尾 → 头
            color = lerp_color(palette[0], head_col, t)
            p1 = pts[i]
            p2 = pts[i + 1]
            # 段方向
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 0.5:
                continue
            nx = -dy / seg_len
            ny = dx / seg_len
            # 正弦波摆动幅度沿身体增大（尾小头大）
            wave = math.sin(self._phase * 2 + i * 0.7) * (6 + t * 14)
            mx = (p1[0] + p2[0]) / 2 + nx * wave
            my = (p1[1] + p2[1]) / 2 + ny * wave
            # 身宽
            width = 2 + t * 10
            draw_glow(fx, (mx, my), width, color, layers=4)

        # ---- 龙鳞光点（身体两侧散布） ----
        for i in range(1, n - 1, 2):
            t = i / max(1, n - 1)
            p = pts[i]
            p_next = pts[min(i + 1, n - 1)]
            dx = p_next[0] - p[0]
            dy = p_next[1] - p[1]
            seg_len = math.hypot(dx, dy) + 0.01
            nx = -dy / seg_len
            ny = dx / seg_len
            spread = 8 + t * 10
            col = lerp_color(palette[1 % len(palette)], head_col, t)
            for side in (-1, 1):
                sx = p[0] + nx * spread * side
                sy = p[1] + ny * spread * side
                draw_glow(fx, (sx, sy), 2 + t * 3, col, layers=3)

        # ---- 龙头高亮（龙角 + 龙须 + 核心光） ----
        head = pts[-1]
        draw_glow(fx, head, 18, head_col, layers=5)
        draw_glow(fx, head, 9, (255, 255, 255), layers=4)
        # 龙角：两点从头部斜上方伸出
        if n >= 2:
            prev = pts[-2]
            hdx = head[0] - prev[0]
            hdy = head[1] - prev[1]
            hlen = math.hypot(hdx, hdy) + 0.01
            hnx = -hdy / hlen
            hny = hdx / hlen
            for side in (-1, 1):
                horn_x = head[0] + hnx * side * 14 + hdx / hlen * 8
                horn_y = head[1] + hny * side * 14 + hdy / hlen * 8
                draw_glow(fx, (horn_x, horn_y), 6, accent, layers=4)
            # 龙须：两点从头部两侧垂下
            for side in (-1, 1):
                whisker_x = head[0] + hnx * side * 22
                whisker_y = head[1] + hny * side * 22 + 10
                draw_glow(fx, (whisker_x, whisker_y), 4, palette[0], layers=3)

    def clear(self):
        self.spine.clear()
