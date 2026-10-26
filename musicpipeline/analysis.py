"""
频谱分析模块
─────────────
使用 Goertzel 算法在若干锚点频率上计算每帧能量，
供可视化模块绘制频谱条形 / 圆形频谱 / 山脉等效果。
纯标准库实现（仅依赖 math）。
"""

import math

# 可视化使用的锚点频率（Hz）
VIZ_FREQS = [50, 100, 200, 400, 800, 1600, 3200, 6000]


def goertzel(samples, target_freq, sample_rate):
    """Goertzel 算法：计算一段采样在某目标频率上的能量（功率）。"""
    n = len(samples)
    k = int(0.5 + n * target_freq / sample_rate)
    omega = 2.0 * math.pi * k / n
    coeff = 2.0 * math.cos(omega)
    s_prev = 0.0
    s_prev2 = 0.0
    for s in samples:
        s_curr = s + coeff * s_prev - s_prev2
        s_prev2 = s_prev
        s_prev = s_curr
    power = s_prev2 * s_prev2 + s_prev * s_prev - coeff * s_prev * s_prev2
    return power


def compute_spectrum(samples, sample_rate, window_size=2048, hop_size=1024):
    """按滑动窗口逐帧计算各锚点频率能量，返回帧列表 [[freq_energy, ...], ...]。"""
    frames = []
    for start in range(0, len(samples) - window_size, hop_size):
        window = samples[start:start + window_size]
        energies = [goertzel(window, f, sample_rate) for f in VIZ_FREQS]
        frames.append(energies)
    return frames
