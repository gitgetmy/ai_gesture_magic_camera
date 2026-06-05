# -*- coding: utf-8 -*-
"""Natural lightning cast from the index finger, with a short star-sky flash."""
import math
import random

import pygame

import config
from utils.draw_utils import draw_glow
from utils.math_utils import normalize


class _ArcGhost:
    __slots__ = ("points", "color", "width", "life", "max_life")

    def __init__(self, points, color, width, max_life=10):
        self.points = points
        self.color = color
        self.width = width
        self.max_life = max_life
        self.life = max_life

    @property
    def alive(self):
        return self.life > 0

    def fade(self):
        self.life -= 1


class Lightning:
    def __init__(self, particle_system, theme):
        self.ps = particle_system
        self.theme = theme
        self._ghosts = []
        self._max_ghosts = 14
        self._flash_ref = None
        self._shake_ref = None
        self._cooldown = 0
        self._star_life = 0
        self._stars = [
            (
                random.randrange(config.WINDOW_WIDTH),
                random.randrange(config.WINDOW_HEIGHT),
                random.randrange(1, 3),
                random.uniform(0.35, 1.0),
            )
            for _ in range(190)
        ]

    def set_theme(self, theme):
        self.theme = theme

    def set_flash(self, flash_obj):
        self._flash_ref = flash_obj

    def set_shake_ref(self, shake_list):
        self._shake_ref = shake_list

    def emit(self, tip, direction, fx_surface):
        dx, dy = normalize(*direction)
        if dx == 0 and dy == 0:
            dx, dy = 0, -1

        core = self.theme["core"]
        accent = self.theme.get("accent", core)

        if self._cooldown > 0:
            self._star_life = max(self._star_life, 4)
            draw_glow(fx_surface, tip, 14, core, layers=4)
            return

        self._cooldown = 5
        self._star_life = 18

        end = _ray_to_border(tip[0], tip[1], dx, dy)
        main = _natural_bolt(tip, end, roughness=54, segments=24)

        _draw_poly_bolt(fx_surface, main, (55, 115, 255), 8)
        _draw_poly_bolt(fx_surface, main, (145, 215, 255), 4)
        _draw_poly_bolt(fx_surface, main, (255, 255, 255), 1)
        self._ghosts.append(_ArcGhost(main, (175, 225, 255), 3, max_life=12))

        base_ang = math.atan2(dy, dx)
        for _ in range(random.randint(3, 5)):
            start = random.choice(main[3:max(4, len(main) - 3)])
            branch_ang = base_ang + random.choice([-1, 1]) * random.uniform(0.45, 1.15)
            branch_len = random.uniform(80, 220)
            branch_end = (
                start[0] + math.cos(branch_ang) * branch_len,
                start[1] + math.sin(branch_ang) * branch_len,
            )
            branch = _natural_bolt(start, branch_end, roughness=26, segments=9)
            color = random.choice([(120, 190, 255), (210, 235, 255), accent])
            _draw_poly_bolt(fx_surface, branch, color, 1)
            self._ghosts.append(_ArcGhost(branch, color, 2, max_life=7))

        draw_glow(fx_surface, tip, 22, (255, 255, 255), layers=6)
        draw_glow(fx_surface, tip, 30, accent, layers=4)
        draw_glow(fx_surface, end, 34, (150, 210, 255), layers=4)
        draw_glow(fx_surface, end, 12, (255, 255, 255), layers=4)
        self.ps.spawn_burst(end, count=18, speed=8)
        self.ps.spawn_burst(tip, count=4, speed=5, color=core)

        if self._flash_ref is not None:
            self._flash_ref.trigger(72, tint=(165, 210, 255))
        if self._shake_ref is not None and len(self._shake_ref) > 0:
            self._shake_ref[0] = max(self._shake_ref[0], 5.0)

    def update(self):
        for g in self._ghosts:
            g.fade()
        self._ghosts = [g for g in self._ghosts if g.alive]
        while len(self._ghosts) > self._max_ghosts:
            self._ghosts.pop(0)
        if self._cooldown > 0:
            self._cooldown -= 1
        if self._star_life > 0:
            self._star_life -= 1

    def draw_starfield(self, screen):
        if self._star_life <= 0:
            return
        alpha = int(178 * min(1.0, self._star_life / 10.0))
        sky = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        sky.fill((2, 4, 18, alpha))
        for x, y, r, b in self._stars:
            twinkle = 0.65 + 0.35 * math.sin(self._star_life * 0.8 + x * 0.01)
            c = int(210 * b * twinkle)
            pygame.draw.circle(sky, (c, c, min(255, c + 35), int(alpha * 0.78)), (x, y), r)
        screen.blit(sky, (0, 0))

    def draw_ghosts(self, fx_surface):
        for g in self._ghosts:
            alpha = g.life / g.max_life
            c = tuple(int(v * alpha) for v in g.color)
            w = max(1, int(g.width * alpha))
            if len(g.points) >= 2:
                pygame.draw.lines(fx_surface, c, False,
                                  [(int(p[0]), int(p[1])) for p in g.points], w)

    def clear(self):
        self._ghosts.clear()
        self._star_life = 0
        self._cooldown = 0


def _natural_bolt(start, end, roughness=42, segments=18):
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    pts = []
    for i in range(segments + 1):
        t = i / segments
        taper = math.sin(math.pi * t)
        offset = random.uniform(-roughness, roughness) * taper
        zig = math.sin(t * math.tau * random.uniform(2.0, 4.0)) * roughness * 0.20 * taper
        pts.append((sx + dx * t + nx * (offset + zig),
                    sy + dy * t + ny * (offset + zig)))
    pts[0] = start
    pts[-1] = end
    return pts


def _draw_poly_bolt(surface, points, color, width):
    if len(points) < 2:
        return
    if width >= 6:
        halo = tuple(max(0, min(255, int(c * 0.45))) for c in color)
        pygame.draw.lines(surface, halo, False, [(int(x), int(y)) for x, y in points], width)
    pygame.draw.lines(surface, color, False, [(int(x), int(y)) for x, y in points], max(1, width))


def _ray_to_border(x, y, dx, dy):
    w, h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
    t_candidates = []
    if dx > 1e-6:
        t_candidates.append((w - x) / dx)
    elif dx < -1e-6:
        t_candidates.append((0 - x) / dx)
    if dy > 1e-6:
        t_candidates.append((h - y) / dy)
    elif dy < -1e-6:
        t_candidates.append((0 - y) / dy)
    t = min([t for t in t_candidates if t > 0], default=config.LIGHTNING_LENGTH)
    t = max(t, config.LIGHTNING_LENGTH)
    return (x + dx * t, y + dy * t)
