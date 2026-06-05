# -*- coding: utf-8 -*-
"""
main.py —— AI 国风玄术手势相机 Pro 程序入口

渲染分层：
  1) 摄像头背景（压暗）
  2) 水墨层、太极图           —— 正常透明度（墨/黑才显示）
  3) 发光特效层 fx（加色）     —— 八卦阵/剑气/龙形/莲花/粒子/冲击波（支持残影拖尾）
  4) 屏幕闪白（大招）
  5) 后处理（暗角/扫描线/噪点）
  6) 关键点 + UI
"""
# Windows 上 mediapipe 原生 DLL 需先于 pygame/cv2 加载
try:
    import mediapipe as _mp  # noqa: F401
except Exception:
    _mp = None

import sys
import math
import random

import pygame

import config
from camera import Camera, CameraError
from particle_system import ParticleSystem
from gesture_recognizer import GestureRecognizer
from gesture_recognizer import count_extended_fingers, hand_scale, is_prayer_orientation
from gesture_state import GestureState
from theme_manager import ThemeManager
from sound_manager import SoundManager
from utils.draw_utils import (cv_frame_to_surface, draw_panel, draw_gradient_bar,
                               draw_glow_text, draw_keycap, draw_separator,
                               scale_color)
from utils.math_utils import clamp
from effects.energy_ball import EnergyBall
from effects.lightning import Lightning
from effects.flame import Flame
from effects.ice import Ice
from effects.shockwave import ShockwaveManager
from effects.trail import Trail
from effects.bagua_circle import BaguaCircle
from effects.taiji_orb import TaijiOrb
from effects.sword_qi import SwordQi
from effects.ink_trail import InkTrail
from effects.dragon_flow import DragonFlow
from effects.lotus_bloom import LotusBloom
from effects.screen_flash import ScreenFlash
from effects.post_processing import PostProcessing
from effects.phoenix_feather import PhoenixFeather
from effects.star_constellation import StarConstellation
from effects.bronze_shield import BronzeShield
from effects.skill_transition import SkillTransition
from effects.season_fx import SeasonFX
from effects.space_ripple import SpaceRipple
from effects.qimen_gate import QimenGate
from effects.taiji_vortex import TaijiVortex
from collections import deque

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
]


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fx = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        self.font = pygame.font.SysFont("microsoftyahei,simhei,arial", 22)
        self.small_font = pygame.font.SysFont("microsoftyahei,simhei,arial", 18)
        self.bagua_font = pygame.font.SysFont("microsoftyahei,simhei,arial", 18)

        self.tm = ThemeManager()
        self.theme = self.tm.theme

        self.show_bg = config.SHOW_CAMERA_BACKGROUND
        self.show_landmarks = config.SHOW_HAND_LANDMARKS
        self.show_fps = config.SHOW_FPS
        self.ghost_on = False
        self.target_particles = config.DEFAULT_PARTICLE_COUNT

        self.camera = Camera()
        self.camera_ok = False
        self.camera_error_msg = ""
        self.sound = SoundManager()

        self.tracker = None
        self.recognizer = GestureRecognizer()
        self.gstate = GestureState()
        self.ps = ParticleSystem(self.theme)

        self.energy_ball = EnergyBall(self.ps, self.theme)
        self.lightning = Lightning(self.ps, self.theme)
        self.flame = Flame(self.ps, self.theme)
        self.ice = Ice(self.ps, self.theme)
        self.shockwave = ShockwaveManager(self.theme)
        self.trail = Trail(self.ps, self.theme)
        self.bagua = BaguaCircle(self.theme, font=self.bagua_font)
        self.taiji = TaijiOrb(self.ps, self.theme)
        self.sword = SwordQi(self.ps, self.theme)
        self.ink = InkTrail(self.ps, self.theme)
        self.dragon = DragonFlow(self.ps, self.theme)
        self.lotus = LotusBloom(self.theme)
        self.flash = ScreenFlash()
        self.postfx = PostProcessing()
        self.phoenix = PhoenixFeather(self.ps, self.theme)
        self.constellation = StarConstellation(self.ps, self.theme)
        self.shield = BronzeShield(self.ps, self.theme)
        self.big_font = pygame.font.SysFont("microsoftyahei,simhei,arial", 46, bold=True)
        self.transition = SkillTransition(self.theme, self.big_font)
        self.season_fx = SeasonFX(self.theme)
        self.sound.set_season(self.season_fx.season_key)
        self.space_ripple = SpaceRipple()
        self.qimen = QimenGate(self.theme)
        self.taiji_vortex = TaijiVortex(self.theme)
        self.postfx.enabled = True
        self.postfx.cinema_on = False
        self.postfx.vignette_on = True

        self._all_themed = [
            self.ps, self.energy_ball, self.lightning, self.flame, self.ice,
            self.shockwave, self.trail, self.bagua, self.taiji, self.sword,
            self.ink, self.dragon, self.lotus, self.phoenix, self.constellation,
            self.shield, self.transition, self.season_fx, self.space_ripple,
            self.qimen, self.taiji_vortex, self.postfx,
        ]

        self.time = 0.0
        self.shake = 0.0
        self.__shake_ref = [0.0]     # mutable ref 供 Lightning 写入震动
        self.lightning.set_flash(self.flash)
        self.lightning.set_shake_ref(self.__shake_ref)
        self.charge = 0.0            # 双手蓄力
        self.single_charge = 0.0     # 单手蓄力
        self.ultimate_cd = 0         # 大招冷却（帧）
        self._lotus_cd = 0           # 莲花触发冷却，避免上抬时连续刷
        self.prev_single = "none"
        self.prev_two = "none"
        self.current_mode = "Idle"
        self._pending_lightning = None
        self._pending_thrust = None
        self._pending_ice = None
        self._taiji_draw = None
        self._shield_center = None       # 本帧护盾中心(手掌下压)
        self._const_center = None        # 本帧星河中心(双手上托)
        self._two_hist = deque(maxlen=6) # 双手中心历史(判断双手上托)
        self._circle_prev_angle = None
        self._circle_accum = 0.0
        self._circle_cd = 0
        self._season_swipe_hist = deque(maxlen=24)
        self._season_swipe_cd = 0
        self._season_interaction = {"point": None, "open": False, "pinch": False}
        self._hands_together_center = None
        self._hands_together_memory = 0
        self._hands_together_last_center = None
        self._single_prayer_frames = 0

    # ---------------- 初始化 ----------------
    def setup(self):
        try:
            self.camera.open()
            self.camera_ok = True
        except CameraError as e:
            self.camera_ok = False
            self.camera_error_msg = str(e)
        if self.camera_ok:
            from hand_tracker import HandTracker
            self.tracker = HandTracker()

    # ---------------- 五行 ----------------
    def _refresh_theme(self):
        self.theme = self.tm.theme
        for obj in self._all_themed:
            if hasattr(obj, "set_theme"):
                obj.set_theme(self.theme)
            else:
                obj.theme = self.theme
        self.sound.set_season(self.season_fx.season_key)

    def set_element_by_key(self, num):
        self.tm.set_by_key(num)
        self._refresh_theme()

    def cycle_element(self):
        self.tm.cycle()
        self._refresh_theme()

    # ---------------- 莲花（上托）----------------
    def _try_lotus(self, center):
        """带冷却地触发莲花绽放，避免上抬过程中每帧连刷"""
        if self._lotus_cd == 0:
            self.lotus.trigger(center)
            self.sound.play("lotus", cooldown=35, volume=0.55)
            self._lotus_cd = 25
            self.current_mode = "掌中生莲 Lotus"

    # ---------------- 大招 ----------------
    def fire_ultimate(self, center, name="乾坤爆发"):
        """全屏多重冲击波 + 闪白 + 多彩大爆炸 + 镜头震动（带冷却）"""
        if self.ultimate_cd > 0:
            return False
        self.shockwave.trigger_multi(center, rings=3)       # 三重彩色冲击波
        self.ps.spawn_burst(center, count=180, speed=17)    # 多色光谱大爆炸
        self.flash.trigger(210, tint=self.theme["core"])
        self.sound.play("ultimate", cooldown=45, volume=0.75)
        self.shake = 22
        self.ultimate_cd = 50
        self.current_mode = name + " Ultimate"
        return True

    # ---------------- 键盘 ----------------
    def handle_keydown(self, key):
        if key == pygame.K_ESCAPE:
            return False
        elif key == pygame.K_r:
            self.ps.clear(); self.shockwave.clear(); self.sword.clear()
            self.ink.clear(); self.dragon.clear(); self.lotus.clear()
            self.phoenix.clear(); self.season_fx.clear(); self.space_ripple.clear()
            self.qimen.clear()
            self.taiji_vortex.clear()
            self._circle_prev_angle = None; self._circle_accum = 0.0; self._circle_cd = 0
            self._season_swipe_hist.clear(); self._season_swipe_cd = 0
            self.charge = 0.0; self.gstate.reset()
        elif key == pygame.K_c:
            self.cycle_element()
        elif key == pygame.K_b:
            self.show_bg = not self.show_bg
        elif key == pygame.K_h:
            self.show_landmarks = not self.show_landmarks
        elif key == pygame.K_f:
            self.show_fps = not self.show_fps
        elif key == pygame.K_p:
            self.postfx.toggle_all()
        elif key == pygame.K_v:
            self.postfx.toggle_vignette()
        elif key == pygame.K_n:
            self.postfx.toggle_noise()
        elif key == pygame.K_m:
            self.postfx.toggle_cinema()
        elif key == pygame.K_l:
            self.ghost_on = not self.ghost_on
        elif key in (pygame.K_1, pygame.K_KP1):
            self.set_element_by_key(1)
        elif key in (pygame.K_2, pygame.K_KP2):
            self.set_element_by_key(2)
        elif key in (pygame.K_3, pygame.K_KP3):
            self.set_element_by_key(3)
        elif key in (pygame.K_4, pygame.K_KP4):
            self.set_element_by_key(4)
        elif key in (pygame.K_5, pygame.K_KP5):
            self.set_element_by_key(5)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.target_particles = min(
                config.MAX_PARTICLE_COUNT, self.target_particles + config.PARTICLE_STEP)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.target_particles = max(
                config.MIN_PARTICLE_COUNT, self.target_particles - config.PARTICLE_STEP)
        return True

    # ---------------- 单手招式 ----------------
    def _track_season_reveal_swipe(self, gesture, center):
        if self._season_swipe_cd > 0:
            self._season_swipe_cd -= 1
        if gesture not in ("open_palm", "sweep"):
            self._season_swipe_hist.clear()
            return False

        self._season_swipe_hist.append(center)
        if self._season_swipe_cd > 0 or len(self._season_swipe_hist) < 8:
            return False

        start = self._season_swipe_hist[0]
        end = self._season_swipe_hist[-1]
        dx = end[0] - start[0]
        dy = abs(end[1] - start[1])
        width = config.WINDOW_WIDTH
        height = config.WINDOW_HEIGHT
        crossed = start[0] < width * 0.32 and end[0] > width * 0.68
        wide_sweep = dx > width * 0.42 and dy < height * 0.32
        if crossed and wide_sweep:
            self.season_fx.trigger_background_reveal()
            self.sound.play("season_reveal", cooldown=80, volume=0.62)
            self.current_mode = f"四季显影 {self.season_fx.name}"
            self._season_swipe_hist.clear()
            self._season_swipe_cd = 80
            return True
        return False

    def handle_single_hand(self, hand):
        res = self.recognizer.recognize_single(hand)
        gesture = res["gesture"]
        center = res["center"]
        pos = res["position"]
        lms = res["landmarks"]
        ref = res["ref"]
        self.current_mode = res["mode"]

        st = self.gstate.update(gesture, center, ref)
        self.single_charge = st["charge"]
        season_reveal = self._track_season_reveal_swipe(gesture, center)

        # 连招：握拳蓄力 -> 张掌 = 乾坤爆发（最高优先，独立于分支）
        if st["combo_release"]:
            if self.fire_ultimate(center, "乾坤爆发"):
                self.bagua.emit_release_beams(self.ps)
                self.prev_single = gesture
                self.prev_two = "none"
                self.bagua.update(center=None)
                return res

        bagua_center = None
        if season_reveal or (gesture in ("open_palm", "sweep") and self.season_fx.reveal_active and self._season_swipe_cd > 0):
            self.bagua.update(center=None)
            self.dragon.update()
            self.prev_single = gesture
            self.prev_two = "none"
            self.current_mode = f"四季显影 {self.season_fx.name}"
            return res

        if gesture == "sword":
            tip = lms[8]
            direction = (lms[8][0] - lms[5][0], lms[8][1] - lms[5][1])
            self._pending_thrust = (tip, direction)
            self.sound.play("sword", cooldown=16, volume=0.52)
            if st["sweep_dir"] != 0 and self.prev_single == "sword":
                self.sword.slash(center, st["sweep_dir"])   # 御剑成光横扫
                self.sound.play("sword_ring", cooldown=22, volume=0.62)
                self.current_mode = "御剑成光 Sword Qi"
            if st["just_charged"]:
                self.fire_ultimate(tip, "剑气爆发")
        elif gesture == "dao_finger":
            self.qimen.emit(pos)
            self.sound.play("qimen", cooldown=36, volume=0.56)
            self.current_mode = "奇门休门阵 Xiumen"
        elif gesture == "sweep":
            # 快速上挥=凤凰火羽；横向挥=龙形
            if st["vy_norm"] < -0.8 and st["sweep_dir"] == 0:
                self.phoenix.emit(center)
                self.current_mode = "凤羽升腾 Phoenix"
            else:
                self.dragon.feed(center)                     # 龙游云海
                self.ink.emit(center, big=True)
                self.current_mode = "龙游云海 Dragon"
        elif gesture == "lightning":
            tip = lms[8]
            direction = (lms[8][0] - lms[5][0], lms[8][1] - lms[5][1])
            self._pending_lightning = (tip, direction)
            self.sound.play("lightning", cooldown=24, volume=0.68)
        elif gesture == "ink_draw":
            self.ink.emit(pos, big=False)
        elif gesture == "open_palm":
            if st["vy_norm"] < -0.8:
                # 缓慢上抬 -> 掌中生莲
                self.current_mode = "掌中生莲 Lotus"
                self._try_lotus(center)
            else:
                scale_mul = 1.0 + self.single_charge * 0.6
                bagua_center = center
                self.bagua.update(center=center, scale_mul=scale_mul)
                self.energy_ball.emit(center, intensity=0.8 + self.single_charge)
        elif gesture == "pinch":
            self.ice.emit(pos)
            self.energy_ball.emit(pos, radius=18, intensity=0.6)
            self._pending_ice = pos
            self.sound.play("ice", cooldown=22, volume=0.52)
        elif gesture == "fist":
            self.flame.emit(center, intensity=1.0)
            self.sound.play("flame", cooldown=20, volume=0.50)
            if st["charging"]:
                self.current_mode = "聚灵成丹 Charging"
                self.ps.spawn_attract(center, count=3)      # 粒子向拳心聚集
            if self.prev_single != "fist":
                self.shockwave.trigger(center)
                self.ps.spawn_burst(center, count=40, speed=9)
                self.shake = 10

        if bagua_center is None:
            self.bagua.update(center=None)
        # 非挥动状态让龙尾消散
        if gesture != "sweep":
            self.dragon.update()

        self.prev_single = gesture
        self.prev_two = "none"
        return res

    # ---------------- 双手招式 ----------------
    def _track_two_hand_circle(self, res):
        if self._circle_cd > 0:
            self._circle_cd -= 1
            return False

        dist = max(1.0, res["distance"])
        ref = max(1.0, res["ref"])
        if dist < ref * 1.25:
            self._circle_prev_angle = None
            self._circle_accum *= 0.82
            return False

        ax, ay = res["hand_a_center"]
        bx, by = res["hand_b_center"]
        angle = math.atan2(by - ay, bx - ax)
        if self._circle_prev_angle is None:
            self._circle_prev_angle = angle
            return False

        delta = angle - self._circle_prev_angle
        while delta > math.pi:
            delta -= math.tau
        while delta < -math.pi:
            delta += math.tau
        self._circle_prev_angle = angle

        if abs(delta) > 0.75:
            self._circle_accum *= 0.5
            return False
        if abs(delta) > 0.035:
            if self._circle_accum and (self._circle_accum > 0) != (delta > 0):
                self._circle_accum *= 0.35
            self._circle_accum += delta
        else:
            self._circle_accum *= 0.96

        if abs(self._circle_accum) >= math.tau * 0.62:
            self.taiji_vortex.emit(res["center"], direction=self._circle_accum, radius=dist * 0.78)
            self.shockwave.trigger(res["center"])
            self.sound.play("vortex", cooldown=45, volume=0.58)
            self.current_mode = "太极旋涡 Vortex"
            self._circle_accum = 0.0
            self._circle_cd = 36
            return True
        return False

    def handle_two_hands(self, hand_a, hand_b):
        res = self.recognizer.recognize_two_hands(hand_a, hand_b)
        gesture = res["gesture"]
        center = res["center"]
        self.current_mode = res["mode"]
        self.gstate.reset()
        self.single_charge = 0.0
        self.dragon.update()

        bagua_center = None
        if gesture in ("two_open", "hands_apart") and self._track_two_hand_circle(res):
            self.bagua.update(center=None)
            self.prev_two = "circle_vortex"
            self.prev_single = "none"
            return

        if gesture == "hands_close":
            self._circle_prev_angle = None
            self._circle_accum = 0.0
            self.charge = min(1.4, self.charge + 0.03)
            radius = clamp(res["distance"] * 0.5, 50, 150) * (0.7 + 0.3 * self.charge)
            self.sound.play("zen", cooldown=90, volume=0.48)
            self._hands_together_center = center
            self._hands_together_last_center = center
            self._hands_together_memory = 10
            self.taiji.update()
            self.taiji.emit_particles(center, radius, intensity=0.6 + self.charge)
            self.ps.spawn_attract(res["hand_a_center"], count=2)
            self.ps.spawn_attract(res["hand_b_center"], count=2)
            self._taiji_draw = (center, radius)
        elif gesture == "two_open":
            bagua_center = center
            self.bagua.update(center=center, scale_mul=2.0)
            self.energy_ball.emit(center, radius=40, intensity=0.9)
        elif gesture == "two_fist":
            self._circle_prev_angle = None
            self._circle_accum = 0.0
            if self.prev_two != "two_fist":
                self.fire_ultimate(res["hand_a_center"], "双拳爆裂")
                self.shockwave.trigger(res["hand_b_center"])
                self.ps.spawn_burst(res["hand_b_center"], count=40, speed=11)
        elif gesture == "hands_apart":
            # 八方震荡 / 乾坤展开：之前在凝太极则释放
            if self.charge > 0.4:
                self.bagua.center = center
                self.bagua.emit_release_beams(self.ps)
                self.fire_ultimate(center, "八方震荡")
            self.charge = 0.0
        else:
            self._circle_prev_angle = None
            self._circle_accum *= 0.85
            self.charge = max(0.0, self.charge - 0.02)

        if bagua_center is None:
            self.bagua.update(center=None)

        self.prev_two = gesture
        self.prev_single = "none"

    def _recover_hands_together_from_single(self, hand, single_gesture):
        if single_gesture in ("dao_finger", "fist", "pinch", "lightning", "ink_draw", "sword", "sweep"):
            self._hands_together_memory = 0
            return None
        if self._hands_together_memory <= 0 or self._hands_together_last_center is None:
            return None
        if not is_prayer_orientation(hand["landmarks"], tolerance=24):
            self._hands_together_memory = 0
            return None

        hx, hy = hand["center"]
        lx, ly = self._hands_together_last_center
        dist = ((hx - lx) ** 2 + (hy - ly) ** 2) ** 0.5
        if dist > 130:
            self._hands_together_memory = 0
            return None

        self._hands_together_memory -= 1
        center = ((hx + lx) * 0.5, (hy + ly) * 0.5)
        self._hands_together_last_center = center
        return center

    def _single_prayer_candidate(self, hand, single_gesture):
        if single_gesture in ("dao_finger", "fist", "pinch", "lightning", "ink_draw", "sword", "sweep"):
            self._single_prayer_frames = 0
            return None
        lms = hand["landmarks"]
        if not is_prayer_orientation(lms, tolerance=18):
            self._single_prayer_frames = 0
            return None
        ref = hand_scale(lms)
        extended = count_extended_fingers(lms)
        tips = [lms[i] for i in (8, 12, 16, 20)]
        tip_spread_x = max(p[0] for p in tips) - min(p[0] for p in tips)
        tip_spread_y = max(p[1] for p in tips) - min(p[1] for p in tips)
        avg_tip_x = sum(p[0] for p in tips) / len(tips)
        wrist_y = lms[0][1]
        wrist_x = lms[0][0]
        highest_tip_y = min(p[1] for p in tips)
        vertical_length = wrist_y - highest_tip_y
        compact_fingers = tip_spread_x < ref * 0.62 and tip_spread_y < ref * 0.62
        tall_silhouette = vertical_length > ref * 1.42
        centered_axis = abs(avg_tip_x - wrist_x) < ref * 0.48
        if extended >= 3 and compact_fingers and tall_silhouette and centered_axis:
            self._single_prayer_frames += 1
        else:
            self._single_prayer_frames = 0
        if self._single_prayer_frames >= 8:
            return hand["center"]
        return None

    def _build_season_interaction(self, hands):
        """Return the fingertip/palm state used by the seasonal particle field."""
        if not hands:
            return {"point": None, "open": False, "pinch": False}

        if len(hands) >= 2:
            center = (
                (hands[0]["center"][0] + hands[1]["center"][0]) * 0.5,
                (hands[0]["center"][1] + hands[1]["center"][1]) * 0.5,
            )
            return {
                "point": center,
                "open": self.prev_two in ("two_open", "hands_apart", "hands_close"),
                "pinch": self.prev_two in ("two_fist",),
            }

        hand = hands[0]
        lms = hand["landmarks"]
        point = lms[8] if len(lms) > 8 else hand["center"]
        return {
            "point": point,
            "open": self.prev_single in ("open_palm", "sweep"),
            "pinch": self.prev_single in ("pinch", "fist"),
        }

    # ---------------- 每帧逻辑 ----------------
    def update_frame(self, frame_rgb):
        hands = self.tracker.process(frame_rgb) if self.tracker else []
        self._pending_lightning = None
        self._pending_thrust = None
        self._pending_ice = None
        self._taiji_draw = None
        self._shield_center = None
        self._const_center = None
        self._hands_together_center = None
        hand_center = None

        if len(hands) >= 2:
            self._single_prayer_frames = 0
            self.handle_two_hands(hands[0], hands[1])
            hand_center = hands[0]["center"]
        elif len(hands) == 1:
            single_res = self.handle_single_hand(hands[0])
            hand_center = hands[0]["center"]
            recovered_center = self._recover_hands_together_from_single(hands[0], single_res["gesture"])
            candidate_center = self._single_prayer_candidate(hands[0], single_res["gesture"])
            if candidate_center is not None:
                self._hands_together_last_center = candidate_center
                self._hands_together_memory = 8
                recovered_center = candidate_center
            if recovered_center is not None:
                self._hands_together_center = recovered_center
                self.current_mode = "阴阳合一 Taiji"
        else:
            self.current_mode = "Idle"
            self.charge = max(0.0, self.charge - 0.02)
            self.single_charge = 0.0
            self.gstate.reset()
            self.dragon.update()
            self._two_hist.clear()
            self._circle_prev_angle = None
            self._circle_accum *= 0.82
            self._single_prayer_frames = 0
            self.ps.ambient(config.WINDOW_WIDTH, config.WINDOW_HEIGHT,
                            min(config.AMBIENT_PARTICLE_COUNT, self.target_particles))
            self.bagua.update(center=None)
            self._hands_together_memory = max(0, self._hands_together_memory - 1)

        if self._hands_together_center is None and len(hands) != 1:
            self._hands_together_memory = max(0, self._hands_together_memory - 1)

        self._season_interaction = self._build_season_interaction(hands)

        # 持续型新特效：有中心则显现，否则淡出（护盾消失会碎裂）
        self.shield.update(self._shield_center)
        self.constellation.update(self._const_center)

        # 技能过渡：招式名变化时触发过场
        tc = hand_center or (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        if self.current_mode != "奇门休门阵 Xiumen":
            self.transition.maybe_trigger(self.current_mode, tc)
        self.transition.update()
        self.phoenix.update()

        # 自动降载：帧率过低时减少粒子上限
        if self.clock.get_fps() and self.clock.get_fps() < 25 and self.target_particles > config.MIN_PARTICLE_COUNT:
            self.target_particles = max(config.MIN_PARTICLE_COUNT, self.target_particles - 50)

        self.ps.max_particles = self.target_particles
        self.ps.update()
        self.shockwave.update()
        self.sword.update()
        self.ink.update()
        self.lotus.update()
        self.flash.update()
        self.lightning.update()
        self.qimen.update()
        self.taiji_vortex.update()
        self.energy_ball.update()
        self.flame.update()
        self.ice.update()
        self.season_fx.update(config.WINDOW_WIDTH, config.WINDOW_HEIGHT,
                              self._season_interaction)
        self.space_ripple.update(self._hands_together_center is not None,
                                 self._hands_together_center)
        self.sound.update()
        if self.ultimate_cd > 0:
            self.ultimate_cd -= 1
        if self._lotus_cd > 0:
            self._lotus_cd -= 1
        # 震动同步：闪电等特效可通过 __shake_ref[0] 叠加震动
        self.shake = max(self.shake, self.__shake_ref[0])
        self.shake *= config.SHAKE_DECAY
        self.__shake_ref[0] *= config.SHAKE_DECAY
        if self.shake < 0.5:
            self.shake = 0.0
        if self.__shake_ref[0] < 0.3:
            self.__shake_ref[0] = 0.0
        return hands

    # ---------------- 渲染 ----------------
    def render(self, frame_rgb, hands):
        ox = random.uniform(-self.shake, self.shake)
        oy = random.uniform(-self.shake, self.shake)
        qimen_active = self.qimen.active

        # 1) 背景
        self.screen.fill(self.theme["bg_tint"])
        if self.show_bg and frame_rgb is not None:
            bg = cv_frame_to_surface(frame_rgb)
            bg.set_alpha(72 if qimen_active else 218)
            self.screen.blit(bg, (ox, oy))
            dark = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            dark.fill(self.theme["bg_tint"])
            dark.set_alpha(174 if qimen_active else 46)
            self.screen.blit(dark, (0, 0))
            self.season_fx.draw_background(self.screen, alpha=42 if qimen_active else 82)
        else:
            self.season_fx.draw_background(self.screen, alpha=45 if qimen_active else 255)
        self.season_fx.draw_background_reveal(self.screen)
        self.qimen.draw_void(self.screen)
        self.space_ripple.draw_dim(self.screen)

        # 2) 水墨 + 太极（正常透明度）
        self.ink.draw(self.screen)
        if self._taiji_draw is not None:
            tc, tr = self._taiji_draw
            self.taiji.draw(self.screen, tc, tr)

        # 3) 发光特效层（加色，可残影拖尾）
        if self.ghost_on:
            fade = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            fade.fill((0, 0, 0)); fade.set_alpha(60)
            self.fx.blit(fade, (0, 0))
        else:
            self.fx.fill((0, 0, 0))
        if self._pending_lightning:
            self.lightning.emit(self._pending_lightning[0], self._pending_lightning[1], self.fx)
        self.lightning.draw_starfield(self.screen)
        self.lightning.draw_ghosts(self.fx)   # 残影电弧（全局拖尾感）
        if self._pending_thrust:
            self.sword.thrust(self._pending_thrust[0], self._pending_thrust[1], self.fx)
        self.energy_ball.draw_core(self.fx)
        self.flame.draw(self.fx)
        if self._pending_ice:
            self.ice.draw_crystals(self.fx, self._pending_ice, self.time)
        self.bagua.draw(self.fx)
        self.sword.draw(self.fx)
        self.dragon.draw(self.fx)
        self.lotus.draw(self.fx)
        self.phoenix.draw(self.fx)
        self.constellation.draw(self.fx)
        self.shield.draw(self.fx)
        self.qimen.draw(self.fx)
        self.taiji_vortex.draw(self.fx)
        self.shockwave.draw(self.fx)
        self.transition.draw_fx(self.fx)       # 过渡彩环 + 放射光束
        self.ink.draw_glow_points(self.fx)
        self.ps.draw(self.fx)
        # Seasonal ambience is part of the glow pass so it blends with spells.
        if not qimen_active:
            self.season_fx.draw(self.screen, self.fx)
        self.space_ripple.draw(self.fx)
        self.screen.blit(self.fx, (ox, oy), special_flags=pygame.BLEND_RGB_ADD)

        # 4) 屏幕闪白
        self.flash.draw(self.screen)
        # 5) 后处理
        self.postfx.apply(self.screen)
        # 6) 技能过渡横幅（清晰，置于后处理之上）
        if not qimen_active:
            self.transition.draw_overlay(self.screen)
        # 7) 关键点 + UI
        if self.show_landmarks:
            self.draw_landmarks(hands)
        self.draw_ui(len(hands))
        self.draw_decorative_frame()
        pygame.display.flip()

    def draw_landmarks(self, hands):
        """绘制手部关键点——带辉光效果的骨架。"""
        col = self.theme["palette"][0]
        core = self.theme["core"]
        accent = self.theme.get("accent", col)
        for hand in hands:
            lms = hand["landmarks"]
            # 连线——先画外辉光再画主线
            for a, b in HAND_CONNECTIONS:
                p1, p2 = (int(lms[a][0]), int(lms[a][1])), (int(lms[b][0]), int(lms[b][1]))
                # 辉光线（宽）
                pygame.draw.line(self.screen, scale_color(col, 0.25),
                                 p1, p2, 4)
                # 主线
                pygame.draw.line(self.screen, col, p1, p2, 2)
            # 关节点——辉光圆 + 核心亮圆
            for i, p in enumerate(lms):
                px, py = int(p[0]), int(p[1])
                # 指尖高亮（食指8、中指12、无名指16、小指20、拇指4）
                is_tip = i in (4, 8, 12, 16, 20)
                if is_tip:
                    pygame.draw.circle(self.screen, scale_color(accent, 0.3),
                                       (px, py), 8)
                    pygame.draw.circle(self.screen, core, (px, py), 5)
                    pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 2)
                else:
                    pygame.draw.circle(self.screen, scale_color(col, 0.35),
                                       (px, py), 5)
                    pygame.draw.circle(self.screen, core, (px, py), 3)

    def draw_ui(self, hand_count):
        """绘制精美的国风 HUD 界面。"""
        accent = self.theme.get("accent", self.theme["palette"][1])
        accent2 = self.theme.get("accent2", self.theme["palette"][2])

        # ==================== 左上角：主信息面板 ====================
        panel_x, panel_y = 14, 14
        panel_w, panel_h = 310, 260
        panel_bg = (14, 16, 28, 185)
        panel_border = accent

        # 面板主体（微带透明的深色背景）
        draw_panel(self.screen, (panel_x, panel_y, panel_w, panel_h),
                   bg_color=panel_bg, border_color=panel_border, radius=14, border_width=1)

        # 面板顶部装饰线
        line_y = panel_y + 2
        pygame.draw.line(self.screen, accent,
                         (panel_x + 20, line_y), (panel_x + panel_w - 20, line_y), 2)

        # ---- 标题行：五行元素标识 + 名称 ----
        element_cn = self.theme.get("cn_name", "?")
        title_x = panel_x + 20
        title_y = panel_y + 18

        # 元素徽章（小方块 + 发光字）
        badge_rect = (title_x, title_y - 3, 36, 36)
        pygame.draw.rect(self.screen, (20, 22, 36), badge_rect, border_radius=8)
        pygame.draw.rect(self.screen, accent, badge_rect, 2, border_radius=8)
        badge_text = self.small_font.render(element_cn, True, accent)
        self.screen.blit(badge_text, (title_x + 9, title_y + 5))

        # 标题文字
        title_text = self.font.render("AI 国风玄术手势相机", True, self.theme["core"])
        self.screen.blit(title_text, (title_x + 48, title_y + 2))

        # ---- 分隔线 ----
        sep_y = title_y + 44
        draw_separator(self.screen, panel_x + 16, sep_y, panel_w - 32,
                       color=accent, alpha=70)

        # ---- 信息行 ----
        info_x = panel_x + 20
        info_y = sep_y + 12
        line_h = 26

        # 四季流转（高亮显示当前季节）
        season_name = self.season_fx.name
        season_cn = self.season_fx.cn_name
        season_color = self.theme.get("accent2", accent)
        season_text = self.small_font.render(f"四季 {season_name}", True, season_color)
        self.screen.blit(season_text, (info_x, info_y))
        info_y += line_h

        # 当前招式（高亮显示）
        mode_color = accent2 if "Ultimate" in self.current_mode else accent
        draw_glow_text(self.screen, self.small_font,
                       f"招式 {self.current_mode}",
                       mode_color, (info_x, info_y),
                       glow_radius=1 if "Idle" in self.current_mode else 2)
        info_y += line_h

        # 五行 / 手数 / 粒子
        hands_label = ("双手" if hand_count >= 2 else "单手" if hand_count == 1 else "无")
        info_lines = [
            f"五行 {self.theme['name']}",
            f"手势 {hands_label}  ·  粒子 {self.ps.count}/{self.target_particles}",
            f"后处理 {self.postfx.status_text()}  ·  残影 {'开' if self.ghost_on else '关'}",
        ]
        for line in info_lines:
            self.screen.blit(self.small_font.render(line, True, (210, 215, 230)),
                             (info_x, info_y))
            info_y += line_h

        # ---- FPS（面板内右下角）----
        if self.show_fps:
            fps = int(self.clock.get_fps())
            fps_color = (120, 255, 160) if fps >= 50 else (255, 220, 100) if fps >= 30 else (255, 120, 100)
            fps_text = self.small_font.render(f"FPS {fps}", True, fps_color)
            self.screen.blit(fps_text, (panel_x + panel_w - fps_text.get_width() - 20, info_y + 4))

        # ---- 大招冷却指示 ----
        if self.ultimate_cd > 0:
            cd_y = panel_y + panel_h + 6
            cd_ratio = 1.0 - self.ultimate_cd / 50.0
            cd_w = panel_w
            cd_h = 6
            # 背景
            pygame.draw.rect(self.screen, (30, 32, 44),
                             (panel_x, cd_y, cd_w, cd_h), border_radius=3)
            # 冷却进度
            if cd_ratio > 0:
                fill_w = int(cd_w * cd_ratio)
                draw_gradient_bar(self.screen,
                                  (panel_x, cd_y, fill_w, cd_h),
                                  accent, accent2, bg_color=(30, 32, 44), radius=3)
            cd_label = self.small_font.render(
                f"大招冷却 {self.ultimate_cd}", True, (255, 185, 140))
            self.screen.blit(cd_label, (panel_x + panel_w + 10, cd_y - 6))

        # ==================== 蓄力条（面板下方）====================
        charge = max(self.single_charge, self.charge / 1.4)
        charge_y = panel_y + panel_h + 18
        if self.ultimate_cd > 0:
            charge_y += 18

        if charge > 0.04:
            bx, by, bw, bh = panel_x, charge_y, panel_w, 14
            # 背景槽
            pygame.draw.rect(self.screen, (24, 26, 38),
                             (bx, by, bw, bh), border_radius=7)
            # 渐变填充
            fill_w = int(bw * min(1.0, charge))
            if fill_w > 0:
                draw_gradient_bar(self.screen, (bx, by, fill_w, bh),
                                  accent, accent2, bg_color=(24, 26, 38), radius=7)
            # 槽位边框
            pygame.draw.rect(self.screen, (*accent, 80),
                             (bx, by, bw, bh), 1, border_radius=7)

            # 标签
            charge_label = self.small_font.render("蓄力", True, self.theme["core"])
            self.screen.blit(charge_label, (bx + bw + 10, by - 2))

            # 蓄力百分比数字
            pct = int(min(1.0, charge) * 100)
            pct_text = self.small_font.render(f"{pct}%", True, accent)
            self.screen.blit(pct_text, (bx + fill_w + 6, by - 2))

            charge_y += 22

        # ==================== 底部提示栏 ====================
        hint_panel_h = 50
        hint_y = config.WINDOW_HEIGHT - hint_panel_h - 10
        hint_x = 14
        hint_w = config.WINDOW_WIDTH - 28

        draw_panel(self.screen, (hint_x, hint_y, hint_w, hint_panel_h),
                   bg_color=(14, 16, 28, 175), border_color=accent,
                   radius=12, border_width=1)

        # 快捷键以键帽样式排列
        key_defs = [
            ("ESC", "退出"), ("R", "重置"), ("1-5", "五行"),
            ("C", "切换属性"), ("B", "背景"), ("H", "关键点"),
            ("F", "帧率"), ("P", "后处理"), ("V", "暗角"),
            ("M", "电影感"), ("N", "噪点"), ("L", "残影"), ("+/-", "粒子"),
        ]
        kx = hint_x + 16
        ky = hint_y + 10
        for key_text, label in key_defs:
            tw = self.small_font.size(key_text)[0] + 12
            draw_keycap(self.screen, self.small_font, key_text,
                        (kx, ky), key_color=(45, 48, 65))
            lbl = self.small_font.render(label, True, (180, 190, 215))
            self.screen.blit(lbl, (kx + tw + 2, ky + 2))
            kx += tw + lbl.get_width() + 16
            if kx > hint_x + hint_w - 120:
                break   # 超出面板则不继续绘制

        # ==================== 中央空闲提示 ====================
        if hand_count == 0:
            # 大号发光提示
            tip_alpha = int(160 + 50 * math.sin(self.time * 1.8))  # 呼吸效果
            tip_text = self.big_font.render("把手放进画面 · 开始施法", True, self.theme["core"])
            tip_text.set_alpha(max(60, min(255, tip_alpha)))
            tip_x = config.WINDOW_WIDTH // 2 - tip_text.get_width() // 2
            tip_y = config.WINDOW_HEIGHT // 2 - tip_text.get_height() // 2
            # 光晕背景
            glow_surf = self.big_font.render("把手放进画面 · 开始施法", True,
                                             scale_color(accent, 0.25))
            glow_surf.set_alpha(max(20, min(100, tip_alpha // 2)))
            self.screen.blit(glow_surf, (tip_x - 3, tip_y - 3))
            self.screen.blit(glow_surf, (tip_x + 3, tip_y + 3))
            self.screen.blit(tip_text, (tip_x, tip_y))

            # 副提示
            sub_tip = self.small_font.render("用五行手势释放国风玄术特效", True, (200, 210, 230))
            sub_tip.set_alpha(max(40, min(200, tip_alpha + 40)))
            self.screen.blit(sub_tip,
                             (config.WINDOW_WIDTH // 2 - sub_tip.get_width() // 2,
                              tip_y + 50))

    def draw_decorative_frame(self):
        """绘制国风装饰边框——四角纹样 + 细边框。"""
        accent = self.theme.get("accent", self.theme["palette"][1])
        w, h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        margin = 8
        corner_len = 28
        corner_gap = 4

        # 四角 L 形纹样
        corners = [
            [(margin, margin + corner_len), (margin, margin),
             (margin + corner_len, margin)],
            [(w - margin - corner_len, margin), (w - margin, margin),
             (w - margin, margin + corner_len)],
            [(margin, h - margin - corner_len), (margin, h - margin),
             (margin + corner_len, h - margin)],
            [(w - margin - corner_len, h - margin), (w - margin, h - margin),
             (w - margin, h - margin - corner_len)],
        ]

        for pts in corners:
            pygame.draw.lines(self.screen, (*accent, 30), False, pts, 4)
            pygame.draw.lines(self.screen, (*accent, 70), False, pts, 2)

        # 顶部和底部细线
        top_surf = pygame.Surface((w - 2 * margin - 2 * corner_len, 1), pygame.SRCALPHA)
        top_surf.fill((*accent, 40))
        self.screen.blit(top_surf, (margin + corner_len + corner_gap, margin))
        self.screen.blit(top_surf, (margin + corner_len + corner_gap, h - margin))

        # 四角小菱形装饰
        ds = 5
        for cx, cy in [(margin + corner_len // 2, margin + corner_len // 2),
                       (w - margin - corner_len // 2, margin + corner_len // 2),
                       (margin + corner_len // 2, h - margin - corner_len // 2),
                       (w - margin - corner_len // 2, h - margin - corner_len // 2)]:
            pts = [(cx, cy - ds), (cx + ds, cy), (cx, cy + ds), (cx - ds, cy)]
            pygame.draw.polygon(self.screen, (*accent, 80), pts)
            pygame.draw.polygon(self.screen, (*accent, 40), pts, 1)

    def draw_camera_error(self):
        """绘制摄像头错误界面——居中、有面板感的提示。"""
        self.screen.fill((10, 8, 18))

        # 中央错误面板
        pw, ph = 560, 280
        px = (config.WINDOW_WIDTH - pw) // 2
        py = (config.WINDOW_HEIGHT - ph) // 2

        # 外光晕
        glow_surf = pygame.Surface((pw + 40, ph + 40), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (255, 80, 80, 15),
                         glow_surf.get_rect(), border_radius=20)
        self.screen.blit(glow_surf, (px - 20, py - 20))

        # 面板主体
        draw_panel(self.screen, (px, py, pw, ph),
                   bg_color=(22, 12, 16, 235),
                   border_color=(180, 60, 60), radius=16, border_width=2)

        # 顶部装饰线
        line_y = py + 3
        pygame.draw.line(self.screen, (200, 70, 70),
                         (px + 30, line_y), (px + pw - 30, line_y), 2)

        # 错误图标（⚠）
        icon_text = self.big_font.render("⚠", True, (255, 140, 120))
        self.screen.blit(icon_text, (px + pw // 2 - icon_text.get_width() // 2, py + 30))

        # 错误标题
        title = self.font.render("摄像头错误  Camera Error", True, (255, 150, 140))
        self.screen.blit(title, (px + pw // 2 - title.get_width() // 2, py + 90))

        # 错误详情
        y = py + 130
        for line in self.camera_error_msg.split("\n"):
            det = self.small_font.render(line, True, (220, 200, 200))
            self.screen.blit(det, (px + pw // 2 - det.get_width() // 2, y))
            y += 26

        # 退出提示
        esc_tip = self.small_font.render("按 ESC 键退出", True, (190, 185, 195))
        self.screen.blit(esc_tip, (px + pw // 2 - esc_tip.get_width() // 2, py + ph - 36))
        pygame.display.flip()

    # ---------------- 主循环 ----------------
    def run(self):
        self.setup()
        running = True
        while running:
            self.time += 0.05
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if not self.handle_keydown(event.key):
                        running = False
            if not self.camera_ok:
                self.draw_camera_error()
                self.clock.tick(30)
                continue
            ok, frame_rgb = self.camera.read_rgb()
            if not ok:
                self.clock.tick(config.TARGET_FPS)
                continue
            hands = self.update_frame(frame_rgb)
            self.render(frame_rgb, hands)
            self.clock.tick(config.TARGET_FPS)
        self.cleanup()

    def cleanup(self):
        self.sound.stop()
        if self.tracker:
            self.tracker.close()
        self.camera.release()
        pygame.quit()


def main():
    try:
        App().run()
    except Exception as e:
        print(f"[错误] 程序异常退出：{e}")
        pygame.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
