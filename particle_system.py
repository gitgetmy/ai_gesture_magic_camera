# -*- coding: utf-8 -*-
"""
particle_system.py —— 粒子系统管理

统一管理所有粒子的生成、更新、删除。
对外提供若干「生成器」，供各特效模块调用：
  - spawn_orbit   围绕中心旋转（能量球）
  - spawn_attract 向中心聚集（捏合 / 冰晶）
  - spawn_burst   从中心爆炸扩散（握拳 / 冲击波）
  - spawn_flame   火焰上飘
  - spawn_trail   拖尾
  - ambient       环境星尘漂浮
"""
import math
import random

import config
from particle import Particle
from utils.math_utils import random_unit_vector


class ParticleSystem:
    def __init__(self, theme):
        self.particles = []
        self.theme = theme
        self.max_particles = config.MAX_PARTICLE_COUNT

    # ---------- 主题 ----------
    def set_theme(self, theme):
        self.theme = theme

    def _color(self):
        return random.choice(self.theme["palette"])

    def _rich_color(self):
        """更丰富的取色：优先从多色相光谱里取，让爆发/旋转更多彩"""
        pool = self.theme.get("spectrum") or self.theme["palette"]
        return random.choice(pool)

    # ---------- 容量控制 ----------
    def _room(self, n):
        """还能再加多少个，避免超过上限拖垮性能"""
        return max(0, min(n, self.max_particles - len(self.particles)))

    @property
    def count(self):
        return len(self.particles)

    # ---------- 生成器 ----------
    def spawn_orbit(self, center, count=12, radius=40, speed=0.04, color=None):
        """能量球：围绕中心旋转的粒子。color 为 None 时从主题取色。"""
        for _ in range(self._room(count)):
            angle = random.uniform(0, math.tau)
            r = radius * random.uniform(0.6, 1.1)
            self.particles.append(Particle(
                x=center[0], y=center[1], color=color or self._color(),
                size=random.uniform(2.5, 5), life=random.randint(25, 45),
                ptype="orbit", angle=angle, orbit_radius=r,
                orbit_speed=speed * random.uniform(0.8, 1.4) * random.choice([1, -1]),
                target=center,
            ))

    def spawn_attract(self, center, count=10, ice=False):
        """捏合 / 冰晶：从四周向中心聚集"""
        for _ in range(self._room(count)):
            ux, uy = random_unit_vector()
            dist = random.uniform(40, 110)
            color = (180, 220, 255) if ice else self._color()
            self.particles.append(Particle(
                x=center[0] + ux * dist, y=center[1] + uy * dist,
                vx=0, vy=0, color=color,
                size=random.uniform(2, 4), life=random.randint(20, 40),
                ptype="ice" if ice else "attract", drag=0.92, target=center,
            ))

    def spawn_burst(self, center, count=60, speed=8, color=None):
        """爆炸扩散：握拳 / 冲击波 / 双手释放。无指定色时用多色光谱，更绚烂。"""
        for _ in range(self._room(count)):
            ux, uy = random_unit_vector()
            s = speed * random.uniform(0.4, 1.3)
            self.particles.append(Particle(
                x=center[0], y=center[1], vx=ux * s, vy=uy * s,
                color=color or self._rich_color(),
                size=random.uniform(3, 6.5), life=random.randint(22, 46),
                ptype="spark", drag=0.93,
            ))

    def spawn_directional(self, center, base_angle, spread, count, speed,
                          color=None, gravity=0.0, life=(24, 46), size=(2.5, 5.5)):
        """
        定向扇形喷射：从 center 沿 base_angle 方向、在 ±spread 角度范围内喷出粒子。
        gravity<0 表示上飘（凤羽/升腾）。color=None 时用多色光谱。
        """
        import math as _m
        for _ in range(self._room(count)):
            a = base_angle + random.uniform(-spread, spread)
            s = speed * random.uniform(0.5, 1.2)
            self.particles.append(Particle(
                x=center[0], y=center[1],
                vx=_m.cos(a) * s, vy=_m.sin(a) * s,
                color=color or self._rich_color(),
                size=random.uniform(*size), life=random.randint(*life),
                ptype="spark", drag=0.97, gravity=gravity,
            ))

    def spawn_flame(self, center, count=None):
        """火焰：掌心附近生成，向上飘动"""
        count = count or config.FLAME_PARTICLE_COUNT // 4
        flame_colors = [(255, 80, 30), (255, 150, 40), (255, 210, 90)]
        for _ in range(self._room(count)):
            self.particles.append(Particle(
                x=center[0] + random.uniform(-config.FLAME_SPREAD, config.FLAME_SPREAD),
                y=center[1] + random.uniform(-5, 10),
                vx=random.uniform(-0.8, 0.8),
                vy=config.FLAME_SPEED_Y * random.uniform(0.6, 1.3),
                color=random.choice(flame_colors),
                size=random.uniform(4, 8), life=random.randint(20, config.FLAME_LIFE),
                ptype="flame", drag=0.98,
            ))

    def spawn_trail(self, pos, velocity, count_base=3):
        """星尘拖尾：移动越快粒子越多"""
        count = int(count_base + min(20, velocity * 6))
        for _ in range(self._room(count)):
            self.particles.append(Particle(
                x=pos[0] + random.uniform(-6, 6),
                y=pos[1] + random.uniform(-6, 6),
                vx=random.uniform(-0.5, 0.5), vy=random.uniform(-0.5, 0.5),
                color=self._color(), size=random.uniform(2, 4),
                life=random.randint(15, 30), ptype="trail", drag=0.95,
            ))

    def ambient(self, width, height, target_count):
        """环境星尘：无手时缓慢漂浮，维持一定数量"""
        living_ambient = sum(1 for p in self.particles if p.ptype == "basic")
        need = self._room(target_count - living_ambient)
        for _ in range(need):
            self.particles.append(Particle(
                x=random.uniform(0, width), y=random.uniform(0, height),
                vx=random.uniform(-0.3, 0.3), vy=random.uniform(-0.3, 0.3),
                color=self._color(), size=random.uniform(1.5, 3),
                life=random.randint(120, 300), ptype="basic", drag=0.99,
            ))

    # ---------- 更新 / 绘制 ----------
    def update(self):
        for p in self.particles:
            p.update()
        # 删除消亡粒子
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, fx_surface):
        for p in self.particles:
            p.draw(fx_surface)

    def clear(self):
        self.particles.clear()
