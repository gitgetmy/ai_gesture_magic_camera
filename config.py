# -*- coding: utf-8 -*-
"""
config.py —— 全局配置参数集中管理

所有可调参数都放在这里，方便统一修改，避免在各模块里硬编码魔法数字。
"""

# ============ 窗口 / 摄像头 ============
WINDOW_WIDTH = 1280          # 显示窗口宽
WINDOW_HEIGHT = 720          # 显示窗口高
WINDOW_TITLE = "AI Gesture Magic Camera | AI 手势魔法相机"

CAMERA_INDEX = 0             # 默认主摄像头
CAMERA_CAPTURE_WIDTH = 1280  # 摄像头采集分辨率（提到原生 720p，画面更清晰）
CAMERA_CAPTURE_HEIGHT = 720
MIRROR = True               # 水平镜像，像照镜子一样操作

TARGET_FPS = 60             # 目标帧率
MIN_ACCEPTABLE_FPS = 30     # 验收最低帧率

# 背景压暗强度（越小画面越亮越清晰）。原来 110 偏暗，调亮一些更清晰
BG_DIM_ALPHA = 60

# ============ MediaPipe 手部识别 ============
MAX_HANDS = 2
DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.7

# ============ 粒子系统 ============
DEFAULT_PARTICLE_COUNT = 800    # 默认目标粒子数（电影级，更密集）
MIN_PARTICLE_COUNT = 150
MAX_PARTICLE_COUNT = 2000
PARTICLE_STEP = 100             # 按 +/- 调整的步长

AMBIENT_PARTICLE_COUNT = 70     # 无手时漂浮的星尘数量

# ============ 显示开关（运行时可用快捷键切换）============
SHOW_CAMERA_BACKGROUND = True   # B
SHOW_HAND_LANDMARKS = True      # H
SHOW_FPS = True                 # F

# 低配模式：减少光晕层数、降低粒子上限，换取流畅度
LOW_QUALITY = False

# ============ 手势判定阈值（均相对手掌尺寸归一化）============
# 这些阈值乘以「手腕到中指根」的距离作为参考，对远近/手大小自适应
PINCH_RATIO = 0.45          # 捏合：拇指尖与食指尖距离 < 参考 * 该值
FINGER_EXTEND_RATIO = 1.05  # 指尖到手腕 > 关节到手腕 * 该值，视为伸直
OPEN_PALM_MIN_FINGERS = 4   # 至少几根手指伸直算张开手掌
FIST_MAX_FINGERS = 1        # 至多几根手指伸直算握拳
WAVE_SPEED_RATIO = 0.9      # 挥手：每帧横向位移 > 参考 * 该值
TWO_HAND_CLOSE_RATIO = 2.5  # 双手靠近：掌心间距 < 参考 * 该值
TWO_HAND_FAR_RATIO = 5.0    # 双手拉开：掌心间距 > 参考 * 该值

# ============ 五行主题顺序 ============
# 实际配色由 theme_manager.py 管理；这里保留顺序常量方便其他模块引用。
THEME_ORDER = ["wood", "fire", "earth", "metal", "water"]
DEFAULT_THEME = "wood"

# ============ 各特效参数建议（来自需求文档）============
# 能量球
ENERGY_BALL_RADIUS = 40
ENERGY_BALL_PARTICLES = 120
ENERGY_BALL_ROT_SPEED = 0.04
ENERGY_BALL_GLOW_ALPHA = 120

# 闪电
LIGHTNING_LENGTH = 250
LIGHTNING_SEGMENTS = 12
LIGHTNING_BRANCHES = 3
LIGHTNING_JITTER = 20

# 火焰
FLAME_PARTICLE_COUNT = 80
FLAME_SPEED_Y = -2.0
FLAME_SPREAD = 30
FLAME_LIFE = 40

# 冲击波
SHOCKWAVE_MAX_RADIUS = 520
SHOCKWAVE_SPEED = 17
SHOCKWAVE_THICKNESS = 7

# 魔法阵
MAGIC_CIRCLE_RADIUS = 110
MAGIC_CIRCLE_ROT_SPEED = 0.02

# 屏幕震动
SHAKE_DECAY = 0.85          # 每帧衰减系数
