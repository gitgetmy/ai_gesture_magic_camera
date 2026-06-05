# -*- coding: utf-8 -*-
"""
effects/screen_flash.py —— 屏幕闪白（电影级 · 径向渐变闪光）

电影级闪白结构：
  - 径向渐变：中心最亮（白），边缘暗（透明），模拟真实爆炸光衰减
  - 色相偏移：根据主题色给闪白混入微量主题色调
  - 色散边缘：R/G/B 通道略微错位模拟色差（chromatic aberration）
  - 快速衰减：非线性衰减曲线，初始极亮→迅速消失
"""
import math

import pygame

import config
from utils.math_utils import scale_color


class ScreenFlash:
    def __init__(self):
        self.alpha = 0.0
        self.tint = (255, 255, 255)  # 闪白色调（被 trigger 更新）
        self._gradient_cache = {}
        # 预渲染中心暗角遮罩（用于边缘色散）
        self._vignette = None

    def trigger(self, intensity=180, tint=None):
        """intensity: 0~255，tint: 可选主题色混入"""
        self.alpha = max(self.alpha, float(intensity))
        if tint is not None:
            # 混入微量主题色
            self.tint = (
                min(255, int(255 * 0.85 + tint[0] * 0.15)),
                min(255, int(255 * 0.85 + tint[1] * 0.15)),
                min(255, int(255 * 0.85 + tint[2] * 0.15)),
            )
        else:
            self.tint = (255, 255, 255)

    def update(self):
        if self.alpha > 0:
            # 非线性衰减：初始快速，后段慢（模拟真实爆炸闪光）
            self.alpha *= 0.78
            if self.alpha < 2:
                self.alpha = 0.0

    def draw(self, screen):
        if self.alpha <= 0:
            return
        a = int(min(255, self.alpha))
        w, h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT

        # 径向渐变遮罩：中心亮白 → 边缘暗
        # 用多层嵌套圆近似（性能好过逐像素）
        cx, cy = w / 2, h / 2
        max_r = math.hypot(cx, cy)

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        # 从大到小画同心圆，越内越亮
        steps = 12
        for i in range(steps, -1, -1):
            t = i / steps
            r = int(max_r * (t ** 0.6))  # 非线性，中心区域更大
            alpha = int(a * (1 - t) ** 1.5)
            if alpha <= 2:
                continue
            # 外围混入主题色调
            if t > 0.5:
                mix = (t - 0.5) * 2
                col = (
                    int(self.tint[0] * (1 - mix * 0.25)),
                    int(self.tint[1] * (1 - mix * 0.25)),
                    int(self.tint[2] * (1 - mix * 0.25)),
                )
            else:
                col = self.tint
            pygame.draw.circle(overlay, (*col, alpha),
                               (int(cx), int(cy)), r)

        screen.blit(overlay, (0, 0))
