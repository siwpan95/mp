"""
musicpipeline
═════════════
随机音乐生成器 + WMP 风格可视化，纯 Python 标准库实现。

顶层公开接口（向后兼容 orc.py 的常用导出）：
    from musicpipeline import generate_music, gui_mode, MusicVisualizerApp

- generate_music(...)        —— 生成随机音乐并写出 WAV（也可 return_samples=True 取采样）
- gui_mode()                 —— 启动 tkinter 图形界面（Windows）
- MusicVisualizerApp(root)    —— 可视化主窗口类（需 tkinter）

仅合成部分（core）在任何平台可用；GUI（visualizer）依赖 tkinter / winsound，
仅 Windows 可用，导入失败时本包仍可作为纯合成库使用。
"""

from .core import (
    generate_music,
    NOTE_NAMES, SCALES, CHORD_PROGRESSIONS, TIMBRES,
    note_freq, build_scale_notes,
    render_note, mix_tracks, samples_to_wav,
    apply_reverb, low_pass_filter, adsr_envelope,
    generate_melody, generate_bass, generate_pad, generate_drum_track,
    sine_wave, square_wave, sawtooth_wave, triangle_wave,
)
from .analysis import compute_spectrum, goertzel, VIZ_FREQS

# GUI 仅在 Windows / 有 tkinter 时可用；导入失败则降级为纯合成库
try:
    from .visualizer import MusicVisualizerApp, gui_mode, VIZ_MODES
except (ImportError, OSError):  # pragma: no cover - 非 Windows / 无显示环境
    MusicVisualizerApp = None
    gui_mode = None
    VIZ_MODES = []

__version__ = "2.0.0"

__all__ = [
    "generate_music", "gui_mode", "MusicVisualizerApp",
    "NOTE_NAMES", "SCALES", "CHORD_PROGRESSIONS", "TIMBRES",
    "note_freq", "build_scale_notes",
    "render_note", "mix_tracks", "samples_to_wav",
    "apply_reverb", "low_pass_filter", "adsr_envelope",
    "generate_melody", "generate_bass", "generate_pad", "generate_drum_track",
    "sine_wave", "square_wave", "sawtooth_wave", "triangle_wave",
    "compute_spectrum", "goertzel", "VIZ_FREQS", "VIZ_MODES",
    "__version__",
]
