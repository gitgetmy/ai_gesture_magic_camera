# -*- coding: utf-8 -*-
"""Lightweight procedural sound effects and seasonal ambience."""
import math

import numpy as np
import pygame


SAMPLE_RATE = 44100


class SoundManager:
    def __init__(self):
        self.enabled = True
        self.ready = False
        self.current_season = None
        self._cooldowns = {}
        self._ambient_channel = None
        self._fx_channels = []
        self.ambience = {}
        self.effects = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self._ambient_channel = pygame.mixer.Channel(0)
            self._fx_channels = [pygame.mixer.Channel(i) for i in range(1, 12)]
            self._build_sounds()
            self.ready = True
        except Exception:
            self.ready = False
            self.enabled = False

    def _build_sounds(self):
        self.ambience = {
            "spring": _make_season_ambience("spring", seconds=4.2, volume=0.30),
            "summer": _make_season_ambience("summer", seconds=4.0, volume=0.28),
            "late_summer": _make_season_ambience("late_summer", seconds=4.4, volume=0.26),
            "autumn": _make_season_ambience("autumn", seconds=4.2, volume=0.28),
            "winter": _make_season_ambience("winter", seconds=4.5, volume=0.25),
        }
        self.effects = {
            "season_reveal": _make_wind_reveal(1.05, volume=0.42),
            "lightning": _make_natural_thunder(0.95, volume=0.62),
            "sword": _make_sword_whoosh(0.48, volume=0.46),
            "sword_ring": _make_sword_whoosh(0.8, volume=0.42, ring=True),
            "qimen": _make_ice_chime(0.65, volume=0.38),
            "zen": _make_soft_bell(1.45, base=174, volume=0.36),
            "flame": _make_fire_whoosh(0.55, volume=0.42),
            "ice": _make_ice_chime(0.42, volume=0.32),
            "lotus": _make_soft_bell(1.0, base=294, volume=0.28),
            "ultimate": _make_soft_impact(0.9, volume=0.58),
            "vortex": _make_wind_reveal(0.9, volume=0.34),
        }

    def update(self):
        for key in list(self._cooldowns):
            self._cooldowns[key] -= 1
            if self._cooldowns[key] <= 0:
                del self._cooldowns[key]

    def set_season(self, season_key):
        if not self.ready or not self.enabled or season_key == self.current_season:
            return
        sound = self.ambience.get(season_key)
        if sound is None or self._ambient_channel is None:
            return
        self.current_season = season_key
        self._ambient_channel.play(sound, loops=-1, fade_ms=700)
        self._ambient_channel.set_volume(0.15)

    def play(self, name, cooldown=12, volume=1.0):
        if not self.ready or not self.enabled:
            return
        if self._cooldowns.get(name, 0) > 0:
            return
        sound = self.effects.get(name)
        if sound is None:
            return
        for channel in self._fx_channels:
            if not channel.get_busy():
                channel.set_volume(volume)
                channel.play(sound)
                self._cooldowns[name] = cooldown
                return

    def stop(self):
        if self.ready:
            pygame.mixer.stop()


def _sound_from_mono(samples):
    samples = np.clip(samples, -1.0, 1.0)
    stereo = np.column_stack([samples, samples])
    data = (stereo * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(data.copy())


def _env(n, attack=0.02, release=0.35):
    x = np.linspace(0.0, 1.0, n, dtype=np.float32)
    a = np.clip(x / max(0.001, attack), 0, 1)
    r = np.clip((1.0 - x) / max(0.001, release), 0, 1)
    return np.minimum(a, r) ** 1.6


def _lowpass(samples, amount=0.93):
    out = np.empty_like(samples, dtype=np.float32)
    acc = 0.0
    for i, value in enumerate(samples):
        acc = acc * amount + value * (1.0 - amount)
        out[i] = acc
    return out


def _smooth_noise(n, amount=0.96):
    noise = np.random.normal(0.0, 1.0, n).astype(np.float32)
    filtered = _lowpass(noise, amount)
    peak = max(0.001, float(np.max(np.abs(filtered))))
    return filtered / peak


def _make_season_ambience(kind, seconds=4.0, volume=0.26):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    breath = 0.55 + 0.45 * np.sin(math.tau * 0.12 * t + 0.8)
    wind = _smooth_noise(n, 0.992) * breath
    texture = _smooth_noise(n, 0.86) * 0.08
    wave = wind * 0.22 + texture

    if kind == "spring":
        wave *= 0.65
        for pos in (0.45, 1.7, 3.2):
            idx = int(pos * SAMPLE_RATE)
            span = min(n - idx, int(0.18 * SAMPLE_RATE))
            if span > 0:
                tt = np.arange(span, dtype=np.float32) / SAMPLE_RATE
                chirp = np.sin(math.tau * (880 + 220 * tt) * tt) * np.exp(-tt * 16)
                wave[idx:idx + span] += chirp * 0.045
    elif kind == "summer":
        water = _smooth_noise(n, 0.78) * 0.05
        wave = wave * 0.45 + water
        for pos in (0.8, 2.15, 3.35):
            idx = int(pos * SAMPLE_RATE)
            span = min(n - idx, int(0.12 * SAMPLE_RATE))
            if span > 0:
                tt = np.arange(span, dtype=np.float32) / SAMPLE_RATE
                drop = np.sin(math.tau * 560 * tt) * np.exp(-tt * 22)
                wave[idx:idx + span] += drop * 0.05
    elif kind == "late_summer":
        wave = _smooth_noise(n, 0.988) * 0.16 + _smooth_noise(n, 0.90) * 0.055
    elif kind == "autumn":
        rustle = _smooth_noise(n, 0.72) * (0.04 + 0.09 * (np.sin(math.tau * 0.5 * t) > 0.78))
        wave = wind * 0.12 + rustle
    elif kind == "winter":
        wave = _smooth_noise(n, 0.995) * 0.20 + _smooth_noise(n, 0.94) * 0.035
        wave += np.sin(math.tau * 82 * t) * 0.012

    fade = np.minimum(np.linspace(0, 1, n), np.linspace(1, 0, n))
    wave *= np.clip(fade * 6, 0, 1)
    return _sound_from_mono(wave * volume)


def _make_wind_reveal(seconds, volume=0.38):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    sweep = _smooth_noise(n, 0.965) * (t / max(0.001, seconds)) ** 0.7
    low = np.sin(math.tau * (110 + 55 * t) * t) * 0.08
    return _sound_from_mono((sweep * 0.35 + low) * _env(n, 0.04, 0.42) * volume)


def _make_natural_thunder(seconds, volume=0.6):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    crack = _smooth_noise(n, 0.55) * np.exp(-t * 26.0) * 0.55
    rumble = _smooth_noise(n, 0.988) * np.exp(-t * 2.4) * 0.36
    low = np.sin(math.tau * (58 - 18 * t) * t) * np.exp(-t * 2.2) * 0.28
    return _sound_from_mono((crack + rumble + low) * _env(n, 0.001, 0.62) * volume)


def _make_sword_whoosh(seconds, volume=0.42, ring=False):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    whoosh = _smooth_noise(n, 0.90) * np.sin(np.pi * np.clip(t / seconds, 0, 1)) ** 1.7
    metal = np.sin(math.tau * 930 * t) * np.exp(-t * 9.0) * 0.10
    if ring:
        metal += np.sin(math.tau * 620 * t) * np.exp(-t * 2.8) * 0.14
        metal += np.sin(math.tau * 1240 * t) * np.exp(-t * 4.0) * 0.05
    return _sound_from_mono((whoosh * 0.34 + metal) * _env(n, 0.004, 0.5) * volume)


def _make_ice_chime(seconds, volume=0.36):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    wave = np.zeros(n, dtype=np.float32)
    for f, amp in ((520, 0.26), (781, 0.18), (1042, 0.12), (1560, 0.06)):
        wave += np.sin(math.tau * f * t) * np.exp(-t * (4.0 + f / 950.0)) * amp
    wave += _smooth_noise(n, 0.72) * np.exp(-t * 18.0) * 0.08
    return _sound_from_mono(wave * _env(n, 0.004, 0.5) * volume)


def _make_soft_bell(seconds, base=220, volume=0.34):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    wave = np.sin(math.tau * base * t) * np.exp(-t * 1.45) * 0.72
    wave += np.sin(math.tau * base * 2.01 * t) * np.exp(-t * 2.4) * 0.18
    wave += _smooth_noise(n, 0.96) * np.exp(-t * 4.0) * 0.035
    return _sound_from_mono(wave * _env(n, 0.01, 0.9) * volume)


def _make_fire_whoosh(seconds, volume=0.4):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    flame = _smooth_noise(n, 0.82) * np.exp(-t * 2.7)
    low = np.sin(math.tau * 92 * t) * np.exp(-t * 4.0) * 0.16
    return _sound_from_mono((flame * 0.32 + low) * _env(n, 0.004, 0.38) * volume)


def _make_soft_impact(seconds, volume=0.56):
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    boom = np.sin(math.tau * (74 - 24 * t) * t) * np.exp(-t * 3.0) * 0.58
    body = _smooth_noise(n, 0.975) * np.exp(-t * 4.5) * 0.22
    return _sound_from_mono((boom + body) * _env(n, 0.003, 0.55) * volume)
