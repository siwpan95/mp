"""
兼容垫片（Deprecation shim）
═════════════════════════════
musicpipeline 自 2.0.0 起由单文件模块 `orc` 重构为包 `musicpipeline`。
为兼容历史 `import orc` 用法，本模块将 `musicpipeline` 的全部公开接口重新导出，
并在导入时给出迁移提示。

请在方便时迁移到新接口：
    from musicpipeline import generate_music, gui_mode
    # 或
    import musicpipeline as mp

本垫片为纯新增、非破坏性，将在未来主版本中移除。
"""

import warnings

import musicpipeline as _mp

warnings.warn(
    "模块 `orc` 已在 2.0.0 重命名为 `musicpipeline`，本垫片仅为向后兼容而保留，"
    "将在未来主版本移除。请改用 `import musicpipeline`。",
    DeprecationWarning,
    stacklevel=2,
)

# ── 透明转发 musicpipeline 的公开接口 ──
generate_music = _mp.generate_music
gui_mode = _mp.gui_mode
MusicVisualizerApp = _mp.MusicVisualizerApp

NOTE_NAMES = _mp.NOTE_NAMES
SCALES = _mp.SCALES
CHORD_PROGRESSIONS = _mp.CHORD_PROGRESSIONS
TIMBRES = _mp.TIMBRES

note_freq = _mp.note_freq
build_scale_notes = _mp.build_scale_notes
render_note = _mp.render_note
mix_tracks = _mp.mix_tracks
samples_to_wav = _mp.samples_to_wav
apply_reverb = _mp.apply_reverb
low_pass_filter = _mp.low_pass_filter
adsr_envelope = _mp.adsr_envelope
generate_melody = _mp.generate_melody
generate_bass = _mp.generate_bass
generate_pad = _mp.generate_pad
generate_drum_track = _mp.generate_drum_track
sine_wave = _mp.sine_wave
square_wave = _mp.square_wave
sawtooth_wave = _mp.sawtooth_wave
triangle_wave = _mp.triangle_wave

compute_spectrum = _mp.compute_spectrum
goertzel = _mp.goertzel
VIZ_FREQS = _mp.VIZ_FREQS
VIZ_MODES = _mp.VIZ_MODES

__version__ = _mp.__version__
__all__ = list(_mp.__all__)
