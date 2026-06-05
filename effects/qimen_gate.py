# -*- coding: utf-8 -*-
"""Qimen Xiumen geometric barrier."""
import math

import numpy as np
import pygame

import config


WHITE = (235, 248, 255)
ICE_BLUE = (70, 150, 255)
DEEP_BLUE = (10, 36, 82)


class QimenGate:
    def __init__(self, theme):
        self.theme = theme
        self.center = np.array([config.WINDOW_WIDTH * 0.5, config.WINDOW_HEIGHT * 0.45], dtype=np.float32)
        self.level = 0.0
        self.radius = 0.0
        self.time = 0.0
        self.font = pygame.font.SysFont("microsoftyahei,simhei,arial", 18, bold=True)
        self.small_font = pygame.font.SysFont("consolas,microsoftyahei,simhei,arial", 10)
        self.vertices, self.edges = self._make_icosahedron()
        self._init_code_ash()

    def set_theme(self, theme):
        self.theme = theme

    def clear(self):
        self.level = 0.0
        self.radius = 0.0
        self.ash_life[:] = 0

    @property
    def active(self):
        return self.level > 0.08

    def _make_icosahedron(self):
        phi = (1.0 + 5.0 ** 0.5) / 2.0
        pts = []
        for a in (-1, 1):
            for b in (-phi, phi):
                pts.append((0, a, b))
                pts.append((a, b, 0))
                pts.append((b, 0, a))
        v = np.array(pts, dtype=np.float32)
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        d = np.linalg.norm(v[:, None, :] - v[None, :, :], axis=2)
        nearest = np.partition(d[d > 0], 0)[0]
        edges = np.argwhere((d > nearest * 0.92) & (d < nearest * 1.08))
        edges = [(int(a), int(b)) for a, b in edges if a < b]
        return v, edges

    def _init_code_ash(self):
        self.max_ash = 180
        self.ash_pos = np.zeros((self.max_ash, 2), dtype=np.float32)
        self.ash_vel = np.zeros((self.max_ash, 2), dtype=np.float32)
        self.ash_life = np.zeros(self.max_ash, dtype=np.float32)
        self.ash_max_life = np.ones(self.max_ash, dtype=np.float32)
        self.ash_kind = np.zeros(self.max_ash, dtype=np.int16)
        self.cursor = 0

    def emit(self, center):
        target = np.array(center, dtype=np.float32)
        self.center = self.center * 0.55 + target * 0.45
        first = self.level < 0.08
        self.level = min(1.0, self.level + 0.18)
        self.radius = min(235.0, max(self.radius, 38.0) + 18.0)
        if first:
            self.radius = 42.0
            self._spawn_ash(self.center, 52, burst=True)

    def update(self):
        self.time += 1.0
        self.level = max(0.0, self.level - 0.055)
        target_radius = 210.0 * (0.35 + self.level * 0.65)
        self.radius += (target_radius - self.radius) * 0.09

        alive = self.ash_life > 0
        if np.any(alive):
            self.ash_vel[alive] *= 0.965
            self.ash_pos[alive] += self.ash_vel[alive]
            self.ash_life[alive] -= 1.7

        if self.level > 0.1 and int(self.time) % 5 == 0:
            ang = np.random.uniform(0.0, math.tau)
            contact = self.center + np.array([math.cos(ang), math.sin(ang)], dtype=np.float32) * self.radius
            self._spawn_ash(contact, 5, burst=False)

    def _spawn_ash(self, origin, count, burst=False):
        idx = (np.arange(count) + self.cursor) % self.max_ash
        self.cursor = int((self.cursor + count) % self.max_ash)
        angles = np.random.uniform(0.0, math.tau, count).astype(np.float32)
        radial = np.stack([np.cos(angles), np.sin(angles)], axis=1)
        speed = np.random.uniform(0.8, 5.2 if burst else 2.8, (count, 1)).astype(np.float32)
        self.ash_pos[idx] = origin + np.random.normal(0.0, 10.0, (count, 2))
        self.ash_vel[idx] = radial * speed + np.array([0.0, -0.25], dtype=np.float32)
        self.ash_life[idx] = np.random.uniform(12, 28 if burst else 20, count).astype(np.float32)
        self.ash_max_life[idx] = self.ash_life[idx]
        self.ash_kind[idx] = np.random.randint(0, 8, count)

    def draw_void(self, screen):
        if self.level <= 0.08:
            return
        strength = min(1.0, self.level)
        veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        veil.fill((4, 6, 10, int(226 * strength)))
        screen.blit(veil, (0, 0))

        horizon = int(config.WINDOW_HEIGHT * 0.58)
        slab = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(slab, (18, 20, 24, int(205 * strength)),
                         (0, horizon, config.WINDOW_WIDTH, config.WINDOW_HEIGHT - horizon))
        for i in range(9):
            y = horizon + i * 32
            alpha = int((58 - i * 4) * strength)
            pygame.draw.line(slab, (48, 56, 68, alpha), (0, y), (config.WINDOW_WIDTH, y), 1)
        for i in range(7):
            x = int(i * config.WINDOW_WIDTH / 6)
            pygame.draw.line(slab, (31, 37, 48, int(30 * strength)), (x, horizon),
                             (x - 80, config.WINDOW_HEIGHT), 1)
        screen.blit(slab, (0, 0))

    def _project(self):
        ry = self.time * 0.012
        rx = -0.65 + math.sin(self.time * 0.011) * 0.08
        cy, sy = math.cos(ry), math.sin(ry)
        cx, sx = math.cos(rx), math.sin(rx)
        rot_y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
        rot_x = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
        pts = self.vertices @ rot_y.T @ rot_x.T
        depth = 2.5 / (2.9 - pts[:, 2])
        xy = pts[:, :2] * depth[:, None] * self.radius + self.center
        return xy, pts[:, 2]

    def draw(self, fx):
        if self.level <= 0.01 and not np.any(self.ash_life > 0):
            return
        layer = pygame.Surface(fx.get_size(), pygame.SRCALPHA)

        if self.level > 0.01:
            xy, depth = self._project()
            alpha = int(220 * self.level)
            cx, cy = self.center
            for mul, a in ((1.36, 34), (1.02, 48), (0.72, 30)):
                pygame.draw.circle(layer, (55, 130, 255, int(a * self.level)),
                                   (int(cx), int(cy)), int(self.radius * mul), 1)
            pygame.draw.circle(layer, (235, 248, 255, int(95 * self.level)),
                               (int(cx), int(cy)), int(self.radius * 0.15), 1)
            pygame.draw.circle(layer, (85, 160, 255, int(38 * self.level)),
                               (int(cx), int(cy)), int(self.radius * 0.28), 1)

            inner = (xy - self.center) * 0.64 + self.center
            for a, b in self.edges[::2]:
                pygame.draw.line(layer, (70, 145, 255, int(42 * self.level)),
                                 (float(inner[a][0]), float(inner[a][1])),
                                 (float(inner[b][0]), float(inner[b][1])), 1)

            for a, b in self.edges:
                da = (depth[a] + depth[b]) * 0.5
                col = (220, 242, 255, max(34, int(alpha * (0.48 + da * 0.16))))
                pygame.draw.line(layer, col, (float(xy[a][0]), float(xy[a][1])),
                                 (float(xy[b][0]), float(xy[b][1])), 1)
                if (a + b) % 5 == int(self.time // 10) % 5:
                    pygame.draw.line(layer, (120, 190, 255, int(42 * self.level)),
                                     (float(inner[a][0]), float(inner[a][1])),
                                     (float(xy[a][0]), float(xy[a][1])), 1)

            for i, p in enumerate(xy):
                node_alpha = int((105 + 48 * math.sin(self.time * 0.09 + i)) * self.level)
                pygame.draw.circle(layer, (210, 238, 255, node_alpha), (int(p[0]), int(p[1])), 2)
                if i % 3 == int(self.time // 18) % 3:
                    glyph = "休" if i % 2 == 0 else "生"
                    text = self.font.render(glyph, True, WHITE)
                    text.set_alpha(int(112 * self.level))
                    layer.blit(text, (int(p[0]) + 6, int(p[1]) - 14))

            for a, b in self.edges[::3]:
                mid = (xy[a] + xy[b]) * 0.5
                if (a + b + int(self.time // 8)) % 4 == 0:
                    pygame.draw.circle(layer, (130, 200, 255, int(58 * self.level)),
                                       (int(mid[0]), int(mid[1])), 1)
                else:
                    end = mid + (xy[b] - xy[a]) * 0.055
                    pygame.draw.line(layer, (95, 170, 255, int(34 * self.level)),
                                     (float(mid[0]), float(mid[1])),
                                     (float(end[0]), float(end[1])), 1)

        alive = self.ash_life > 0
        if np.any(alive):
            p = self.ash_pos[alive]
            life_ratio = np.clip(self.ash_life[alive] / self.ash_max_life[alive], 0.0, 1.0)
            kinds = self.ash_kind[alive]
            for (x, y), ratio, kind in zip(p, life_ratio, kinds):
                alpha = int(92 * ratio)
                if kind % 3 == 0:
                    pygame.draw.circle(layer, (170, 215, 255, alpha), (int(x), int(y)), 1)
                elif kind % 3 == 1:
                    pygame.draw.line(layer, (160, 205, 245, alpha),
                                     (int(x), int(y)), (int(x + 3), int(y - 2)), 1)
                else:
                    pygame.draw.circle(layer, (90, 98, 110, int(alpha * 0.75)), (int(x), int(y)), 1)

        fx.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)
