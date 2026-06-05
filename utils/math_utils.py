# -*- coding: utf-8 -*-
"""
utils/math_utils.py —— 通用数学计算工具

距离、角度、插值、向量归一化等，供手势判定与粒子运动复用。
"""
import math
import random


def distance(p1, p2):
    """两点欧氏距离"""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def angle_between(p1, p2):
    """从 p1 指向 p2 的方向角（弧度）"""
    return math.atan2(p2[1] - p1[1], p2[0] - p1[0])


def lerp(a, b, t):
    """线性插值，t 在 [0,1]"""
    return a + (b - a) * t


def lerp_point(p1, p2, t):
    """两点之间插值"""
    return (lerp(p1[0], p2[0], t), lerp(p1[1], p2[1], t))


def lerp_color(c1, c2, t):
    """两个 RGB 颜色之间插值"""
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def normalize(vx, vy):
    """向量归一化，返回单位向量；零向量返回 (0,0)"""
    length = math.hypot(vx, vy)
    if length < 1e-6:
        return 0.0, 0.0
    return vx / length, vy / length


def midpoint(p1, p2):
    """中点"""
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def clamp(value, low, high):
    return max(low, min(high, value))


def random_unit_vector():
    """随机方向单位向量"""
    a = random.uniform(0, math.tau)
    return math.cos(a), math.sin(a)


def scale_color(color, factor):
    """按亮度系数缩放颜色（用于加色混合时控制强弱）"""
    return (
        int(clamp(color[0] * factor, 0, 255)),
        int(clamp(color[1] * factor, 0, 255)),
        int(clamp(color[2] * factor, 0, 255)),
    )
