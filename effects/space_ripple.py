# -*- coding: utf-8 -*-
"""Hands-together Zen scene transition with NumPy slow falling leaves."""
from pathlib import Path
import math

import numpy as np
import pygame

import config


ZEN_BG = Path(__file__).resolve().parent.parent / "assets" / "zen_scene" / "taoist_meditation_bg.png"
LEAF_SPRITE = Path(__file__).resolve().parent.parent / "assets" / "season_particles" / "autumn_leaf.png"


class SpaceRipple:
    REALITY = "reality"
    FADE_BLACK = "fade_black"
    FADE_ZEN = "fade_zen"
    ZEN = "zen"

    def __init__(self):
        self.state = self.REALITY
        self.hold_time = 0.0
        self.state_time = 0.0
        self.black_alpha = 0
        self.zen_alpha = 0
        self._zen_bg = None
        self._leaf_sprite = None
        self._rng = np.random.default_rng()
        self._leaf_count = 78
        self._time = 0.0
        self._init_leaves()

    def _init_leaves(self):
        n = self._leaf_count
        self.leaf_pos = np.zeros((n, 2), dtype=np.float32)
        self.leaf_base_x = np.zeros(n, dtype=np.float32)
        self.leaf_speed_y = self._rng.uniform(6.0, 17.0, n).astype(np.float32)
        self.leaf_sway = self._rng.uniform(8.0, 28.0, n).astype(np.float32)
        self.leaf_phase = self._rng.uniform(0.0, math.tau, n).astype(np.float32)
        self.leaf_alpha = self._rng.uniform(55.0, 130.0, n).astype(np.float32)
        self.leaf_size = self._rng.integers(0, 4, n, dtype=np.int16)
        self.leaf_angle = self._rng.integers(0, 8, n, dtype=np.int16)
        self._reset_leaves(np.ones(n, dtype=bool), scatter=True)

    def _load_assets(self):
        if self._zen_bg is None:
            if ZEN_BG.exists():
                raw = pygame.image.load(str(ZEN_BG)).convert()
                self._zen_bg = _cover_scale(raw, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
            else:
                self._zen_bg = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)).convert()
                self._zen_bg.fill((8, 10, 16))
        if self._leaf_sprite is None:
            self._leaf_sprite = _make_leaf_frames()

    def update(self, is_hands_together=False, center=None, dt=1.0 / 60.0):
        dt = max(0.0, min(0.05, float(dt)))
        self._time += dt

        if is_hands_together:
            self.hold_time += dt
        else:
            self.hold_time = 0.0

        if self.state == self.REALITY:
            self.black_alpha = 0
            self.zen_alpha = 0
            if self.hold_time >= 0.25:
                self.state = self.FADE_BLACK
                self.state_time = 0.0
        elif self.state == self.FADE_BLACK:
            self.state_time += dt
            p = min(1.0, self.state_time / 0.55)
            self.black_alpha = int(255 * _smoothstep(p))
            self.zen_alpha = 0
            if p >= 1.0:
                self.state = self.FADE_ZEN
                self.state_time = 0.0
        elif self.state == self.FADE_ZEN:
            self.state_time += dt
            p = min(1.0, self.state_time / 0.55)
            self.black_alpha = int(255 * (1.0 - _smoothstep(p)))
            self.zen_alpha = int(255 * _smoothstep(p))
            self._update_leaves(dt)
            if p >= 1.0:
                self.state = self.ZEN
                self.state_time = 0.0
                self.black_alpha = 0
                self.zen_alpha = 255
        elif self.state == self.ZEN:
            self.black_alpha = 0
            self.zen_alpha = 255
            self._update_leaves(dt)
            if not is_hands_together:
                self.state = self.REALITY
                self.hold_time = 0.0
                self.state_time = 0.0

    def _update_leaves(self, dt):
        self.leaf_pos[:, 1] += self.leaf_speed_y * dt
        self.leaf_pos[:, 0] = self.leaf_base_x + np.sin(self._time * 0.65 + self.leaf_phase) * self.leaf_sway
        self.leaf_angle = (self.leaf_angle + (self.leaf_speed_y > 12.0).astype(np.int16)) % 8
        offscreen = self.leaf_pos[:, 1] > config.WINDOW_HEIGHT + 40
        if np.any(offscreen):
            self._reset_leaves(offscreen, scatter=False)

    def _reset_leaves(self, mask, scatter=False):
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return
        m = idx.size
        self.leaf_base_x[idx] = self._rng.uniform(-40, config.WINDOW_WIDTH + 40, m)
        self.leaf_pos[idx, 0] = self.leaf_base_x[idx]
        if scatter:
            self.leaf_pos[idx, 1] = self._rng.uniform(-60, config.WINDOW_HEIGHT, m)
        else:
            self.leaf_pos[idx, 1] = self._rng.uniform(-90, -20, m)
        self.leaf_speed_y[idx] = self._rng.uniform(6.0, 17.0, m)
        self.leaf_sway[idx] = self._rng.uniform(8.0, 28.0, m)
        self.leaf_phase[idx] = self._rng.uniform(0.0, math.tau, m)
        self.leaf_alpha[idx] = self._rng.uniform(55.0, 130.0, m)
        self.leaf_size[idx] = self._rng.integers(0, 4, m, dtype=np.int16)
        self.leaf_angle[idx] = self._rng.integers(0, 8, m, dtype=np.int16)

    def draw_dim(self, screen):
        self.draw_scene(screen)

    def draw_scene(self, screen):
        if self.state == self.REALITY:
            return
        self._load_assets()
        if self.zen_alpha > 0:
            bg = self._zen_bg.copy()
            bg.set_alpha(self.zen_alpha)
            screen.blit(bg, (0, 0))
            self._draw_leaves(screen, self.zen_alpha / 255.0)
        if self.black_alpha > 0:
            black = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
            black.fill((0, 0, 0, self.black_alpha))
            screen.blit(black, (0, 0))

    def _draw_leaves(self, screen, scene_alpha):
        frames = self._leaf_sprite
        for i in range(self._leaf_count):
            frame = frames[int(self.leaf_size[i]) * 8 + int(self.leaf_angle[i])]
            frame.set_alpha(int(self.leaf_alpha[i] * scene_alpha))
            rect = frame.get_rect(center=(int(self.leaf_pos[i, 0]), int(self.leaf_pos[i, 1])))
            screen.blit(frame, rect)

    def draw(self, fx):
        return

    def clear(self):
        self.state = self.REALITY
        self.hold_time = 0.0
        self.state_time = 0.0
        self.black_alpha = 0
        self.zen_alpha = 0


def _make_leaf_frames():
    if LEAF_SPRITE.exists():
        src = pygame.image.load(str(LEAF_SPRITE)).convert()
        src = _crop_nonblack(src)
        src = _black_to_alpha(src)
    else:
        src = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(src, (125, 100, 80, 160), (8, 14, 24, 12))
    frames = []
    for size in (12, 16, 20, 25):
        base = pygame.transform.smoothscale(src, (size, size)).convert_alpha()
        base.fill((115, 105, 90), special_flags=pygame.BLEND_RGB_MULT)
        for angle in range(0, 360, 45):
            frames.append(pygame.transform.rotate(base, angle).convert_alpha())
    return frames


def _cover_scale(surf, width, height):
    sw, sh = surf.get_size()
    scale = max(width / sw, height / sh)
    scaled = pygame.transform.smoothscale(surf, (int(sw * scale), int(sh * scale)))
    x = max(0, (scaled.get_width() - width) // 2)
    y = max(0, (scaled.get_height() - height) // 2)
    return scaled.subsurface((x, y, width, height)).copy().convert()


def _crop_nonblack(surf):
    arr = pygame.surfarray.array3d(surf)
    mask = np.max(arr, axis=2) > 8
    if not np.any(mask):
        return surf
    xs = np.flatnonzero(np.any(mask, axis=1))
    ys = np.flatnonzero(np.any(mask, axis=0))
    pad = 8
    x0 = max(0, int(xs[0]) - pad)
    x1 = min(surf.get_width(), int(xs[-1]) + pad)
    y0 = max(0, int(ys[0]) - pad)
    y1 = min(surf.get_height(), int(ys[-1]) + pad)
    return surf.subsurface((x0, y0, max(1, x1 - x0), max(1, y1 - y0))).copy()


def _black_to_alpha(surf):
    arr = pygame.surfarray.array3d(surf)
    bright = np.max(arr, axis=2).astype(np.float32)
    alpha = np.clip((bright - 6.0) * 3.2, 0, 255).astype(np.uint8)
    rgba = np.dstack((arr.swapaxes(0, 1), alpha.swapaxes(0, 1)))
    return pygame.image.frombuffer(rgba.tobytes(), surf.get_size(), "RGBA").convert_alpha()


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)
