# -*- coding: utf-8 -*-
"""
camera.py —— 摄像头读取模块

封装 OpenCV 摄像头：打开、读取帧、镜像、缩放到窗口尺寸、释放。
摄像头无法打开时抛出明确异常，由 main.py 给出友好提示。
"""
import cv2

import config


class CameraError(Exception):
    """摄像头相关错误"""
    pass


class Camera:
    def __init__(self, index=config.CAMERA_INDEX):
        self.index = index
        self.cap = None

    def open(self):
        """打开摄像头。Windows 下优先用 CAP_DSHOW，启动更快、更稳定。"""
        # cv2.CAP_DSHOW 在 Windows 上能避免某些黑屏/卡顿问题；其它系统回退默认
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not self.cap or not self.cap.isOpened():
            # 回退一次：不带后端参数再试
            self.cap = cv2.VideoCapture(self.index)
        if not self.cap or not self.cap.isOpened():
            raise CameraError(
                f"无法打开摄像头（index={self.index}）。\n"
                "请检查：1) 摄像头是否被其它程序占用；"
                "2) 系统是否授予了摄像头权限；"
                "3) 可在 config.py 中修改 CAMERA_INDEX 尝试其它设备。"
            )
        # 设置采集分辨率（采集低分辨率再放大，减轻负载）
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_CAPTURE_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_CAPTURE_HEIGHT)
        return self

    def read_rgb(self):
        """
        读取一帧，返回 (success, frame_rgb)。
        frame_rgb: 已镜像（可选）、已缩放到窗口尺寸、已转 RGB 的 numpy 数组。
        """
        if self.cap is None:
            return False, None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return False, None

        if config.MIRROR:
            frame = cv2.flip(frame, 1)   # 水平镜像
        # 缩放到窗口大小，保证与特效坐标一致
        frame = cv2.resize(frame, (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return True, frame_rgb

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
