# -*- coding: utf-8 -*-
"""Cinematic post-processing overlays."""
import numpy as np
import pygame

import config

W, H = config.WINDOW_WIDTH, config.WINDOW_HEIGHT


def _make_vignette():
    cx, cy = W / 2, H / 2
    max_d = (cx ** 2 + cy ** 2) ** 0.5
    ys, xs = np.mgrid[0:H, 0:W]
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / max_d
    alpha = np.clip((d - 0.48) / 0.52, 0, 1) ** 1.65 * 210
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 3] = alpha.astype(np.uint8)
    return pygame.image.frombuffer(rgba.tobytes(), (W, H), "RGBA").convert_alpha()


def _make_scanline():
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(0, H, 3):
        pygame.draw.line(surf, (0, 0, 0, 30), (0, y), (W, y), 1)
    return surf


def _make_noise_frames(n=4):
    frames = []
    sw, sh = W // 6, H // 6
    for _ in range(n):
        arr = (np.random.rand(sh, sw) * 30).astype(np.uint8)
        rgb = np.stack([arr, arr, arr], axis=-1)
        small = pygame.image.frombuffer(rgb.tobytes(), (sw, sh), "RGB")
        frame = pygame.transform.smoothscale(small, (W, H))
        frame.set_alpha(32)
        frames.append(frame)
    return frames


class PostProcessing:
    def __init__(self):
        self.enabled = True
        self.vignette_on = True
        self.scanline_on = False
        self.noise_on = False
        self.cinema_on = False
        self.theme = None
        self._vignette = _make_vignette()
        self._scanline = _make_scanline()
        self._noise = _make_noise_frames()
        self._noise_i = 0

    def set_theme(self, theme):
        self.theme = theme

    def toggle_all(self):
        self.enabled = not self.enabled

    def toggle_vignette(self):
        self.vignette_on = not self.vignette_on

    def toggle_scanline(self):
        self.scanline_on = not self.scanline_on

    def toggle_noise(self):
        self.noise_on = not self.noise_on

    def toggle_cinema(self):
        self.cinema_on = not self.cinema_on

    def apply(self, screen):
        if not self.enabled:
            return

        if self.cinema_on:
            self._apply_tone(screen)
            self._draw_letterbox(screen)

        if self.noise_on:
            self._noise_i = (self._noise_i + 1) % len(self._noise)
            screen.blit(self._noise[self._noise_i], (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        if self.scanline_on:
            screen.blit(self._scanline, (0, 0))

        if self.vignette_on:
            screen.blit(self._vignette, (0, 0))

    def _apply_tone(self, screen):
        bg = (12, 13, 20)
        core = (235, 240, 255)
        if self.theme:
            bg = self.theme.get("bg_tint", bg)
            core = self.theme.get("core", core)

        shadows = pygame.Surface((W, H), pygame.SRCALPHA)
        shadows.fill((max(0, bg[0] // 2), max(0, bg[1] // 2), max(0, bg[2] // 2), 28))
        screen.blit(shadows, (0, 0))

        highlights = pygame.Surface((W, H), pygame.SRCALPHA)
        highlights.fill((core[0], core[1], core[2], 9))
        screen.blit(highlights, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_letterbox(self, screen):
        bar_h = 36
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, W, bar_h))
        pygame.draw.rect(screen, (0, 0, 0), (0, H - bar_h, W, bar_h))
        pygame.draw.line(screen, (255, 255, 255, 22), (0, bar_h), (W, bar_h), 1)
        pygame.draw.line(screen, (255, 255, 255, 18), (0, H - bar_h), (W, H - bar_h), 1)

    def status_text(self):
        if not self.enabled:
            return "OFF"
        flags = []
        if self.cinema_on:
            flags.append("C")
        if self.vignette_on:
            flags.append("V")
        if self.scanline_on:
            flags.append("S")
        if self.noise_on:
            flags.append("N")
        return "ON[" + "".join(flags) + "]"
