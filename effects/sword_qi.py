# -*- coding: utf-8 -*-
"""Sword-finger effect: willow-leaf trail plus NumPy directional sword particles."""
from collections import deque
import math

import numpy as np
import pygame

import config
from utils.math_utils import normalize, scale_color


CYAN = (70, 225, 255)
WHITE = (255, 255, 255)


class SwordQi:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self.slashes = []
        self._max_slashes = 8
        self.history_points = deque(maxlen=42)
        self.ring_center = np.array([config.WINDOW_WIDTH * 0.5, config.WINDOW_HEIGHT * 0.5], dtype=np.float32)
        self.ring_radius = 120.0
        self.ring_level = 0.0
        self.ring_formed = False
        self.ring_spin = 1.0
        self.ring_rotation = 0.0
        self.ring_tilt = 0.72
        self._circle_cd = 0
        self._spark_life = np.zeros(96, dtype=np.float32)
        self._spark_pos = np.zeros((96, 2), dtype=np.float32)
        self._spark_vel = np.zeros((96, 2), dtype=np.float32)
        self._spark_cursor = 0

        self.max_particles = 720
        self.p_pos = np.zeros((self.max_particles, 2), dtype=np.float32)
        self.p_vel = np.zeros((self.max_particles, 2), dtype=np.float32)
        self.p_life = np.zeros(self.max_particles, dtype=np.float32)
        self.p_max_life = np.ones(self.max_particles, dtype=np.float32)
        self.p_size = np.ones(self.max_particles, dtype=np.float32)
        self._cursor = 0

    def set_theme(self, theme):
        self.theme = theme

    def thrust(self, tip, direction, fx, length=260):
        dx, dy = normalize(*direction)
        if dx == 0 and dy == 0:
            dx, dy = 0, -1

        self.history_points.append((float(tip[0]), float(tip[1])))
        self._emit_directional_particles(tip, (dx, dy), count=5)
        self._draw_leaf_trail(fx, list(self.history_points), (dx, dy))
        self._track_sword_ring(tip)
        if self.ring_formed:
            self.ring_level = max(self.ring_level, 0.86)

        end = (tip[0] + dx * length * 0.35, tip[1] + dy * length * 0.35)
        pulse = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        self._draw_tip_sword(pulse, tip, (dx, dy))
        pygame.draw.line(pulse, (80, 230, 255, 42), tip, end, 5)
        pygame.draw.line(pulse, (230, 255, 255, 145), tip, end, 1)
        fx.blit(pulse, (0, 0), special_flags=pygame.BLEND_ADD)

    def _element_colors(self):
        element = self.theme.get("element", "wood")
        if element == "metal":
            return (245, 250, 255), (235, 210, 105), (190, 170, 255)
        if element == "water":
            return (225, 248, 255), (70, 185, 255), (120, 95, 255)
        if element == "fire":
            return (255, 248, 225), (255, 92, 42), (255, 190, 70)
        if element == "earth":
            return (255, 242, 200), (218, 166, 80), (90, 210, 180)
        return (232, 255, 238), (72, 232, 145), (255, 218, 82)

    def _draw_tip_sword(self, surf, tip, direction):
        core, aura, accent = self._element_colors()
        dx, dy = direction
        nx, ny = -dy, dx
        base_x = tip[0] + dx * 10
        base_y = tip[1] + dy * 10
        blade_len = 118
        blade_half = 8
        tang_len = 24
        tip_p = (base_x + dx * blade_len, base_y + dy * blade_len)
        shoulder_l = (base_x + nx * blade_half, base_y + ny * blade_half)
        shoulder_r = (base_x - nx * blade_half, base_y - ny * blade_half)
        mid_l = (base_x + dx * blade_len * 0.62 + nx * 4, base_y + dy * blade_len * 0.62 + ny * 4)
        mid_r = (base_x + dx * blade_len * 0.62 - nx * 4, base_y + dy * blade_len * 0.62 - ny * 4)
        pommel = (base_x - dx * tang_len, base_y - dy * tang_len)
        guard_l = (base_x - dx * 4 + nx * 20, base_y - dy * 4 + ny * 20)
        guard_r = (base_x - dx * 4 - nx * 20, base_y - dy * 4 - ny * 20)

        # Outer bloom and motion streaks.
        for k, alpha in ((4, 22), (3, 32), (2, 46)):
            tail = (base_x - dx * (22 + k * 8), base_y - dy * (22 + k * 8))
            pygame.draw.line(surf, (*aura, alpha), tail, tip_p, k * 4)

        blade_poly = [tip_p, mid_l, shoulder_l, shoulder_r, mid_r]
        pygame.draw.polygon(surf, (*aura, 92), blade_poly)
        pygame.draw.polygon(surf, (*WHITE, 230), [
            tip_p,
            (base_x + dx * blade_len * 0.58 + nx * 2.2, base_y + dy * blade_len * 0.58 + ny * 2.2),
            (base_x, base_y),
            (base_x + dx * blade_len * 0.58 - nx * 2.2, base_y + dy * blade_len * 0.58 - ny * 2.2),
        ])
        pygame.draw.line(surf, (*accent, 150), (base_x, base_y), tip_p, 1)
        pygame.draw.line(surf, (*core, 210), guard_l, guard_r, 3)
        pygame.draw.line(surf, (*aura, 135), pommel, (base_x, base_y), 5)
        pygame.draw.line(surf, (*WHITE, 180), pommel, (base_x, base_y), 2)
        pygame.draw.circle(surf, (*WHITE, 220), (int(tip_p[0]), int(tip_p[1])), 3)

    def _track_sword_ring(self, tip):
        if self._circle_cd > 0:
            self._circle_cd -= 1
        pts = np.array(self.history_points, dtype=np.float32)
        if len(pts) < 18:
            return
        recent = pts[-28:]
        center = recent.mean(axis=0)
        rel = recent - center
        radii = np.linalg.norm(rel, axis=1)
        mean_r = float(radii.mean())
        if mean_r < 45 or mean_r > 230:
            return
        roundness = float(radii.std() / max(1.0, mean_r))
        angles = np.unwrap(np.arctan2(rel[:, 1], rel[:, 0]))
        arc = float(angles[-1] - angles[0])
        closure = float(np.linalg.norm(recent[-1] - recent[0]))
        if roundness < 0.38 and abs(arc) > math.tau * 0.58 and closure < mean_r * 1.55 and self._circle_cd == 0:
            self.ring_center = self.ring_center * 0.35 + center * 0.65
            self.ring_radius = self.ring_radius * 0.45 + mean_r * 0.55
            self.ring_spin = 1.0 if arc >= 0 else -1.0
            first = not self.ring_formed or self.ring_level < 0.25
            self.ring_formed = True
            self.ring_level = 1.0
            self._circle_cd = 28
            if first:
                self._burst_ring_sparks(count=54)
        elif self.ring_formed:
            self.ring_center = self.ring_center * 0.86 + np.array(tip, dtype=np.float32) * 0.14

    def slash(self, center, sweep_dir):
        base_angle = 0.0 if sweep_dir >= 0 else math.pi
        self.slashes.append({
            "cx": center[0], "cy": center[1],
            "angle": base_angle, "radius": 16, "alive": True,
        })
        while len(self.slashes) > self._max_slashes:
            self.slashes.pop(0)
        self.ps.spawn_burst(center, count=22, speed=10)

    def _emit_directional_particles(self, tip, direction, count=5):
        dx, dy = direction
        perp = np.array([-dy, dx], dtype=np.float32)
        base = np.array([dx, dy], dtype=np.float32)
        idx = (np.arange(count) + self._cursor) % self.max_particles
        self._cursor = (self._cursor + count) % self.max_particles

        speed = np.random.uniform(13.0, 22.0, count).astype(np.float32)
        side_noise = np.random.normal(0.0, 0.38, count).astype(np.float32)
        forward_noise = np.random.uniform(-0.8, 1.2, count).astype(np.float32)
        self.p_pos[idx] = np.array(tip, dtype=np.float32) + perp * side_noise[:, None] * 3.0
        self.p_vel[idx] = base * (speed + forward_noise)[:, None] + perp * side_noise[:, None]
        self.p_life[idx] = np.random.uniform(18.0, 34.0, count)
        self.p_max_life[idx] = self.p_life[idx]
        self.p_size[idx] = np.random.uniform(1.4, 3.6, count)

    def _draw_leaf_trail(self, fx, history_points, direction):
        if len(history_points) < 2:
            return

        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        pts = np.array(history_points, dtype=np.float32)
        n = len(pts)

        left = []
        right = []
        for i in range(n):
            if i == 0:
                tangent = pts[1] - pts[0]
            elif i == n - 1:
                tangent = pts[-1] - pts[-2]
            else:
                tangent = pts[i + 1] - pts[i - 1]
            length = max(1.0, float(np.linalg.norm(tangent)))
            normal = np.array([-tangent[1] / length, tangent[0] / length], dtype=np.float32)

            t = i / max(1, n - 1)
            leaf_width = math.sin(math.pi * t) * 22.0
            leaf_width += 2.0 if i == n - 1 else 0.0
            left.append(pts[i] + normal * leaf_width)
            right.append(pts[i] - normal * leaf_width)

        polygon = [(int(p[0]), int(p[1])) for p in left + right[::-1]]
        if len(polygon) >= 3:
            pygame.draw.polygon(surf, (45, 210, 255, 62), polygon)

        for i in range(n - 1):
            t = i / max(1, n - 2)
            alpha = int(255 * (t ** 2.2))
            width = max(1, int(8 * math.sin(math.pi * t) + 1))
            c = _lerp_color(CYAN, WHITE, t)
            pygame.draw.line(
                surf,
                (*c, alpha),
                (int(pts[i, 0]), int(pts[i, 1])),
                (int(pts[i + 1, 0]), int(pts[i + 1, 1])),
                width,
            )

        head = pts[-1]
        pygame.draw.circle(surf, (255, 255, 255, 235), (int(head[0]), int(head[1])), 4)
        fx.blit(surf, (0, 0), special_flags=pygame.BLEND_ADD)

    def update(self):
        alive = self.p_life > 0
        self.p_pos[alive] += self.p_vel[alive]
        self.p_vel[alive] *= 0.91
        self.p_life[alive] -= 1.0
        self.ring_rotation += 0.035 * self.ring_spin * (0.45 + self.ring_level)
        if self.ring_formed:
            self.ring_level = max(0.0, self.ring_level - 0.008)
            if self.ring_level <= 0.02:
                self.ring_formed = False
        else:
            self.ring_level = max(0.0, self.ring_level - 0.045)
            self.ring_radius *= 0.985

        spark_alive = self._spark_life > 0
        self._spark_pos[spark_alive] += self._spark_vel[spark_alive]
        self._spark_vel[spark_alive] *= 0.94
        self._spark_life[spark_alive] -= 1.0

        for s in self.slashes:
            s["radius"] += 30
            if s["radius"] > 400:
                s["alive"] = False
        self.slashes = [s for s in self.slashes if s["alive"]]

    def draw(self, fx):
        self._draw_sword_ring(fx)
        self._draw_ring_sparks(fx)
        self._draw_particles(fx)
        self._draw_slashes(fx)

    def _ellipse_point(self, angle, radius=None):
        r = self.ring_radius if radius is None else radius
        x = math.cos(angle) * r
        y = math.sin(angle) * r * self.ring_tilt
        ca = math.cos(-0.16)
        sa = math.sin(-0.16)
        return np.array([
            self.ring_center[0] + x * ca - y * sa,
            self.ring_center[1] + x * sa + y * ca,
        ], dtype=np.float32)

    def _draw_sword_ring(self, fx):
        if self.ring_level <= 0.02:
            return
        core, aura, accent = self._element_colors()
        level = self.ring_level
        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        pts = [self._ellipse_point(self.ring_rotation + i * math.tau / 144) for i in range(145)]
        poly = [(float(p[0]), float(p[1])) for p in pts]
        pygame.draw.lines(surf, (*aura, int(76 * level)), False, poly, 5)
        pygame.draw.lines(surf, (*core, int(170 * level)), False, poly, 2)
        inner = [self._ellipse_point(self.ring_rotation * -0.55 + i * math.tau / 144, self.ring_radius * 0.82) for i in range(145)]
        pygame.draw.lines(surf, (*accent, int(42 * level)), False, [(float(p[0]), float(p[1])) for p in inner], 1)

        tick_count = 32
        for i in range(tick_count):
            a = self.ring_rotation * -0.45 + i * math.tau / tick_count
            p1 = self._ellipse_point(a, self.ring_radius * 0.94)
            p2 = self._ellipse_point(a, self.ring_radius * 1.04)
            pygame.draw.line(surf, (*core, int((92 if i % 4 == 0 else 45) * level)),
                             (float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1])), 1)
            if i % 8 == 0:
                pygame.draw.circle(surf, (*WHITE, int(150 * level)), (int(p2[0]), int(p2[1])), 3)

        # 剑胆光球
        cx, cy = self.ring_center
        pulse = 0.75 + 0.25 * math.sin(self.ring_rotation * 3.0)
        pygame.draw.circle(surf, (*aura, int(42 * level)), (int(cx), int(cy)), int(22 * pulse))
        pygame.draw.circle(surf, (*WHITE, int(125 * level)), (int(cx), int(cy)), int(5 + 3 * pulse))

        sword_count = 5 if self.theme.get("element") != "metal" else 6
        for i in range(sword_count):
            a = self.ring_rotation + i * math.tau / sword_count
            pos = self._ellipse_point(a)
            ahead = self._ellipse_point(a + 0.035 * self.ring_spin)
            tx, ty = ahead - pos
            ang = math.atan2(ty, tx)
            self._draw_flying_sword(surf, pos, ang, core, aura, level, i)
        fx.blit(surf, (0, 0), special_flags=pygame.BLEND_ADD)

    def _draw_flying_sword(self, surf, pos, angle, core, aura, level, seed):
        length = 42
        width = 6
        dx, dy = math.cos(angle), math.sin(angle)
        nx, ny = -dy, dx
        bob = math.sin(self.ring_rotation * 4.0 + seed) * 3.0
        cx, cy = pos[0] + nx * bob, pos[1] + ny * bob
        tip = (cx + dx * length * 0.62, cy + dy * length * 0.62)
        tail = (cx - dx * length * 0.38, cy - dy * length * 0.38)
        left = (cx + nx * width, cy + ny * width)
        right = (cx - nx * width, cy - ny * width)
        for k in range(4, 0, -1):
            off = k * 11
            alpha = int(30 * level * (5 - k))
            p1 = (tail[0] - dx * off, tail[1] - dy * off)
            pygame.draw.line(surf, (*aura, alpha), p1, tail, max(1, 5 - k))
        pygame.draw.polygon(surf, (*aura, int(82 * level)), [tip, left, tail, right])
        pygame.draw.polygon(surf, (*WHITE, int(210 * level)), [tip, (cx + nx * 2, cy + ny * 2), tail, (cx - nx * 2, cy - ny * 2)])
        guard1 = (tail[0] + nx * 8, tail[1] + ny * 8)
        guard2 = (tail[0] - nx * 8, tail[1] - ny * 8)
        pygame.draw.line(surf, (*core, int(160 * level)), guard1, guard2, 2)

    def _burst_ring_sparks(self, count=48):
        idx = (np.arange(count) + self._spark_cursor) % self._spark_life.size
        self._spark_cursor = int((self._spark_cursor + count) % self._spark_life.size)
        angles = np.linspace(0.0, math.tau, count, endpoint=False).astype(np.float32)
        ring = np.array([self._ellipse_point(float(a)) for a in angles], dtype=np.float32)
        tangent = np.stack([-np.sin(angles), np.cos(angles)], axis=1)
        self._spark_pos[idx] = ring
        self._spark_vel[idx] = tangent * self.ring_spin * np.random.uniform(1.5, 5.0, (count, 1)).astype(np.float32)
        self._spark_life[idx] = np.random.uniform(16, 34, count).astype(np.float32)

    def _draw_ring_sparks(self, fx):
        alive = np.flatnonzero(self._spark_life > 0)
        if alive.size == 0:
            return
        _, aura, _ = self._element_colors()
        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        for idx in alive:
            ratio = self._spark_life[idx] / 34.0
            x, y = self._spark_pos[idx]
            pygame.draw.circle(surf, (*aura, int(130 * ratio)), (int(x), int(y)), 2)
        fx.blit(surf, (0, 0), special_flags=pygame.BLEND_ADD)

    def _draw_particles(self, fx):
        alive = np.flatnonzero(self.p_life > 0)
        if alive.size == 0:
            return

        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        ratio = np.clip(self.p_life[alive] / self.p_max_life[alive], 0.0, 1.0)
        for idx, r in zip(alive, ratio):
            t = 1.0 - float(r)
            color = _lerp_color(CYAN, WHITE, min(1.0, t * 1.4))
            alpha = int(220 * float(r))
            x, y = self.p_pos[idx]
            if -20 <= x <= config.WINDOW_WIDTH + 20 and -20 <= y <= config.WINDOW_HEIGHT + 20:
                radius = max(1, int(self.p_size[idx] * (0.7 + r)))
                pygame.draw.circle(surf, (*color, alpha), (int(x), int(y)), radius)
                tail = self.p_vel[idx] * -0.75
                pygame.draw.line(surf, (*color, int(alpha * 0.45)),
                                 (int(x + tail[0]), int(y + tail[1])),
                                 (int(x), int(y)), max(1, radius))
        fx.blit(surf, (0, 0), special_flags=pygame.BLEND_ADD)

    def _draw_slashes(self, fx):
        core = self.theme["core"]
        for s in self.slashes:
            ratio = 1.0 - s["radius"] / 400.0
            if ratio <= 0:
                continue
            r = s["radius"]
            rect = pygame.Rect(s["cx"] - r, s["cy"] - r, r * 2, r * 2)
            try:
                pygame.draw.arc(fx, scale_color(core, ratio * 0.55),
                                rect, s["angle"] - 1.0, s["angle"] + 1.0,
                                max(1, int(5 * ratio)))
                pygame.draw.arc(fx, scale_color(WHITE, ratio),
                                rect, s["angle"] - 0.95, s["angle"] + 0.95,
                                max(1, int(2 * ratio)))
            except Exception:
                pass

    def clear(self):
        self.slashes.clear()
        self.history_points.clear()
        self.p_life.fill(0)
        self.ring_level = 0.0
        self.ring_formed = False
        self._spark_life.fill(0)


def _lerp_color(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
