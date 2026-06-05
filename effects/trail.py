# -*- coding: utf-8 -*-
"""
effects/trail.py —— 星尘拖尾特效

手部快速移动时，在移动路径上生成粒子拖尾，逐渐变透明。
移动越快粒子越多。具体由粒子系统的 spawn_trail 实现，这里做语义封装。
"""


class Trail:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme

    def emit(self, pos, velocity):
        """pos 当前位置，velocity 归一化速度（越大拖尾越浓）"""
        self.ps.spawn_trail(pos, velocity)
