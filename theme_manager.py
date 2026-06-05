# -*- coding: utf-8 -*-
"""
theme_manager.py —— 五行主题管理（木 火 土 金 水）

每个五行属性是一套配色，结构与原有特效兼容（含 core / palette / bg_tint），
另外补充 ink（水墨深色，用于水墨拖尾）、cn_name、element 等字段。
按 1-5 直接切换属性，按 C 循环切换。
切换属性会改变所有特效的颜色、背景色调与水墨墨色。
"""

# 五行配色。core=白热核心；palette=主色相池(丰富多彩不单调)；
# accent=符线强调色；accent2=互补撞色(增强冲击)；spectrum=大招用多色相光谱；
# bg_tint=背景色调；ink=水墨墨色
ELEMENTS = {
    "metal": {
        "element": "metal", "cn_name": "金", "name": "金 · 锐金剑气",
        "core": (255, 252, 235),
        "palette": [(255, 215, 90), (255, 240, 200), (255, 180, 60),
                    (255, 250, 230), (210, 170, 255), (120, 230, 255)],
        "accent": (255, 225, 120), "accent2": (160, 120, 255),
        "spectrum": [(255, 215, 90), (255, 255, 240), (255, 150, 60),
                     (180, 140, 255), (120, 230, 255), (255, 120, 180)],
        "bg_tint": (20, 17, 8), "ink": (60, 50, 20),
    },
    "wood": {
        "element": "wood", "cn_name": "木", "name": "木 · 生发青木",
        "core": (235, 255, 230),
        "palette": [(80, 230, 120), (160, 255, 150), (40, 200, 110),
                    (200, 255, 180), (255, 230, 120), (90, 220, 255)],
        "accent": (140, 255, 160), "accent2": (255, 200, 90),
        "spectrum": [(80, 230, 120), (230, 255, 200), (255, 220, 100),
                     (90, 220, 255), (180, 120, 255), (60, 255, 160)],
        "bg_tint": (8, 19, 11), "ink": (16, 46, 28),
    },
    "water": {
        "element": "water", "cn_name": "水", "name": "水 · 玄水墨韵",
        "core": (235, 248, 255),
        "palette": [(80, 160, 255), (120, 215, 255), (60, 110, 230),
                    (190, 225, 255), (150, 120, 255), (90, 255, 230)],
        "accent": (140, 210, 255), "accent2": (180, 130, 255),
        "spectrum": [(80, 160, 255), (235, 248, 255), (90, 255, 230),
                     (150, 120, 255), (255, 150, 220), (120, 215, 255)],
        "bg_tint": (8, 14, 26), "ink": (10, 16, 34),
    },
    "fire": {
        "element": "fire", "cn_name": "火", "name": "火 · 朱火凤羽",
        "core": (255, 245, 220),
        "palette": [(255, 80, 40), (255, 150, 45), (255, 210, 90),
                    (255, 60, 30), (255, 120, 200), (255, 235, 150)],
        "accent": (255, 110, 60), "accent2": (255, 90, 190),
        "spectrum": [(255, 80, 40), (255, 245, 200), (255, 180, 60),
                     (255, 90, 190), (180, 120, 255), (255, 150, 45)],
        "bg_tint": (24, 10, 8), "ink": (60, 18, 12),
    },
    "earth": {
        "element": "earth", "cn_name": "土", "name": "土 · 厚土镇阵",
        "core": (255, 248, 215),
        "palette": [(228, 188, 90), (210, 155, 75), (255, 210, 110),
                    (242, 215, 130), (255, 150, 90), (150, 220, 160)],
        "accent": (240, 205, 115), "accent2": (255, 140, 90),
        "spectrum": [(228, 188, 90), (255, 248, 210), (255, 150, 90),
                     (150, 220, 160), (200, 150, 255), (255, 210, 110)],
        "bg_tint": (20, 16, 9), "ink": (50, 40, 18),
    },
}

# 五行顺序（木火土金水），按 C 循环、按 1-5 直选
ELEMENT_ORDER = ["wood", "fire", "earth", "metal", "water"]
# 键位 1-5 -> 五行
KEY_TO_ELEMENT = {1: "wood", 2: "fire", 3: "earth", 4: "metal", 5: "water"}
DEFAULT_ELEMENT = "wood"   # 默认木系，对应春季生发


class ThemeManager:
    def __init__(self, element=DEFAULT_ELEMENT):
        self.element = element
        self.theme = ELEMENTS[element]

    def set_element(self, element):
        if element in ELEMENTS:
            self.element = element
            self.theme = ELEMENTS[element]
        return self.theme

    def set_by_key(self, num):
        """num 为 1-5，对应木火土金水"""
        el = KEY_TO_ELEMENT.get(num)
        if el:
            self.set_element(el)
        return self.theme

    def cycle(self):
        i = ELEMENT_ORDER.index(self.element)
        self.set_element(ELEMENT_ORDER[(i + 1) % len(ELEMENT_ORDER)])
        return self.theme

    @property
    def cn_name(self):
        return self.theme["cn_name"]
