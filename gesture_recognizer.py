# -*- coding: utf-8 -*-
"""
gesture_recognizer.py —— 手势判断模块

输入 hand_tracker 给出的手部数据，判断当前手势并映射到特效模式。
所有阈值都相对「手掌参考尺寸」归一化，对远近 / 手大小自适应。

单手手势：open_palm / index_point / pinch / fist / wave / none
双手模式：hands_close / hands_apart / two_open / two_fist / none
"""
from collections import deque
import math

import config
from utils.math_utils import distance, midpoint
from hand_tracker import (
    WRIST, THUMB_TIP, THUMB_MCP, INDEX_TIP, MIDDLE_MCP, MIDDLE_TIP,
    FINGER_TIPS, FINGER_PIPS,
)

# 单手手势 -> 国风招式名称（用于 UI 显示）
GESTURE_TO_MODE = {
    "open_palm": "掌开八卦 Bagua",
    "dao_finger": "奇门休门阵 Xiumen",
    "lightning": "指尖引雷 Lightning",
    "ink_draw": "凌空画符 Ink",
    "sword": "御剑成光 Sword Qi",
    "sweep": "斩风破云 Slash",
    "pinch": "聚气凝丹 Core",
    "fist": "火符爆裂 Flame",
    "none": "Idle",
}


def hand_scale(landmarks):
    """手掌参考尺寸：手腕到中指根的距离。用于归一化所有阈值。"""
    return max(1.0, distance(landmarks[WRIST], landmarks[MIDDLE_MCP]))


def count_extended_fingers(landmarks):
    """
    统计伸直的手指数（不含拇指）。
    判据：指尖到手腕的距离 > 对应中节关节到手腕的距离 * 系数。
    这种基于「离手腕远近」的判据对手部旋转较鲁棒。
    """
    wrist = landmarks[WRIST]
    count = 0
    for tip, pip in zip(FINGER_TIPS, FINGER_PIPS):
        if distance(landmarks[tip], wrist) > distance(landmarks[pip], wrist) * config.FINGER_EXTEND_RATIO:
            count += 1
    return count


def is_pinch(landmarks):
    """拇指尖与食指尖距离 < 参考尺寸 * 阈值，判为捏合"""
    ref = hand_scale(landmarks)
    return distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) < ref * config.PINCH_RATIO


def is_index_point(landmarks):
    """食指伸出、其余手指基本弯曲"""
    wrist = landmarks[WRIST]
    index_tip, index_pip = FINGER_TIPS[0], FINGER_PIPS[0]
    index_out = distance(landmarks[index_tip], wrist) > distance(landmarks[index_pip], wrist) * config.FINGER_EXTEND_RATIO
    # 中指、无名指、小指都没伸直
    others_folded = all(
        distance(landmarks[tip], wrist) <= distance(landmarks[pip], wrist) * config.FINGER_EXTEND_RATIO
        for tip, pip in zip(FINGER_TIPS[1:], FINGER_PIPS[1:])
    )
    return index_out and others_folded


def is_sword_fingers(landmarks):
    """剑指：食指 + 中指伸直，无名指 + 小指弯曲（拇指不限）。"""
    wrist = landmarks[WRIST]

    def extended(tip, pip):
        return distance(landmarks[tip], wrist) > distance(landmarks[pip], wrist) * config.FINGER_EXTEND_RATIO

    index_out = extended(FINGER_TIPS[0], FINGER_PIPS[0])
    middle_out = extended(FINGER_TIPS[1], FINGER_PIPS[1])
    ring_folded = not extended(FINGER_TIPS[2], FINGER_PIPS[2])
    pinky_folded = not extended(FINGER_TIPS[3], FINGER_PIPS[3])
    return index_out and middle_out and ring_folded and pinky_folded


def is_dao_finger(landmarks):
    """道指：食指和小拇指朝上，中指、无名指、拇指收拢。"""
    wrist = landmarks[WRIST]

    def extended(tip, pip):
        return distance(landmarks[tip], wrist) > distance(landmarks[pip], wrist) * config.FINGER_EXTEND_RATIO

    index_out = extended(FINGER_TIPS[0], FINGER_PIPS[0])
    middle_folded = not extended(FINGER_TIPS[1], FINGER_PIPS[1])
    ring_folded = not extended(FINGER_TIPS[2], FINGER_PIPS[2])
    pinky_out = extended(FINGER_TIPS[3], FINGER_PIPS[3])
    thumb_folded = distance(landmarks[THUMB_TIP], wrist) <= distance(landmarks[THUMB_MCP], wrist) * 1.35
    return index_out and pinky_out and middle_folded and ring_folded and thumb_folded


def hand_up_angle(landmarks):
    """手腕到中指指尖的角度；正向合十朝上时约为 -90 度。"""
    wrist = landmarks[WRIST]
    tip = landmarks[MIDDLE_TIP]
    dx = tip[0] - wrist[0]
    dy = tip[1] - wrist[1]
    return math.degrees(math.atan2(dy, dx))


def is_prayer_orientation(landmarks, tolerance=22):
    angle = hand_up_angle(landmarks)
    return -90 - tolerance <= angle <= -90 + tolerance


class GestureRecognizer:
    def __init__(self):
        # 按左右手标签记录掌心历史，用于挥手速度判断
        self._center_history = {"Left": deque(maxlen=5), "Right": deque(maxlen=5)}

    def _hand_velocity(self, label, center, ref):
        """返回 (速度大小, 带符号横向速度)，均相对参考尺寸归一化"""
        history = self._center_history[label]
        history.append(center)
        if len(history) < 2:
            return 0.0, 0.0
        dx = history[-1][0] - history[-2][0]
        dy = history[-1][1] - history[-2][1]
        speed = (dx * dx + dy * dy) ** 0.5 / ref
        return speed, dx / ref

    def recognize_single(self, hand):
        """识别单手手势，返回结果字典"""
        lms = hand["landmarks"]
        ref = hand_scale(lms)
        center = hand["center"]
        speed, vx = self._hand_velocity(hand["label"], center, ref)

        extended = count_extended_fingers(lms)
        pinch = is_pinch(lms)
        moving = speed > config.WAVE_SPEED_RATIO

        # 优先级：剑指 > 道指 > 捏合 > 食指(动=画符 / 静=引雷) > 张开手掌 > 握拳
        if is_sword_fingers(lms):
            gesture = "sword"
        elif is_dao_finger(lms):
            gesture = "dao_finger"
        elif pinch:
            gesture = "pinch"
        elif is_index_point(lms):
            gesture = "ink_draw" if moving else "lightning"
        elif extended >= config.OPEN_PALM_MIN_FINGERS:
            gesture = "sweep" if moving else "open_palm"
        elif extended <= config.FIST_MAX_FINGERS:
            gesture = "fist"
        else:
            gesture = "none"

        # 关键点位置，供特效定位
        position = center
        if gesture in ("lightning", "ink_draw"):
            position = lms[INDEX_TIP]
        elif gesture == "dao_finger":
            position = midpoint(lms[INDEX_TIP], lms[FINGER_TIPS[3]])
        elif gesture == "sword":
            position = lms[INDEX_TIP]
        elif gesture == "pinch":
            position = midpoint(lms[THUMB_TIP], lms[INDEX_TIP])

        return {
            "gesture": gesture,
            "mode": GESTURE_TO_MODE.get(gesture, "Idle"),
            "position": position,
            "label": hand["label"],
            "ref": ref,
            "velocity": speed,
            "vx": vx,
            "extended": extended,
            "landmarks": lms,
            "center": center,
        }

    def recognize_two_hands(self, hand_a, hand_b):
        """识别双手模式，返回结果字典"""
        ca = hand_a["center"]
        cb = hand_b["center"]
        ref = (hand_scale(hand_a["landmarks"]) + hand_scale(hand_b["landmarks"])) / 2.0
        dist = distance(ca, cb)
        center = midpoint(ca, cb)

        ext_a = count_extended_fingers(hand_a["landmarks"])
        ext_b = count_extended_fingers(hand_b["landmarks"])
        both_open = ext_a >= config.OPEN_PALM_MIN_FINGERS and ext_b >= config.OPEN_PALM_MIN_FINGERS
        both_fist = ext_a <= config.FIST_MAX_FINGERS and ext_b <= config.FIST_MAX_FINGERS
        close = dist < ref * config.TWO_HAND_CLOSE_RATIO
        far = dist > ref * config.TWO_HAND_FAR_RATIO
        middle_tips_close = distance(hand_a["landmarks"][MIDDLE_TIP], hand_b["landmarks"][MIDDLE_TIP]) < ref * 0.95
        upright = (
            is_prayer_orientation(hand_a["landmarks"])
            and is_prayer_orientation(hand_b["landmarks"])
        )

        # 优先级：靠近(阴阳合一/太极) > 双手握拳(双重爆炸) >
        #         张开且拉开(大型八卦) > 远离(乾坤展开释放)
        if close and middle_tips_close and upright and not both_fist:
            two_gesture = "hands_close"    # 双手靠近 -> 太极阴阳球
            mode = "阴阳合一 Taiji"
        elif both_fist:
            two_gesture = "two_fist"       # 双手握拳 -> 双重爆炸
            mode = "双拳爆裂 Burst"
        elif both_open and not close:
            two_gesture = "two_open"       # 双手张开且分开 -> 大型八卦阵
            mode = "双掌开卦 Bagua"
        elif far:
            two_gesture = "hands_apart"    # 双手远离 -> 释放
            mode = "乾坤展开 Release"
        else:
            two_gesture = "none"
            mode = "双手 Two Hands"

        return {
            "gesture": two_gesture,
            "mode": mode,
            "position": center,
            "center": center,
            "distance": dist,
            "ref": ref,
            "hand_a_center": ca,
            "hand_b_center": cb,
        }
