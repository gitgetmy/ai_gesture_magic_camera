# -*- coding: utf-8 -*-
"""NumPy-driven seasonal particle field with black-background sprites."""
import math
from pathlib import Path

import numpy as np
import pygame

import config


ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets"
ASSET_DIR = ASSET_ROOT / "season_particles"
BACKGROUND_DIR = ASSET_ROOT / "season_backgrounds"


SEASON_DEFS = {
    "spring": {
        "name": "春 · 樱花新绿",
        "cn_name": "春",
        "element": "wood",
        "asset": "spring_petal.png",
        "background": "spring_bg.png",
        "count": 2200,
        "draw_cap": 65,
        "sprite_alpha": 145,
        "sprite_tint": (255, 155, 190),
        "blend": "normal",
        "size": (10, 24),
        "tint": (255, 232, 238),
        "tint_alpha": 12,
        "spawn": "top",
        "base_vx": (-0.20, 0.45),
        "base_vy": (0.25, 0.95),
        "life": (360, 760),
        "drag": (0.986, 0.996),
        "mass": (0.70, 1.25),
    },
    "summer": {
        "name": "夏 · 萤火水光",
        "cn_name": "夏",
        "element": "fire",
        "asset": "summer_drop.png",
        "background": "summer_bg.png",
        "count": 2200,
        "draw_cap": 90,
        "sprite_alpha": 120,
        "sprite_tint": (255, 205, 90),
        "blend": "add",
        "size": (7, 18),
        "tint": (255, 240, 184),
        "tint_alpha": 10,
        "spawn": "all",
        "base_vx": (-0.18, 0.18),
        "base_vy": (-0.45, -0.08),
        "life": (260, 620),
        "drag": (0.982, 0.995),
        "mass": (0.75, 1.2),
    },
    "late_summer": {
        "name": "长夏 · 厚土金尘",
        "cn_name": "长夏",
        "element": "earth",
        "asset": "summer_drop.png",
        "background": "late_summer_bg.png",
        "count": 1800,
        "draw_cap": 70,
        "sprite_alpha": 80,
        "sprite_tint": (235, 170, 95),
        "blend": "add",
        "size": (5, 13),
        "tint": (255, 218, 150),
        "tint_alpha": 13,
        "spawn": "all",
        "base_vx": (-0.10, 0.20),
        "base_vy": (-0.02, 0.34),
        "life": (320, 700),
        "drag": (0.988, 0.997),
        "mass": (1.00, 1.65),
    },
    "autumn": {
        "name": "秋 · 金风红叶",
        "cn_name": "秋",
        "element": "metal",
        "asset": "autumn_leaf.png",
        "background": "autumn_bg.png",
        "count": 2000,
        "draw_cap": 55,
        "sprite_alpha": 155,
        "sprite_tint": (220, 120, 55),
        "blend": "normal",
        "size": (16, 34),
        "tint": (255, 198, 164),
        "tint_alpha": 10,
        "spawn": "side_top",
        "base_vx": (0.45, 1.55),
        "base_vy": (0.05, 0.70),
        "life": (320, 690),
        "drag": (0.984, 0.996),
        "mass": (0.85, 1.45),
    },
    "winter": {
        "name": "冬 · 玄水冰雪",
        "cn_name": "冬",
        "element": "water",
        "asset": "winter_snowflake.png",
        "background": "winter_bg.png",
        "count": 2400,
        "draw_cap": 115,
        "sprite_alpha": 75,
        "sprite_tint": (150, 210, 255),
        "blend": "add",
        "size": (7, 18),
        "tint": (220, 236, 255),
        "tint_alpha": 15,
        "spawn": "top",
        "base_vx": (-0.18, 0.28),
        "base_vy": (0.22, 0.82),
        "life": (420, 920),
        "drag": (0.972, 0.992),
        "mass": (0.55, 2.25),
    },
}


ELEMENT_TO_SEASON = {
    "wood": "spring",
    "fire": "summer",
    "earth": "late_summer",
    "metal": "autumn",
    "water": "winter",
}


class SeasonFX:
    def __init__(self, theme):
        self.theme = theme
        self.season_key = "spring"
        self.defn = SEASON_DEFS["spring"]
        self.active = True
        self._timer = 0.0
        self._rng = np.random.default_rng()
        self._last_hand = None
        self._pinch_latch = False
        self._trail = []
        self._reveal_age = 9999
        self._reveal_duration = 170
        self._reveal_fade_in = 38
        self._sprites = self._load_sprites()
        self._backgrounds = self._load_backgrounds()
        self._init_arrays(SEASON_DEFS["spring"]["count"])
        self.set_theme(theme)

    def _load_sprites(self):
        sprites = {}
        for key, d in SEASON_DEFS.items():
            path = ASSET_DIR / d["asset"]
            if path.exists():
                src = pygame.image.load(str(path)).convert()
                src = self._crop_nonblack(src)
                src = self._black_to_alpha(src)
            else:
                src = self._fallback_sprite(key)
            min_sz, max_sz = d["size"]
            frames = []
            for size in np.linspace(min_sz, max_sz, 5):
                base = pygame.transform.smoothscale(src, (int(size), int(size)))
                base.fill(d.get("sprite_tint", (255, 255, 255)),
                          special_flags=pygame.BLEND_RGB_MULT)
                for angle in range(0, 360, 45):
                    frames.append(pygame.transform.rotate(base, angle).convert_alpha())
            sprites[key] = frames
        return sprites

    def _black_to_alpha(self, surf):
        arr = pygame.surfarray.array3d(surf)
        bright = np.max(arr, axis=2).astype(np.float32)
        alpha = np.clip((bright - 6.0) * 3.2, 0, 255).astype(np.uint8)
        rgba = np.dstack((arr.swapaxes(0, 1), alpha.swapaxes(0, 1)))
        return pygame.image.frombuffer(rgba.tobytes(), surf.get_size(), "RGBA").convert_alpha()

    def _load_backgrounds(self):
        backgrounds = {}
        for key, d in SEASON_DEFS.items():
            path = BACKGROUND_DIR / d["background"]
            if path.exists():
                raw = pygame.image.load(str(path)).convert()
                backgrounds[key] = self._cover_scale(raw, config.WINDOW_WIDTH,
                                                     config.WINDOW_HEIGHT)
            else:
                fallback = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
                fallback.fill(d["tint"])
                backgrounds[key] = fallback.convert()
        return backgrounds

    def _cover_scale(self, surf, width, height):
        sw, sh = surf.get_size()
        scale = max(width / sw, height / sh)
        scaled = pygame.transform.smoothscale(surf, (int(sw * scale), int(sh * scale)))
        x = max(0, (scaled.get_width() - width) // 2)
        y = max(0, (scaled.get_height() - height) // 2)
        return scaled.subsurface((x, y, width, height)).copy().convert()

    def _crop_nonblack(self, surf):
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

    def _fallback_sprite(self, key):
        surf = pygame.Surface((48, 48))
        surf.fill((0, 0, 0))
        color = {
            "spring": (255, 190, 220),
            "summer": (255, 230, 120),
            "late_summer": (255, 200, 110),
            "autumn": (255, 140, 70),
            "winter": (220, 240, 255),
        }[key]
        if key == "autumn":
            pygame.draw.polygon(surf, color, [(24, 4), (34, 20), (44, 24), (30, 30), (24, 44), (18, 30), (4, 24), (14, 20)])
        elif key == "spring":
            pygame.draw.ellipse(surf, color, (8, 16, 32, 14))
        else:
            pygame.draw.circle(surf, color, (24, 24), 10)
        surf.set_colorkey((0, 0, 0))
        return surf

    def _init_arrays(self, count):
        self.n = count
        self.pos = np.zeros((count, 2), dtype=np.float32)
        self.vel = np.zeros((count, 2), dtype=np.float32)
        self.acc = np.zeros((count, 2), dtype=np.float32)
        self.life = np.zeros(count, dtype=np.float32)
        self.max_life = np.ones(count, dtype=np.float32)
        self.mass = np.ones(count, dtype=np.float32)
        self.drag = np.ones(count, dtype=np.float32)
        self.size_idx = np.zeros(count, dtype=np.int16)
        self.angle_idx = np.zeros(count, dtype=np.int16)
        self.rot_speed = np.zeros(count, dtype=np.float32)
        self.phase = np.zeros(count, dtype=np.float32)
        self.hidden = np.zeros(count, dtype=np.float32)
        self._respawn(np.ones(count, dtype=bool), config.WINDOW_WIDTH,
                      config.WINDOW_HEIGHT, scatter=True)

    def set_theme(self, theme):
        self.theme = theme
        new_key = ELEMENT_TO_SEASON.get(theme.get("element", "wood"), "spring")
        if new_key != self.season_key:
            self.season_key = new_key
            self.defn = SEASON_DEFS[new_key]
            self._trail.clear()
            self._last_hand = None
            self._pinch_latch = False
            if self.n != self.defn["count"]:
                self._init_arrays(self.defn["count"])
            else:
                self._respawn(np.ones(self.n, dtype=bool), config.WINDOW_WIDTH,
                              config.WINDOW_HEIGHT, scatter=True)
        else:
            self.defn = SEASON_DEFS[new_key]

    @property
    def cn_name(self):
        return self.defn["cn_name"]

    @property
    def name(self):
        return self.defn["name"]

    def draw_background(self, screen, alpha=255):
        bg = self._backgrounds.get(self.season_key)
        if bg is None:
            screen.fill(self.theme.get("bg_tint", (8, 12, 20)))
            return
        if alpha >= 255:
            screen.blit(bg, (0, 0))
            return
        bg = bg.copy()
        bg.set_alpha(alpha)
        screen.blit(bg, (0, 0))

    def _cinematic_background_copy(self):
        bg = self._backgrounds.get(self.season_key)
        if bg is None:
            return None
        temp = bg.copy()
        temp.fill((218, 222, 230), special_flags=pygame.BLEND_RGB_MULT)
        shade = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 10, 16, 34))
        temp.blit(shade, (0, 0))
        return temp

    def trigger_background_reveal(self):
        self._reveal_age = 0

    @property
    def reveal_active(self):
        return self._reveal_age < self._reveal_duration

    def draw_background_reveal(self, screen):
        if self._reveal_age >= self._reveal_duration:
            return
        bg = self._backgrounds.get(self.season_key)
        if bg is None:
            return
        if self._reveal_age < self._reveal_fade_in:
            p = self._reveal_age / max(1, self._reveal_fade_in)
            strength = p * p * (3.0 - 2.0 * p)
        else:
            p = (self._reveal_age - self._reveal_fade_in) / max(1, self._reveal_duration - self._reveal_fade_in)
            strength = (1.0 - p) ** 1.35
        temp = self._cinematic_background_copy()
        if temp is None:
            return
        temp.set_alpha(int(245 * strength))
        screen.blit(temp, (0, 0))

        veil = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        veil.fill((5, 9, 15, int(46 * strength)))
        screen.blit(veil, (0, 0))

    def update(self, width, height, interaction=None):
        self._timer += 1.0
        if self._reveal_age < self._reveal_duration:
            self._reveal_age += 1
        if not self.active:
            return

        hand = None
        if interaction and interaction.get("point") is not None:
            hand = np.array(interaction["point"], dtype=np.float32)

        self.acc.fill(0.0)
        if self.season_key == "spring":
            self._update_spring(hand)
        elif self.season_key == "summer":
            self._update_summer(hand, interaction or {})
        elif self.season_key == "late_summer":
            self._update_late_summer(hand)
        elif self.season_key == "autumn":
            self._update_autumn(hand)
        else:
            self._update_winter(hand, interaction or {})

        self.vel += self.acc
        self.vel *= self.drag[:, None]
        self.pos += self.vel
        self.life -= 1.0
        self.hidden *= 0.90

        self.angle_idx = (self.angle_idx + self.rot_speed.astype(np.int16)) % 8
        dead = (
            (self.life <= 0)
            | (self.pos[:, 0] < -96)
            | (self.pos[:, 0] > width + 96)
            | (self.pos[:, 1] < -96)
            | (self.pos[:, 1] > height + 96)
        )
        if np.any(dead):
            self._respawn(dead, width, height)

        self._last_hand = None if hand is None else hand.copy()

    def _respawn(self, mask, width, height, scatter=False):
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return
        d = self.defn
        m = idx.size

        if scatter:
            self._scatter_positions(idx, width, height)
        elif d["spawn"] == "top":
            self.pos[idx, 0] = self._rng.uniform(-40, width + 40, m)
            self.pos[idx, 1] = self._rng.uniform(-70, 10, m)
        elif d["spawn"] == "side_top":
            self.pos[idx, 0] = self._rng.uniform(-90, width * 0.35, m)
            self.pos[idx, 1] = self._rng.uniform(-60, height * 0.50, m)
        else:
            self.pos[idx, 0] = self._rng.uniform(0, width, m)
            self.pos[idx, 1] = self._rng.uniform(0, height, m)

        self.vel[idx, 0] = self._rng.uniform(*d["base_vx"], m)
        self.vel[idx, 1] = self._rng.uniform(*d["base_vy"], m)
        self.max_life[idx] = self._rng.uniform(*d["life"], m)
        if scatter:
            self.life[idx] = self._rng.uniform(self.max_life[idx] * 0.45,
                                               self.max_life[idx] * 0.98)
        else:
            self.life[idx] = self.max_life[idx]
        self.mass[idx] = self._rng.uniform(*d["mass"], m)
        self.drag[idx] = self._rng.uniform(*d["drag"], m)
        self.size_idx[idx] = self._rng.integers(0, 5, m, dtype=np.int16)
        self.angle_idx[idx] = self._rng.integers(0, 8, m, dtype=np.int16)
        self.rot_speed[idx] = self._rng.choice(np.array([-1, 0, 1], dtype=np.float32), m)
        self.phase[idx] = self._rng.uniform(0.0, math.tau, m)
        self.hidden[idx] = 0.0

    def _scatter_positions(self, idx, width, height):
        m = idx.size
        cols = max(1, int(math.sqrt(m * width / max(1, height))))
        rows = max(1, int(math.ceil(m / cols)))
        cell_w = width / cols
        cell_h = height / rows
        order = self._rng.permutation(rows * cols)[:m]
        gx = order % cols
        gy = order // cols
        self.pos[idx, 0] = (gx + self._rng.uniform(0.15, 0.85, m)) * cell_w
        self.pos[idx, 1] = (gy + self._rng.uniform(0.10, 0.90, m)) * cell_h

    def _hand_vectors(self, hand):
        delta = self.pos - hand
        dist2 = np.sum(delta * delta, axis=1) + 36.0
        inv_dist = 1.0 / np.sqrt(dist2)
        return delta, dist2, inv_dist

    def _update_spring(self, hand):
        wind = np.sin(self._timer * 0.025 + self.phase) * 0.045
        self.acc[:, 0] += wind
        self.acc[:, 1] += 0.010 / self.mass
        if hand is not None:
            delta, dist2, inv_dist = self._hand_vectors(hand)
            field = np.clip((170.0 ** 2 - dist2) / (170.0 ** 2), 0.0, 1.0)
            self.acc += delta * inv_dist[:, None] * (field * 0.42 / self.mass)[:, None]

    def _update_summer(self, hand, interaction):
        self.acc[:, 1] -= 0.010
        wave = np.sin(self._timer * 0.075 + self.phase) * 0.035
        self.acc[:, 0] += wave
        if hand is None:
            self._pinch_latch = False
            return

        delta, dist2, inv_dist = self._hand_vectors(hand)
        direction_to_hand = -delta * inv_dist[:, None]
        if interaction.get("open"):
            gravity = np.clip(10500.0 / dist2, 0.0, 0.72)
            self.acc += direction_to_hand * gravity[:, None]

        pinching = bool(interaction.get("pinch"))
        if pinching and not self._pinch_latch:
            ring = self._rng.uniform(5.0, 13.5, self.n)
            self.vel += delta * inv_dist[:, None] * ring[:, None]
        self._pinch_latch = pinching

    def _update_late_summer(self, hand):
        self.acc[:, 1] += 0.006 / self.mass
        self.acc[:, 0] += np.sin(self._timer * 0.018 + self.phase) * 0.025
        if hand is not None:
            delta, dist2, inv_dist = self._hand_vectors(hand)
            field = np.clip((140.0 ** 2 - dist2) / (140.0 ** 2), 0.0, 1.0)
            self.acc += delta * inv_dist[:, None] * (field * 0.24 / self.mass)[:, None]

    def _update_autumn(self, hand):
        self.acc[:, 1] += 0.012 / self.mass
        self.acc[:, 0] += 0.018 + np.sin(self._timer * 0.018 + self.phase) * 0.030
        if hand is None:
            return

        delta, dist2, inv_dist = self._hand_vectors(hand)
        tangent = np.column_stack((-delta[:, 1], delta[:, 0])) * inv_dist[:, None]
        vortex = np.clip((230.0 ** 2 - dist2) / (230.0 ** 2), 0.0, 1.0)
        to_center = -delta * inv_dist[:, None]
        self.acc += tangent * (vortex * 0.88)[:, None]
        self.acc += to_center * (vortex * 0.18)[:, None]

        if self._last_hand is not None:
            hand_vel = hand - self._last_hand
            speed = np.linalg.norm(hand_vel)
            if speed > 1.0:
                self.acc += tangent * (vortex * min(1.15, speed * 0.035))[:, None]

    def _update_winter(self, hand, interaction):
        self.acc[:, 1] += 0.020 / self.mass
        self.acc[:, 0] += np.sin(self._timer * 0.015 + self.phase) * 0.012
        if hand is None:
            return

        delta, dist2, inv_dist = self._hand_vectors(hand)
        field = np.clip((145.0 ** 2 - dist2) / (145.0 ** 2), 0.0, 1.0)
        self.acc += delta * inv_dist[:, None] * (field * 0.55 / self.mass)[:, None]

        if self._last_hand is not None:
            hand_vel = hand - self._last_hand
            speed = np.linalg.norm(hand_vel)
            if speed > 3.0:
                self._trail.append((hand.copy(), 24.0))
                trail_field = np.clip((70.0 ** 2 - dist2) / (70.0 ** 2), 0.0, 1.0)
                self.hidden = np.maximum(self.hidden, trail_field)

    def draw(self, screen, fx):
        if not self.active:
            return
        self._draw_color_wash(screen)
        if self.season_key == "winter":
            self._draw_snow_trails(screen)

        frames = self._sprites[self.season_key]
        age = np.clip(self.life / self.max_life, 0.0, 1.0)
        fade_in = np.clip((self.max_life - self.life) / 42.0, 0.0, 1.0)
        alpha = age * fade_in * (1.0 - self.hidden)
        visible = np.flatnonzero(alpha > 0.10)
        draw_cap = self.defn.get("draw_cap", 500)
        if visible.size > draw_cap:
            visible = visible[:: max(1, visible.size // draw_cap)]

        for i in visible:
            frame_index = int(self.size_idx[i] * 8 + self.angle_idx[i])
            sprite = frames[frame_index]
            sprite.set_alpha(int(self.defn.get("sprite_alpha", 90) * alpha[i]))
            rect = sprite.get_rect(center=(int(self.pos[i, 0]), int(self.pos[i, 1])))
            if self.defn.get("blend") == "normal":
                screen.blit(sprite, rect)
            else:
                fx.blit(sprite, rect, special_flags=pygame.BLEND_ADD)

    def _draw_color_wash(self, screen):
        alpha = self.defn["tint_alpha"]
        if alpha <= 0:
            return
        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*self.defn["tint"], alpha))
        screen.blit(overlay, (0, 0))

    def _draw_snow_trails(self, screen):
        if not self._trail:
            return
        kept = []
        for point, life in self._trail:
            if life <= 0:
                continue
            radius = int(32 + (24 - life) * 2.0)
            cut = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(cut, (10, 16, 28, int(34 * life / 24)), (radius, radius), radius)
            screen.blit(cut, (int(point[0] - radius), int(point[1] - radius)))
            kept.append((point, life - 1.0))
        self._trail = kept[-18:]

    def draw_god_rays(self, fx):
        return

    def clear(self):
        self._respawn(np.ones(self.n, dtype=bool), config.WINDOW_WIDTH,
                      config.WINDOW_HEIGHT, scatter=True)
        self._trail.clear()
