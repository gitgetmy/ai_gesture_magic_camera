# -*- coding: utf-8 -*-
"""
hand_tracker.py —— 手部识别模块

封装 MediaPipe Hands：输入 RGB 帧，输出每只手的 21 个关键点（已转为屏幕像素坐标）、
左右手标签、掌心中心，以及一些常用关键点的快捷访问。
"""
import mediapipe as mp

import config

# MediaPipe 21 个关键点索引（部分常用）
WRIST = 0
THUMB_TIP = 4
THUMB_IP = 3
THUMB_MCP = 2
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_TIP = 20

# 指尖与对应的近端关节（用于判断手指是否伸直）
FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_PIPS = [INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP]
# 掌心中心由这些关键点求平均得到（较手部抖动更稳定）
PALM_POINTS = [WRIST, INDEX_MCP, MIDDLE_MCP, PINKY_MCP]


class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_HANDS,
            min_detection_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )

    def process(self, frame_rgb):
        """
        处理一帧，返回手部列表，每只手为字典：
        {
            "label": "Right"/"Left",
            "landmarks": [(x1,y1), ... 21 个],  # 屏幕像素坐标
            "center": (cx, cy)                  # 掌心中心
        }
        """
        h, w = frame_rgb.shape[:2]
        # MediaPipe 不修改输入；frame_rgb 已是 RGB
        results = self.hands.process(frame_rgb)
        hands_out = []
        if not results.multi_hand_landmarks:
            return hands_out

        handedness = results.multi_handedness or []
        for idx, hand_lms in enumerate(results.multi_hand_landmarks):
            # 归一化坐标 -> 屏幕像素
            pts = [(lm.x * w, lm.y * h) for lm in hand_lms.landmark]
            label = "Right"
            if idx < len(handedness):
                label = handedness[idx].classification[0].label
            # 掌心中心
            cx = sum(pts[i][0] for i in PALM_POINTS) / len(PALM_POINTS)
            cy = sum(pts[i][1] for i in PALM_POINTS) / len(PALM_POINTS)
            hands_out.append({
                "label": label,
                "landmarks": pts,
                "center": (cx, cy),
            })
        return hands_out

    def close(self):
        self.hands.close()
