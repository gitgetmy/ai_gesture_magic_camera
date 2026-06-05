# -*- coding: utf-8 -*-
"""
utils/draw_utils.py —— 绘制辅助函数

核心思路：所有发光特效先画到一张「黑底特效层」上（颜色越亮贡献越大），
最后用加色混合（BLEND_RGB_ADD）叠加到摄像头画面上，得到霓虹发光感。
黑色区域加 0，不影响背景；亮色区域点亮画面。
"""
import math
import random
import pygame

from utils.math_utils import scale_color

# 光晕精灵缓存：避免每帧重复生成。key = (半径分桶, 颜色)
_glow_cache = {}


def make_glow_sprite(radius, color, layers=6):
    """
    生成一张柔和的圆形光晕精灵（黑底，用于加色混合）。
    中心带白热核心、向外渐暗，层数更多 -> 更强的 bloom 辉光。结果缓存复用。
    """
    radius = max(1, int(radius))
    key = (radius, color, layers)
    cached = _glow_cache.get(key)
    if cached is not None:
        return cached

    size = radius * 2
    surf = pygame.Surface((size, size))   # 黑底即可
    surf.fill((0, 0, 0))
    center = (radius, radius)
    # 多层同心圆，由暗到亮叠出渐变（电影级 bloom）
    for i in range(layers, 0, -1):
        t = i / layers                       # 1.0 = 最外层
        r = max(1, int(radius * t))
        factor = (1.0 - t) ** 2 + 0.18
        c = scale_color(color, factor)
        # 最内两层往白热过渡，制造高光核心
        if i <= 2:
            c = (min(255, c[0] + 90), min(255, c[1] + 90), min(255, c[2] + 90))
        pygame.draw.circle(surf, c, center, r)
    _glow_cache[key] = surf
    return surf


def draw_glow(fx_surface, pos, radius, color, layers=6):
    """把一个光点以加色方式画到特效层上（默认 6 层，更亮）"""
    sprite = make_glow_sprite(radius, color, layers)
    rect = sprite.get_rect(center=(int(pos[0]), int(pos[1])))
    fx_surface.blit(sprite, rect, special_flags=pygame.BLEND_RGB_ADD)


def draw_glow_multi(fx_surface, pos, radius, colors):
    """多色辉光：外圈到内圈用不同色相叠加，呈现棱镜/极光般的多彩光晕。"""
    n = len(colors)
    for i, c in enumerate(colors):
        r = radius * (1.0 - i / (n + 0.5))
        draw_glow(fx_surface, pos, max(1, r), c, layers=4)


def draw_ring(fx_surface, center, radius, color, thickness=2, alpha=1.0):
    """画一个发光圆环（加色）。alpha 当作亮度系数使用。"""
    if radius < 1:
        return
    c = scale_color(color, alpha)
    pygame.draw.circle(fx_surface, c, (int(center[0]), int(center[1])),
                       int(radius), max(1, int(thickness)))


def draw_ring_multi(fx_surface, center, radius, colors, thickness=2, alpha=1.0):
    """多色同心圆环：每种颜色一圈，形成彩色光环组。"""
    for i, c in enumerate(colors):
        draw_ring(fx_surface, center, radius + i * (thickness + 2), c,
                  thickness=thickness, alpha=alpha * (1.0 - i * 0.12))


def draw_beams(fx_surface, center, radius, color, count=12, rotation=0.0,
               width=2, alpha=1.0):
    """从中心向外发散的光束（神光/god-ray），用于大招与阵法释放。"""
    cx, cy = center
    c = scale_color(color, alpha)
    for i in range(count):
        a = rotation + i * (math.tau / count)
        x = cx + math.cos(a) * radius
        y = cy + math.sin(a) * radius
        pygame.draw.line(fx_surface, c, (cx, cy), (x, y), max(1, int(width)))


def draw_lightning(fx_surface, start, end, color, segments=12,
                   jitter=20, width=3):
    """在 start -> end 之间画一条抖动折线（主闪电），外发光更宽。"""
    sx, sy = start
    ex, ey = end
    points = [(sx, sy)]
    dx = ex - sx
    dy = ey - sy
    length = math.hypot(dx, dy)
    if length < 1:
        return points
    nx, ny = -dy / length, dx / length
    for i in range(1, segments):
        t = i / segments
        bx = sx + dx * t
        by = sy + dy * t
        offset = random.uniform(-jitter, jitter) * (1.0 - abs(t - 0.5))
        points.append((bx + nx * offset, by + ny * offset))
    points.append((ex, ey))
    # 三层：宽外晕 + 中层 + 亮白主线
    pygame.draw.lines(fx_surface, scale_color(color, 0.25), False, points, width + 6)
    pygame.draw.lines(fx_surface, scale_color(color, 0.6), False, points, width + 2)
    white = (min(255, color[0] + 80), min(255, color[1] + 80), min(255, color[2] + 80))
    pygame.draw.lines(fx_surface, white, False, points, width)
    return points


# ============================================================
#  UI 辅助绘制函数（面板、渐变、发光文字等）
# ============================================================

_rounded_rect_cache = {}


def _make_rounded_rect_surface(w, h, radius, bg_color, border_width, border_color):
    """预渲染一张圆角矩形 Surface（带缓存），供面板绘制复用。"""
    key = (w, h, radius, bg_color, border_width, border_color)
    cached = _rounded_rect_cache.get(key)
    if cached is not None:
        return cached.copy()

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # 绘制圆角矩形（填充）
    rect = pygame.Rect(0, 0, w, h)
    pygame.draw.rect(surf, bg_color, rect, border_radius=radius)
    # 边框
    if border_width > 0 and border_color is not None:
        pygame.draw.rect(surf, border_color, rect, border_width, border_radius=radius)
    _rounded_rect_cache[key] = surf.copy()
    return surf


def draw_panel(screen, rect, bg_color=(15, 15, 30, 200),
               border_color=None, radius=12, border_width=1):
    """绘制一个半透明圆角面板。bg_color 支持 RGBA。"""
    x, y, w, h = rect
    if len(bg_color) == 3:
        bg = (*bg_color, 200)
    else:
        bg = bg_color
    surf = _make_rounded_rect_surface(w, h, radius, bg, border_width, border_color)
    screen.blit(surf, (x, y))


def draw_gradient_bar(screen, rect, color_start, color_end, bg_color=(30, 30, 45),
                      radius=4, vertical=False):
    """绘制渐变色进度条，从 color_start 到 color_end。"""
    import numpy as np
    x, y, w, h = rect
    # 背景
    pygame.draw.rect(screen, bg_color, rect, border_radius=radius)
    # 渐变填充
    if w <= 0 or h <= 0:
        return
    if vertical:
        grad = np.linspace(0, 1, h).reshape(-1, 1)
        r = (color_start[0] + (color_end[0] - color_start[0]) * grad).astype(np.uint8)
        g = (color_start[1] + (color_end[1] - color_start[1]) * grad).astype(np.uint8)
        b = (color_start[2] + (color_end[2] - color_start[2]) * grad).astype(np.uint8)
        rgb = np.concatenate([r, g, b], axis=1)
        small = pygame.image.frombuffer(rgb.tobytes(), (1, h), "RGB")
        fill_surf = pygame.transform.scale(small, (w, h))
    else:
        grad = np.linspace(0, 1, w).reshape(1, -1)
        r = (color_start[0] + (color_end[0] - color_start[0]) * grad).astype(np.uint8)
        g = (color_start[1] + (color_end[1] - color_start[1]) * grad).astype(np.uint8)
        b = (color_start[2] + (color_end[2] - color_start[2]) * grad).astype(np.uint8)
        rgb = np.concatenate([r, g, b], axis=1)
        small = pygame.image.frombuffer(rgb.tobytes(), (w, 1), "RGB")
        fill_surf = pygame.transform.scale(small, (w, h))
    # 裁剪为圆角：用 mask
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    fill_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    screen.blit(fill_surf, (x, y))


def draw_glow_text(screen, font, text, color, pos, glow_color=None, glow_radius=2):
    """绘制带辉光的文字：先画多层光晕，再画主体文字。"""
    if glow_color is None:
        glow_color = tuple(max(0, c - 100) for c in color)
    x, y = pos
    # 多层外晕
    for r in range(glow_radius, 0, -1):
        alpha = 80 - r * 20
        if alpha <= 0:
            continue
        c = tuple(min(255, gc + 20) for gc in glow_color)
        s = font.render(text, True, c)
        s.set_alpha(alpha)
        screen.blit(s, (x - r, y - r))
        screen.blit(s, (x + r, y - r))
        screen.blit(s, (x - r, y + r))
        screen.blit(s, (x + r, y + r))
    # 主体
    screen.blit(font.render(text, True, color), (x, y))


def draw_keycap(screen, font, text, pos, key_color=(60, 65, 85),
                text_color=(220, 225, 240)):
    """绘制一个仿机械键盘键帽的小标签。"""
    x, y = pos
    text_surf = font.render(text, True, text_color)
    tw, th = text_surf.get_size()
    pad_x, pad_y = 8, 4
    rect = pygame.Rect(x, y, tw + pad_x * 2, th + pad_y * 2)
    # 键帽阴影
    shadow = pygame.Rect(x + 1, y + 2, rect.w, rect.h)
    pygame.draw.rect(screen, (10, 12, 20), shadow, border_radius=4)
    # 键帽主体
    pygame.draw.rect(screen, key_color, rect, border_radius=4)
    # 顶部高光
    highlight = pygame.Rect(x + 2, y + 1, rect.w - 4, rect.h // 2)
    pygame.draw.rect(screen, (min(255, key_color[0] + 40),
                               min(255, key_color[1] + 40),
                               min(255, key_color[2] + 40)),
                     highlight, border_radius=3)
    screen.blit(text_surf, (x + pad_x, y + pad_y))


def draw_separator(screen, x, y, w, color=(80, 85, 105), alpha=120):
    """绘制一条水平分隔线。"""
    s = pygame.Surface((w, 2), pygame.SRCALPHA)
    s.fill((*color, alpha))
    screen.blit(s, (x, y))


def cv_frame_to_surface(frame_rgb):
    """
    把已经是 RGB、且尺寸与窗口一致的 numpy 帧转成 pygame Surface。
    frame_rgb: (H, W, 3) uint8
    """
    h, w = frame_rgb.shape[:2]
    return pygame.image.frombuffer(frame_rgb.tobytes(), (w, h), "RGB")
