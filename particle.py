# -*- coding: utf-8 -*-
"""
particle.py —— 单个粒子类

粒子支持多种行为：自由运动、向目标点吸引、围绕目标旋转、重力/上飘等。
绘制时把自身画到「特效层」上（加色混合），透明度由生命周期映射为亮度。
"""
import math

from utils.draw_utils import draw_glow
from utils.math_utils import normalize, distance


class Particle:
    __slots__ = (
        "x", "y", "vx", "vy", "size", "color", "life", "max_life",
        "ptype", "gravity", "drag", "angle", "orbit_radius", "orbit_speed",
        "target",
    )

    def __init__(self, x, y, vx=0.0, vy=0.0, color=(255, 255, 255),
                 size=3.0, life=40, ptype="basic",
                 gravity=0.0, drag=1.0,
                 orbit_radius=0.0, orbit_speed=0.0, angle=0.0, target=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.life = life
        self.max_life = max(1, life)
        self.ptype = ptype          # basic / orbit / attract / flame / ice / trail / spark
        self.gravity = gravity      # 每帧叠加到 vy
        self.drag = drag            # 速度阻尼（<1 减速）
        self.angle = angle          # orbit 用：当前角度
        self.orbit_radius = orbit_radius
        self.orbit_speed = orbit_speed
        self.target = target        # (tx, ty) 吸引 / 旋转中心

    @property
    def alive(self):
        return self.life > 0

    @property
    def life_ratio(self):
        """剩余生命比例，1->新生，0->消亡"""
        return max(0.0, self.life / self.max_life)

    def update(self):
        """按粒子类型更新一帧"""
        if self.ptype == "orbit" and self.target is not None:
            # 围绕目标点做圆周运动
            self.angle += self.orbit_speed
            self.x = self.target[0] + math.cos(self.angle) * self.orbit_radius
            self.y = self.target[1] + math.sin(self.angle) * self.orbit_radius
        elif self.ptype in ("attract", "ice") and self.target is not None:
            # 向目标点加速聚集
            dx = self.target[0] - self.x
            dy = self.target[1] - self.y
            nx, ny = normalize(dx, dy)
            pull = 0.6 if self.ptype == "attract" else 0.35
            self.vx += nx * pull
            self.vy += ny * pull
            self.vx *= self.drag
            self.vy *= self.drag
            self.x += self.vx
            self.y += self.vy
        else:
            # 自由运动（basic / flame / trail / spark）
            self.vy += self.gravity
            self.vx *= self.drag
            self.vy *= self.drag
            self.x += self.vx
            self.y += self.vy

        # 火焰随生命收缩
        if self.ptype == "flame":
            self.size *= 0.97

        self.life -= 1

    def draw(self, fx_surface):
        """画到特效层（加色）。生命越接近结束越暗，实现淡出。"""
        if self.size < 0.5:
            return
        brightness = self.life_ratio
        # 用亮度缩放颜色：黑色不影响加色背景，从而实现淡出
        c = (
            int(self.color[0] * brightness),
            int(self.color[1] * brightness),
            int(self.color[2] * brightness),
        )
        # spark/trail 用更小更亮的核心；其余带柔光晕
        layers = 3 if self.ptype in ("trail", "spark") else 4
        draw_glow(fx_surface, (self.x, self.y), self.size, c, layers=layers)
