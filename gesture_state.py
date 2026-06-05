# -*- coding: utf-8 -*-
"""
gesture_state.py —— 手势状态机

单帧手势只能回答"现在是什么手势"，但国风招式需要"连续动作"判断，例如：
  - 静止蓄力：同一手势保持不动超过若干帧 -> 蓄力进度增长，满了可放大招
  - 横扫：手掌在短时间内大幅横向移动 -> 触发剑气横斩

本模块跟踪最近若干帧的手势与位置，给出 charge（蓄力进度）与运动信息，
供 main 编排"蓄力 -> 释放"这类组合技。
"""
from collections import deque

from utils.math_utils import distance


class GestureState:
    def __init__(self, hold_frames=45):
        # 蓄力所需帧数（约 0.7~1.5 秒，取决于帧率）
        self.hold_frames = hold_frames
        self.prev_gesture = "none"
        self.hold_count = 0          # 当前手势已保持的帧数
        self.charge = 0.0            # 蓄力进度 0~1
        self._pos_history = deque(maxlen=8)
        self.released = False        # 本帧是否刚好达到满蓄力（边沿）
        self._fist_armed = 0         # 握拳蓄满后的"待释放"倒计时帧

    def update(self, gesture, position, ref):
        """
        gesture: 当前帧单手手势
        position: 当前手部中心
        ref: 手掌参考尺寸（用于归一化位移）
        返回 dict：charge / charging / just_charged / sweep_dir / vy_norm / combo_release
        """
        self.released = False
        self._pos_history.append(position)

        # 是否基本静止（蓄力要求手不大动）
        moving = False
        if len(self._pos_history) >= 2:
            step = distance(self._pos_history[-1], self._pos_history[-2]) / max(1.0, ref)
            moving = step > 0.25

        chargeable = gesture in ("open_palm", "sword", "fist")

        if chargeable and gesture == self.prev_gesture and not moving:
            self.hold_count += 1
        else:
            self.hold_count = 0

        prev_charge = self.charge
        self.charge = min(1.0, self.hold_count / self.hold_frames) if chargeable else 0.0
        just_charged = prev_charge < 1.0 <= self.charge

        # 横扫方向（最近几帧横向净位移）
        sweep_dir = 0
        vy_norm = 0.0
        if len(self._pos_history) >= 4:
            dx = (self._pos_history[-1][0] - self._pos_history[-4][0]) / max(1.0, ref)
            dy = (self._pos_history[-1][1] - self._pos_history[-4][1]) / max(1.0, ref)
            if abs(dx) > 1.4:
                sweep_dir = 1 if dx > 0 else -1
            vy_norm = dy   # 负=向上，正=向下

        # 连招：握拳蓄到一定程度 -> 短时间内张开手掌 = 乾坤爆发
        combo_release = False
        if gesture == "fist" and self.charge >= 0.6:
            self._fist_armed = 12           # 蓄满握拳后留 12 帧窗口
        elif gesture == "open_palm" and self._fist_armed > 0:
            combo_release = True
            self._fist_armed = 0
        else:
            self._fist_armed = max(0, self._fist_armed - 1)

        self.prev_gesture = gesture
        return {
            "charge": self.charge,
            "charging": chargeable and self.hold_count > 3,
            "just_charged": just_charged,
            "sweep_dir": sweep_dir,
            "vy_norm": vy_norm,
            "combo_release": combo_release,
        }

    def reset(self):
        self.hold_count = 0
        self.charge = 0.0
        self.prev_gesture = "none"
        self._fist_armed = 0
        self._pos_history.clear()
