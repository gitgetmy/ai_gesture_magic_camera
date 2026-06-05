# -*- coding: utf-8 -*-
"""
effects/taiji_orb.py —— 太极阴阳能量球

双手靠近时在两手之间生成旋转的太极图，外圈环绕阴阳两色粒子。
注意：太极有黑（墨）半，加色混合画不出黑色，因此太极图本体用「正常透明度」
直接画到屏幕上（压暗形成墨色）；环绕的发光粒子仍走加色粒子系统。

实现：预渲染一张固定朝向的太极 Surface（带缓存），每帧旋转后叠加，
即可得到旋转的太极图，性能稳定。
"""
import math

import pygame

# 太极底图缓存：key=(直径)，value=Surface(SRCALPHA)
_taiji_cache = {}


def _make_taiji(diameter, light=(235, 240, 255), dark=(12, 16, 30), alpha=200):
    """生成固定朝向的太极图（标准阴阳鱼），SRCALPHA，半透明以透出摄像头。"""
    key = (diameter, light, dark, alpha)
    cached = _taiji_cache.get(key)
    if cached is not None:
        return cached
    d = max(8, int(diameter))
    R = d // 2
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    c = (R, R)
    la = (*light, alpha)
    da = (*dark, alpha)
    eye = max(2, R // 8)
    # 1) 整圆为亮色
    pygame.draw.circle(surf, la, c, R)
    # 2) 右半圆为墨色（左亮右墨）
    pygame.draw.circle(surf, da, c, R, draw_top_right=True, draw_bottom_right=True)
    # 3) 上半墨色小圆 + 下半亮色小圆，构成 S 形分界
    pygame.draw.circle(surf, da, (R, R // 2), R // 2)
    pygame.draw.circle(surf, la, (R, R + R // 2), R // 2)
    # 4) 两个鱼眼（颜色相反）
    pygame.draw.circle(surf, la, (R, R // 2), eye)
    pygame.draw.circle(surf, da, (R, R + R // 2), eye)
    _taiji_cache[key] = surf
    return surf


class TaijiOrb:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.angle = 0.0

    def set_theme(self, theme):
        self.theme = theme

    def update(self):
        self.angle += 2.4   # 度/帧，旋转速度

    def emit_particles(self, center, radius, intensity=1.0):
        """环绕太极的阴阳两色粒子（走加色粒子系统）"""
        light = (235, 240, 255)
        dark_glow = self.theme["palette"][0]   # 用主题色作"阴"侧发光
        n = int(4 * intensity) + 2
        for k in range(n):
            color = light if k % 2 == 0 else dark_glow
            self.ps.spawn_orbit(center, count=1, radius=radius * 1.05,
                                speed=0.05, color=color)

    def draw(self, screen, center, radius):
        """把旋转的太极图以正常透明度画到屏幕（这样墨色半才可见）"""
        diameter = int(radius * 2)
        base = _make_taiji(diameter, light=self.theme["core"],
                           dark=self.theme["ink"] if sum(self.theme["ink"]) < 220
                           else (14, 18, 32))
        rotated = pygame.transform.rotate(base, self.angle)
        rect = rotated.get_rect(center=(int(center[0]), int(center[1])))
        screen.blit(rotated, rect)
