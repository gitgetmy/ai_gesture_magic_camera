# -*- coding: utf-8 -*-
"""
effects/skill_transition.py —— 技能切换过渡动画（电影级 · 仪式感过场）

电影级过场结构：
  - 几何扩散：从手部位置扩散的六边形/菱形几何图案
  - 多层彩环：3-4圈不同速度/颜色的同心光环
  - 粒子迸发：触发瞬间的粒子爆发
  - 放射光束：16-24条光束从中心射出
  - 招式名横幅：半透明底衬 + 上下描边 + 淡入上浮 + 淡出
  - 符文散落：从横幅位置飘落的小型光符
"""
import math
import random

import pygame

from utils.draw_utils import draw_ring_multi, draw_beams, draw_glow
from utils.math_utils import scale_color


class SkillTransition:
    def __init__(self, theme, big_font):
        self.theme = theme
        self.big_font = big_font
        self.t = 0.0
        self.duration = 40
        self.active = False
        self.name = ""
        self.center = (0, 0)
        self._last_name = ""
        self._cooldown = 0
        self._runes = []   # 飘散光符 (x, y, vx, vy, life, char)

    def set_theme(self, theme):
        self.theme = theme

    def maybe_trigger(self, name, center):
        if self._cooldown > 0:
            return
        base = name.split(" ")[0]
        last_base = self._last_name.split(" ")[0]
        if base and base != last_base and "Idle" not in name:
            self.name = name
            self.center = center
            self.t = 0.0
            self.active = True
            self._cooldown = 18
            # 生成飘散符文
            self._runes = []
            rune_chars = ["乾", "坤", "震", "巽", "离", "坎", "艮", "兑",
                          "金", "木", "水", "火", "土", "天", "地", "玄"]
            for _ in range(12):
                a = random.uniform(0, math.tau)
                spd = random.uniform(1.5, 5)
                self._runes.append([
                    center[0], center[1],
                    math.cos(a) * spd,
                    math.sin(a) * spd - random.uniform(1, 3),
                    random.randint(25, 50),
                    random.choice(rune_chars),
                ])
        self._last_name = name

    def update(self):
        if self._cooldown > 0:
            self._cooldown -= 1
        if self.active:
            self.t += 1
            if self.t >= self.duration:
                self.active = False
        # 更新符文
        for r in self._runes:
            r[0] += r[2]
            r[1] += r[3]
            r[2] *= 0.96
            r[3] += 0.05   # 微重力
            r[4] -= 1
        self._runes = [r for r in self._runes if r[4] > 0]

    def draw_fx(self, fx):
        """加色层：几何扩散 + 彩环 + 光束 + 符文辉光"""
        return
        p = self.t / self.duration
        ease = 1.0 - (1.0 - p) ** 2.5
        alpha = 1.0 - p
        cx, cy = self.center
        spectrum = self.theme.get("spectrum", [self.theme["core"]])
        accent = self.theme.get("accent", self.theme["core"])

        # 多层彩环
        for i in range(4):
            delay = i * 0.08
            if p < delay:
                continue
            ring_p = (p - delay) / (1 - delay)
            ring_ease = 1.0 - (1.0 - ring_p) ** 2
            radius = 20 + ring_ease * 200 * (1 - i * 0.15)
            ring_alpha = alpha * (1 - ring_p)
            col = spectrum[i % len(spectrum)]
            draw_glow(fx, (cx, cy), radius, scale_color(col, ring_alpha),
                      layers=6)

        # 放射光束
        beam_count = 20
        draw_beams(fx, self.center, 40 + ease * 220, accent,
                   count=beam_count, rotation=self.t * 0.12,
                   width=max(1, int(3 * alpha)), alpha=alpha * 0.7)

        # 六边形几何图案（旋转扩散）
        hex_pts = []
        for i in range(6):
            a = self.t * 0.04 + i * math.tau / 6
            r = 30 + ease * 160
            hex_pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        if len(hex_pts) >= 3:
            pygame.draw.polygon(fx, scale_color(accent, alpha * 0.35),
                                [(int(x), int(y)) for x, y in hex_pts], 2)
        # 内六边形（反向旋转）
        inner_hex = []
        for i in range(6):
            a = -self.t * 0.06 + i * math.tau / 6
            r = 15 + ease * 90
            inner_hex.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        if len(inner_hex) >= 3:
            pygame.draw.polygon(fx, scale_color(spectrum[1], alpha * 0.45),
                                [(int(x), int(y)) for x, y in inner_hex], 1)

        # 中心辉光
        draw_glow(fx, self.center, 30 * alpha + 4, accent, layers=5)

        # 符文辉光（加色层）
        for rx, ry, _, _, life, _ in self._runes:
            r_alpha = life / 50.0
            if r_alpha > 0:
                col = spectrum[random.randint(0, len(spectrum) - 1)]
                draw_glow(fx, (rx, ry), 5 * r_alpha + 1, col, layers=3)

    def draw_overlay(self, screen):
        """正常透明度层：招式名横幅 + 符文文字"""
        if not self.active or self.big_font is None:
            return
        p = self.t / self.duration
        if p < 0.2:
            a = p / 0.2
        else:
            a = max(0.0, 1.0 - (p - 0.2) / 0.8)
        if a <= 0.02:
            return
        sw = screen.get_width()
        rise = int((1 - a) * 20)
        cy = 120 + rise
        name_cn = self.name.split(" ")[0]
        text = self.big_font.render(name_cn, True, self.theme["core"])
        text.set_alpha(int(255 * a))

        # 半透明底衬条（更宽）
        pad = 32
        bar_w, bar_h = text.get_width() + pad * 2, text.get_height() + 18
        bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        bar.fill((*self.theme["bg_tint"], int(170 * a)))
        bar_rect = bar.get_rect(center=(sw // 2, cy))
        screen.blit(bar, bar_rect)

        # 上下装饰线（主题色）
        line_c = (*self.theme.get("accent", self.theme["core"]), int(220 * a))
        pygame.draw.line(screen, line_c,
                         (bar_rect.left, bar_rect.top),
                         (bar_rect.right, bar_rect.top), 2)
        pygame.draw.line(screen, line_c,
                         (bar_rect.left, bar_rect.bottom),
                         (bar_rect.right, bar_rect.bottom), 2)
        # 左右短装饰线
        corner_len = 16
        for y_pos in (bar_rect.top, bar_rect.bottom):
            pygame.draw.line(screen, line_c,
                             (bar_rect.left, y_pos),
                             (bar_rect.left + corner_len, y_pos), 3)
            pygame.draw.line(screen, line_c,
                             (bar_rect.right - corner_len, y_pos),
                             (bar_rect.right, y_pos), 3)

        screen.blit(text, text.get_rect(center=(sw // 2, cy)))

        # 符文文字（正常透明度，小字）
        small_font = pygame.font.SysFont("microsoftyahei,simhei,arial", 20)
        for rx, ry, _, _, life, char in self._runes:
            r_a = life / 50.0 * a
            if r_a <= 0.03:
                continue
            r_surf = small_font.render(char, True, self.theme["core"])
            r_surf.set_alpha(int(255 * r_a))
            screen.blit(r_surf, (int(rx), int(ry)))
