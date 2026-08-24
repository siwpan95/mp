"""
随机音乐生成器 + 多乐器模拟 + 鼓与和弦铺底 + WMP 风格可视化 + 时长控制
纯 Python 标准库实现
"""

import wave
import struct
import math
import random
import os
import sys
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import winsound  # Windows 播放


# ──────────────────────────────────────────
# 音符频率表 (Hz)  A4 = 440 Hz
# ──────────────────────────────────────────
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def note_freq(name: str, octave: int) -> float:
    semitone = NOTE_NAMES.index(name)
    midi = (octave + 1) * 12 + semitone
    return 440.0 * (2 ** ((midi - 69) / 12))


def build_scale_notes(root_note: str, root_octave: int, scale_intervals: list[int]) -> list[float]:
    """根据根音、音阶间隔构建音阶音符频率列表（2个八度）"""
    base_freq = note_freq(root_note, root_octave)
    result = []
    # 生成2个八度的音阶
    for octave in range(2):
        for interval in scale_intervals:
            semitones = interval + (octave * 12)
            freq = base_freq * (2 ** (semitones / 12))
            result.append(freq)
    return result


SCALES = {
    "大调":     [0, 2, 4, 5, 7, 9, 11],
    "自然小调": [0, 2, 3, 5, 7, 8, 10],
    "五声大调": [0, 2, 4, 7, 9],
    "五声小调": [0, 3, 5, 7, 10],
    "布鲁斯":   [0, 3, 5, 6, 7, 10],
    "多利安":   [0, 2, 3, 5, 7, 9, 10],
}

CHORD_PROGRESSIONS = [
    [1, 5, 6, 4],
    [1, 4, 5, 1],
    [1, 6, 4, 5],
    [2, 5, 1, 6],
    [1, 3, 4, 5],
    [6, 4, 1, 5],
]

# ──────────────────────────────────────────
# 基本波形
# ──────────────────────────────────────────
def sine_wave(freq: float, t: float) -> float:
    return math.sin(2 * math.pi * freq * t)

def square_wave(freq: float, t: float, duty=0.5) -> float:
    phase = (freq * t) % 1.0
    return 1.0 if phase < duty else -1.0

def sawtooth_wave(freq: float, t: float) -> float:
    return 2.0 * ((freq * t) % 1.0) - 1.0

def triangle_wave(freq: float, t: float) -> float:
    p = (freq * t) % 1.0
    return 4.0 * p - 1.0 if p < 0.5 else 3.0 - 4.0 * p

# ──────────────────────────────────────────
# 乐器模拟器（全部使用音符内时间 note_t）
# ──────────────────────────────────────────
def piano_wave(freq, t, duration):
    impulse = math.exp(-t * 80) * 0.2 if t < 0.05 else 0
    harmonics = (
        sine_wave(freq, t) * 1.0
        + sine_wave(freq * 2, t) * 0.5
        + sine_wave(freq * 3, t) * 0.25
        + sine_wave(freq * 4, t) * 0.12
        + sine_wave(freq * 5, t) * 0.06
        + sine_wave(freq * 6, t) * 0.03
    )
    decay = math.exp(-t * 5.0 / max(duration, 0.01)) * (0.5 + 0.5 * math.exp(-t * 2.0))
    return (harmonics * decay) + impulse

def epiano_wave(freq, t, duration):
    harmonics = (
        sine_wave(freq, t) * 1.0
        + sine_wave(freq * 2, t) * 0.4
        + sine_wave(freq * 3, t) * 0.2
        + sine_wave(freq * 4, t) * 0.08
    )
    vibrato = 1 + 0.002 * sine_wave(5.0, t)
    decay = math.exp(-t * 3.0 / max(duration, 0.01))
    return harmonics * decay * vibrato

def organ_wave(freq, t, duration=None):
    return (
        sine_wave(freq, t) * 0.5
        + sine_wave(freq * 2, t) * 0.3
        + sine_wave(freq * 3, t) * 0.15
        + sine_wave(freq * 4, t) * 0.05
    )

def violin_wave(freq, t, duration):
    mod = 1 + 0.002 * sine_wave(5.5, t)
    f_mod = freq * mod
    harmonics = (
        sine_wave(f_mod, t) * 1.0
        + sine_wave(f_mod * 2, t) * 0.6
        + sine_wave(f_mod * 3, t) * 0.35
        + sine_wave(f_mod * 4, t) * 0.15
        + sine_wave(f_mod * 5, t) * 0.05
    )
    attack = min(1.0, t / 0.1) if t < 0.1 else 1.0
    return harmonics * attack * 0.8

def cello_wave(freq, t, duration):
    f0 = freq / 2
    mod = 1 + 0.003 * sine_wave(4.5, t)
    f_mod = f0 * mod
    harmonics = (
        sine_wave(f_mod, t) * 1.0
        + sine_wave(f_mod * 2, t) * 0.7
        + sine_wave(f_mod * 3, t) * 0.4
        + sine_wave(f_mod * 4, t) * 0.2
        + sine_wave(f_mod * 5, t) * 0.08
    )
    attack = min(1.0, t / 0.15)
    return harmonics * attack * 0.75

def strings_wave(freq, t, duration):
    detune = [0.0, 0.001, -0.0015, 0.0005]
    v = 0
    for dt in detune:
        v += sine_wave(freq * (1 + dt), t) * 0.5
    v += sine_wave(freq * 2, t) * 0.3
    v += sine_wave(freq * 3, t) * 0.1
    attack = min(1.0, t / 0.12)
    return v * attack * 0.7

def flute_wave(freq, t, duration):
    v = sine_wave(freq, t) * 1.0 + sine_wave(freq * 2, t) * 0.1
    attack = min(1.0, t / 0.05)
    return v * attack * 0.9

def clarinet_wave(freq, t, duration):
    v = (
        sine_wave(freq, t) * 1.0
        + sine_wave(freq * 3, t) * 0.5
        + sine_wave(freq * 5, t) * 0.2
    )
    attack = min(1.0, t / 0.08)
    return v * attack * 0.85

def trumpet_wave(freq, t, duration):
    harmonics = (
        sine_wave(freq, t) * 1.0
        + sine_wave(freq * 2, t) * 0.6
        + sine_wave(freq * 3, t) * 0.4
        + sine_wave(freq * 4, t) * 0.25
        + sine_wave(freq * 5, t) * 0.15
    )
    attack = min(1.0, t / 0.03)
    vib = 1 + 0.003 * sine_wave(6.0, t)
    return harmonics * attack * vib * 0.75

def guitar_wave(freq, t, duration):
    harmonics = (
        sine_wave(freq, t) * 1.0
        + sine_wave(freq * 2, t) * 0.5
        + sine_wave(freq * 3, t) * 0.2
    )
    decay = math.exp(-t * 8.0 / max(duration, 0.01))
    return harmonics * decay * 0.9

def eguitar_wave(freq, t, duration):
    raw = sine_wave(freq, t) + sine_wave(freq * 2, t) * 0.5
    distorted = math.tanh(raw * 2.5)
    decay = math.exp(-t * 4.0 / max(duration, 0.01))
    return distorted * decay * 0.8

def choir_wave(freq, t, duration):
    detune = [0.0, 0.0008, -0.001, 0.0005, -0.0005]
    v = 0
    for dt in detune:
        v += sine_wave(freq * (1 + dt), t)
    tremolo = 1 + 0.1 * sine_wave(0.5, t)
    attack = min(1.0, t / 0.2)
    return v * attack * tremolo * 0.3

def marimba_wave(freq, t, duration):
    v = sine_wave(freq, t) * 1.0 + sine_wave(freq * 2, t) * 0.8
    decay = math.exp(-t * 12.0 / max(duration, 0.01))
    return v * decay * 0.7

def bass_wave(freq, t, duration):
    v = sine_wave(freq, t) + sine_wave(freq * 2, t) * 0.2
    return v * 0.9

# 新增：鼓合成
def kick_drum(t, sample_rate):
    freq = 150 * math.exp(-t * 30)
    amp = math.exp(-t * 20) * 1.2
    return sine_wave(freq, t) * amp

def snare_drum(t, sample_rate):
    noise = random.uniform(-1, 1)
    tone = sine_wave(200, t) * 0.6
    amp = math.exp(-t * 10) * 0.8
    return (noise * 0.6 + tone) * amp

def hihat(t, sample_rate):
    noise = random.uniform(-1, 1) * 0.4
    amp = math.exp(-t * 80) * 1.0
    return noise * amp

def render_drum(note_type, duration, sample_rate):
    n_samples = int(duration * sample_rate)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        if note_type == "K":
            samples.append(kick_drum(t, sample_rate))
        elif note_type == "S":
            samples.append(snare_drum(t, sample_rate))
        elif note_type == "H":
            samples.append(hihat(t, sample_rate))
        else:
            samples.append(0.0)
    return samples

# 新增：鼓节奏型库
DRUM_PATTERNS = [
    # 每个子列表代表一个八分音符步进（0.5拍），K=底鼓 S=军鼓 H=踩镲 . 休止
    "K . H . S . H . K . H K S H H .".split(),
    "K . H . S H H . K . H . S H H K".split(),
    "K . H . S . H . K K H . S H H .".split(),
    "K H H S H H K H H . H S H H K".split(),
]

# ──────────────────────────────────────────
# 乐器列表
# ──────────────────────────────────────────
TIMBRES = [
    "原声钢琴", "电钢琴", "管风琴",
    "小提琴", "大提琴", "弦乐合奏",
    "长笛", "单簧管", "小号",
    "原声吉他", "电吉他", "合唱",
    "马林巴", "贝斯",
    "正弦波", "方波", "三角波", "锯齿波"
]

INSTRUMENT_WITH_INTERNAL_ENVELOPE = {
    "原声钢琴", "电钢琴", "原声吉他", "电吉他",
    "马林巴", "贝斯",
}

# ──────────────────────────────────────────
# ADSR 包络
# ──────────────────────────────────────────
def adsr_envelope(note_t: float, duration: float,
                  attack=0.02, decay=0.05, sustain=0.7, release=0.08) -> float:
    if duration <= 0:
        return 0.0
    effective_attack = min(attack, duration * 0.3)
    effective_decay = min(decay, duration * 0.2)
    effective_release = min(release, duration * 0.4)

    if note_t < effective_attack:
        return note_t / max(effective_attack, 0.001)
    elif note_t < effective_attack + effective_decay:
        return 1.0 - (1.0 - sustain) * (note_t - effective_attack) / max(effective_decay, 0.001)
    elif note_t < duration - effective_release:
        return sustain
    elif note_t < duration:
        return sustain * (1.0 - (note_t - (duration - effective_release)) / max(effective_release, 0.001))
    else:
        return 0.0

# ──────────────────────────────────────────
# 音符渲染（乐器）
# ──────────────────────────────────────────
def render_note(freq: float, duration: float, sample_rate: int,
                timbre: str, volume: float = 0.8) -> list[float]:
    n_samples = int(duration * sample_rate)
    samples = []
    use_internal_env = timbre in INSTRUMENT_WITH_INTERNAL_ENVELOPE

    for i in range(n_samples):
        note_t = i / sample_rate
        if freq <= 0:
            samples.append(0.0)
            continue

        if timbre == "原声钢琴":
            raw = piano_wave(freq, note_t, duration)
        elif timbre == "电钢琴":
            raw = epiano_wave(freq, note_t, duration)
        elif timbre == "管风琴":
            raw = organ_wave(freq, note_t)
        elif timbre == "小提琴":
            raw = violin_wave(freq, note_t, duration)
        elif timbre == "大提琴":
            raw = cello_wave(freq, note_t, duration)
        elif timbre == "弦乐合奏":
            raw = strings_wave(freq, note_t, duration)
        elif timbre == "长笛":
            raw = flute_wave(freq, note_t, duration)
        elif timbre == "单簧管":
            raw = clarinet_wave(freq, note_t, duration)
        elif timbre == "小号":
            raw = trumpet_wave(freq, note_t, duration)
        elif timbre == "原声吉他":
            raw = guitar_wave(freq, note_t, duration)
        elif timbre == "电吉他":
            raw = eguitar_wave(freq, note_t, duration)
        elif timbre == "合唱":
            raw = choir_wave(freq, note_t, duration)
        elif timbre == "马林巴":
            raw = marimba_wave(freq, note_t, duration)
        elif timbre == "贝斯":
            raw = bass_wave(freq, note_t, duration)
        elif timbre == "方波":
            raw = square_wave(freq, note_t, duty=random.uniform(0.4, 0.6))
        elif timbre == "三角波":
            raw = triangle_wave(freq, note_t)
        elif timbre == "锯齿波":
            raw = sawtooth_wave(freq, note_t)
        else:  # "正弦波"
            raw = sine_wave(freq, note_t)

        if use_internal_env:
            env = 1.0
        else:
            env = adsr_envelope(note_t, duration)
        samples.append(raw * env * volume)
    return samples


# ──────────────────────────────────────────
# 混响 & 滤波
# ──────────────────────────────────────────
def apply_reverb(samples: list, sample_rate: int, delay_ms=80, decay=0.3, mix=0.25) -> list:
    delay_samples = int(delay_ms * sample_rate / 1000)
    out = list(samples)
    for i in range(delay_samples, len(out)):
        out[i] += out[i - delay_samples] * decay * mix
    return out

def low_pass_filter(samples: list, cutoff_ratio: float = 0.3) -> list:
    alpha = 1.0 - math.exp(-2 * math.pi * cutoff_ratio)
    out = []
    prev = 0.0
    for s in samples:
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


# ──────────────────────────────────────────
# 旋律生成（丰富节奏型库）
# ──────────────────────────────────────────
def generate_melody(scale_notes: list, n_bars: int, bpm: int, time_sig=4) -> list:
    beat_dur = 60.0 / bpm
    rhythms = [
        [1, 1, 1, 1],
        [0.5, 0.5, 1, 1, 1],
        [2, 1, 1],
        [0.5, 0.5, 0.5, 0.5, 1, 1],
        [1.5, 0.5, 1, 1],          # 附点四分
        [0.25, 0.25, 0.5, 1, 1, 1],
        # 新增切分/三连音
        [0.5, 1, 0.5, 1, 1],       # 切分
        [1, 0.5, 0.5, 2],          # 反拍强调
        [2/3, 2/3, 2/3, 2],        # 三连音
        [1.5, 0.5, 0.5, 0.5, 1],   # 附点 + 八分
        [0.25, 0.25, 0.25, 0.25, 1, 1, 1],  # 四个十六分音符
    ]
    melody = []
    prev_idx = len(scale_notes) // 2
    for _ in range(n_bars):
        rhythm = random.choice(rhythms)
        total = sum(rhythm)
        rhythm = [r * time_sig / total for r in rhythm]
        for dur_beats in rhythm:
            dur_sec = dur_beats * beat_dur
            step_type = random.random()
            if step_type < 0.6:
                delta = random.choice([-2, -1, -1, 0, 1, 1, 2])
            elif step_type < 0.85:
                delta = random.choice([-4, -3, 3, 4])
            else:
                delta = random.choice([-7, -5, 5, 7])
            prev_idx = max(0, min(len(scale_notes) - 1, prev_idx + delta))
            if random.random() < 0.10:
                melody.append((0, dur_sec))
            else:
                melody.append((scale_notes[prev_idx], dur_sec))
    return melody

# 低音生成（丰富律动库）
def generate_bass(scale_notes: list, chord_prog: list, n_bars: int, bpm: int, time_sig=4) -> list:
    beat_dur = 60.0 / bpm
    target_duration = n_bars * time_sig * beat_dur
    bass_notes = scale_notes[:len(scale_notes) // 2]
    
    grooves = [
        [(1, beat_dur), (5, beat_dur*0.5), (1, beat_dur*0.5), (5, beat_dur), (1, beat_dur)],
        [(1, beat_dur), (5, beat_dur*0.5), (1, beat_dur*0.5), (5, beat_dur*0.5), (1, beat_dur*0.5)],
        [(1, beat_dur*1.5), (5, beat_dur*0.5), (1, beat_dur), (5, beat_dur)],
        [(1, beat_dur*1.5), (1, beat_dur*0.5), (5, beat_dur), (1, beat_dur)],
        [(1, beat_dur), (0, beat_dur*0.5), (5, beat_dur*0.5), (1, beat_dur), (5, beat_dur)],
    ]
    
    bass = []
    total_dur = 0.0
    while total_dur < target_duration:
        for chord_idx in chord_prog:
            if total_dur >= target_duration:
                break
            root_idx = min(chord_idx - 1, len(bass_notes) - 1)
            fifth_idx = min(root_idx + 4, len(bass_notes) - 1)
            
            groove = random.choice(grooves)
            for interval, dur in groove:
                if total_dur >= target_duration:
                    break
                dur = min(dur, target_duration - total_dur)
                if interval == 0:
                    bass.append((0, dur))
                elif interval == 1:
                    bass.append((bass_notes[root_idx], dur))
                else:
                    bass.append((bass_notes[fifth_idx], dur))
                total_dur += dur
    return bass

# 新增：和弦铺底生成
def generate_pad(scale_notes, chord_prog, n_bars, bpm, time_sig=4):
    beat_dur = 60.0 / bpm
    bars_per_chord = max(1, n_bars // len(chord_prog))
    pad_seq = []
    for chord_idx in chord_prog:
        root = min(chord_idx - 1, len(scale_notes) - 1)
        third = min(root + 2, len(scale_notes) - 1)
        fifth = min(root + 4, len(scale_notes) - 1)
        for _ in range(bars_per_chord):
            # 每小节第一拍奏和弦音，持续两拍，后面休止
            dur = beat_dur * 2
            for note_idx in [root, third, fifth]:
                pad_seq.append((scale_notes[note_idx], dur))
            pad_seq.append((0, beat_dur * 2))  # 休止两拍
    return pad_seq

# 新增：鼓轨生成
def generate_drum_track(bpm, n_bars, sample_rate, time_sig=4):
    beat_dur = 60.0 / bpm
    pattern = random.choice(DRUM_PATTERNS)
    track = []
    for bar in range(n_bars):
        for step in pattern:
            dur = beat_dur * 0.5
            track.extend(render_drum(step, dur, sample_rate))
    return track


# ──────────────────────────────────────────
# 混合 & WAV 写入
# ──────────────────────────────────────────
def mix_tracks(tracks: list, sample_rate: int) -> list:
    max_len = max(len(t) for t in tracks)
    mixed = [0.0] * max_len
    for track in tracks:
        for i, s in enumerate(track):
            mixed[i] += s
    peak = max(abs(s) for s in mixed) or 1.0
    if peak > 0.9:
        factor = 0.9 / peak
        mixed = [s * factor for s in mixed]
    return mixed

def samples_to_wav(samples: list, sample_rate: int, filepath: str,
                   n_channels=1, bit_depth=16):
    max_val = (2 ** (bit_depth - 1)) - 1
    fmt = "<h" if bit_depth == 16 else "<i"
    with wave.open(filepath, "w") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(bit_depth // 8)
        wf.setframerate(sample_rate)
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            wf.writeframes(struct.pack(fmt, int(clamped * max_val)))
    print(f"  ✓ WAV 文件已保存: {filepath}")


# ──────────────────────────────────────────
# 音频生成（乐器选择功能）
# ──────────────────────────────────────────

# 可选乐器列表
AVAILABLE_INSTRUMENTS = ["旋律", "低音", "鼓", "Pad"]

def generate_music(output_path: str = None,
                   bpm: int = None,
                   scale_name: str = None,
                   root_note: str = None,
                   root_octave: int = None,
                   melody_timbre: str = None,
                   bass_timbre: str = None,
                   n_bars: int = None,
                   instruments: list[str] = None,  # 乐器选择列表: ["旋律", "低音", "鼓", "Pad"]
                   add_reverb: bool = None,
                   sample_rate: int = 44100,
                   return_samples: bool = False):
    bpm = bpm or random.randint(70, 160)
    scale_name = scale_name or random.choice(list(SCALES.keys()))
    root_note = root_note or random.choice(["C", "D", "E", "F", "G", "A", "B"])
    root_octave = root_octave if root_octave is not None else random.choice([4, 5])
    melody_timbre = melody_timbre or random.choice(TIMBRES)
    bass_timbre = bass_timbre or random.choice(["贝斯", "大提琴", "正弦波"])
    n_bars = n_bars if n_bars is not None else random.randint(8, 24)
    # 默认全部开启乐器
    if instruments is None:
        instruments = ["旋律", "低音", "鼓", "Pad"]
    add_reverb = add_reverb if add_reverb is not None else random.choice([True, False])

    chord_prog = random.choice(CHORD_PROGRESSIONS)
    time_sig = 4

    params = {
        "bpm": bpm,
        "调式": scale_name,
        "主音": f"{root_note}{root_octave}",
        "旋律音色": melody_timbre,
        "乐器": instruments,
        "小节数": n_bars,
        "混响": add_reverb,
        "和弦进行": chord_prog,
    }

    print("\n🎵 随机音乐生成器")
    print("=" * 40)
    for k, v in params.items():
        print(f"  {k}: {v}")
    print("=" * 40)

    scale_intervals = SCALES[scale_name]
    scale_notes = build_scale_notes(root_note, root_octave, scale_intervals)

    tracks = []

    if "旋律" in instruments:
        print("  生成旋律…")
        melody_seq = generate_melody(scale_notes, n_bars, bpm, time_sig)
        melody_track = []
        for freq, dur in melody_seq:
            melody_track.extend(render_note(freq, dur, sample_rate, melody_timbre, volume=0.75))
        tracks.append(melody_track)

    if "低音" in instruments:
        print("  生成低音…")
        bass_seq = generate_bass(scale_notes, chord_prog, n_bars, bpm, time_sig)
        bass_track = []
        for freq, dur in bass_seq:
            bass_track.extend(render_note(freq / 2, dur, sample_rate, bass_timbre, volume=0.55))
        tracks.append(bass_track)

    if "Pad" in instruments:
        print("  生成和弦铺底…")
        pad_seq = generate_pad(scale_notes, chord_prog, n_bars, bpm, time_sig)
        pad_track = []
        for freq, dur in pad_seq:
            pad_track.extend(render_note(freq, dur, sample_rate, "弦乐合奏", volume=0.35))
        tracks.append(pad_track)

    if "鼓" in instruments:
        print("  生成鼓轨…")
        drum_track = generate_drum_track(bpm, n_bars, sample_rate, time_sig)
        tracks.append(drum_track)

    print("  混合音轨…")
    mixed = mix_tracks(tracks, sample_rate)

    if add_reverb:
        print("  应用混响…")
        mixed = apply_reverb(mixed, sample_rate,
                             delay_ms=random.uniform(60, 120),
                             decay=random.uniform(0.2, 0.45),
                             mix=0.3)

    if melody_timbre in ("方波", "锯齿波", "电吉他"):
        mixed = low_pass_filter(mixed, cutoff_ratio=0.3)

    peak = max(abs(s) for s in mixed) or 1.0
    mixed = [s * 0.88 / peak for s in mixed]

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, f"music_{ts}.wav")

    samples_to_wav(mixed, sample_rate, output_path)
    print(f"\n🎼 完成！时长约 {len(mixed) / sample_rate:.1f} 秒")

    if return_samples:
        return output_path, params, mixed, sample_rate
    return output_path, params


# ══════════════════════════════════════════
# 可视化部分（7种效果，省略以缩短篇幅，使用之前完整版）
# ══════════════════════════════════════════
VIZ_FREQS = [50, 100, 200, 400, 800, 1600, 3200, 6000]

def goertzel(samples, target_freq, sample_rate):
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
    frames = []
    for start in range(0, len(samples) - window_size, hop_size):
        window = samples[start:start + window_size]
        energies = [goertzel(window, f, sample_rate) for f in VIZ_FREQS]
        frames.append(energies)
    return frames

VIZ_MODES = [
    "频谱条形", "滚动波形", "频谱+波形", "圆形频谱",
    "声波涟漪", "粒子舞蹈", "频谱山脉"
]

class MusicVisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("随机音乐生成器 - WMP 风格可视化")
        self.root.geometry("900x500")
        self.root.resizable(False, False)
        self.samples = []
        self.sample_rate = 44100
        self.spectrum_frames = []
        self.duration = 0.0
        self.playing = False
        self.start_time = 0.0
        self.after_id = None
        self.wav_path = None
        self.params = {}
        self.viz_mode = 0
        self.particles = []
        self.setup_ui()

    def setup_ui(self):
        # 顶部控制栏
        top_frame = tk.Frame(self.root, bg="#1a1a2e", height=50)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        # 主按钮区
        btn_gen = tk.Button(top_frame, text="🎲 生成", command=self.on_generate,
                            bg="#e94560", fg="white", font=("微软雅黑", 12, "bold"),
                            padx=20, pady=8, relief=tk.FLAT, cursor="hand2")
        btn_gen.pack(side=tk.LEFT, padx=15, pady=10)

        self.btn_play = tk.Button(top_frame, text="▶ 播放", command=self.on_play,
                                  bg="#16c79a", fg="white", font=("微软雅黑", 11),
                                  padx=15, pady=8, relief=tk.FLAT, cursor="hand2")
        self.btn_play.pack(side=tk.LEFT, padx=5, pady=10)

        btn_stop = tk.Button(top_frame, text="⏹ 停止", command=self.on_stop,
                             bg="#f39c12", fg="white", font=("微软雅黑", 11),
                             padx=15, pady=8, relief=tk.FLAT, cursor="hand2")
        btn_stop.pack(side=tk.LEFT, padx=5, pady=10)

        btn_viz = tk.Button(top_frame, text="🔄 可视化", command=self.toggle_viz_mode,
                            bg="#5f6caf", fg="white", font=("微软雅黑", 11),
                            padx=15, pady=8, relief=tk.FLAT, cursor="hand2")
        btn_viz.pack(side=tk.LEFT, padx=5, pady=10)

        self.lbl_status = tk.Label(top_frame, text="准备就绪", fg="#a0a0a0", bg="#1a1a2e",
                                    font=("微软雅黑", 11))
        self.lbl_status.pack(side=tk.RIGHT, padx=20, pady=10)

        # 参数设置面板
        param_frame = tk.Frame(self.root, bg="#16213e", height=120)
        param_frame.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))

        # 第一行：基础参数
        row1 = tk.Frame(param_frame, bg="#16213e")
        row1.pack(side=tk.TOP, fill=tk.X, pady=8, padx=15)

        # BPM
        tk.Label(row1, text="速度:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.random_bpm_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row1, text="随机", variable=self.random_bpm_var, bg="#16213e", fg="#fff",
                      selectcolor="#16c79a", indicatoron=False, padx=6, pady=1,
                      command=self._on_random_bpm_changed).pack(side=tk.LEFT, padx=3)
        self.bpm_var = tk.IntVar(value=120)
        self.bpm_scale = tk.Scale(row1, from_=60, to=180, orient=tk.HORIZONTAL,
                                   variable=self.bpm_var, length=120, bg="#16213e", fg="#fff",
                                   troughcolor="#4a4a4a", highlightthickness=0, showvalue=False)
        self.bpm_scale.pack(side=tk.LEFT, padx=5)
        self.bpm_label = tk.Label(row1, text="120", fg="#16c79a", bg="#16213e", font=("Consolas", 10), width=5)
        self.bpm_label.pack(side=tk.LEFT)

        # 调式
        tk.Label(row1, text="调式:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.random_scale_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row1, text="随机", variable=self.random_scale_var, bg="#16213e", fg="#fff",
                      selectcolor="#16c79a", indicatoron=False, padx=6, pady=1,
                      command=self._on_random_scale_changed).pack(side=tk.LEFT, padx=3)
        self.scale_var = tk.StringVar(value="大调")
        self.scale_menu = ttk.Combobox(row1, textvariable=self.scale_var, values=list(SCALES.keys()),
                                        state="readonly", width=10)
        self.scale_menu.pack(side=tk.LEFT, padx=5)

        # 根音
        tk.Label(row1, text="根音:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.random_root_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row1, text="随机", variable=self.random_root_var, bg="#16213e", fg="#fff",
                      selectcolor="#16c79a", indicatoron=False, padx=6, pady=1,
                      command=self._on_random_root_changed).pack(side=tk.LEFT, padx=3)
        self.root_var = tk.StringVar(value="C")
        self.root_menu = ttk.Combobox(row1, textvariable=self.root_var,
                                       values=["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
                                       state="readonly", width=5)
        self.root_menu.pack(side=tk.LEFT, padx=5)

        # 八度
        tk.Label(row1, text="八度:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.octave_var = tk.IntVar(value=4)
        for o in [3, 4, 5]:
            tk.Radiobutton(row1, text=str(o), variable=self.octave_var, value=o,
                          bg="#16213e", fg="#fff", selectcolor="#16c79a",
                          indicatoron=False, padx=8, pady=1).pack(side=tk.LEFT, padx=2)

        # 第二行：音色与乐器
        row2 = tk.Frame(param_frame, bg="#16213e")
        row2.pack(side=tk.TOP, fill=tk.X, pady=5, padx=15)

        # 旋律音色
        tk.Label(row2, text="旋律音色:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.random_melody_timbre_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row2, text="随机", variable=self.random_melody_timbre_var, bg="#16213e", fg="#fff",
                      selectcolor="#16c79a", indicatoron=False, padx=6, pady=1,
                      command=self._on_random_melody_changed).pack(side=tk.LEFT, padx=3)
        self.melody_timbre_var = tk.StringVar(value="原声钢琴")
        self.melody_timbre_menu = ttk.Combobox(row2, textvariable=self.melody_timbre_var,
                                                values=TIMBRES, state="readonly", width=12)
        self.melody_timbre_menu.pack(side=tk.LEFT, padx=5)

        # 低音音色
        tk.Label(row2, text="低音音色:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.random_bass_timbre_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row2, text="随机", variable=self.random_bass_timbre_var, bg="#16213e", fg="#fff",
                      selectcolor="#16c79a", indicatoron=False, padx=6, pady=1,
                      command=self._on_random_bass_changed).pack(side=tk.LEFT, padx=3)
        self.bass_timbre_var = tk.StringVar(value="贝斯")
        self.bass_timbre_menu = ttk.Combobox(row2, textvariable=self.bass_timbre_var,
                                             values=["贝斯", "大提琴", "正弦波"], state="readonly", width=10)
        self.bass_timbre_menu.pack(side=tk.LEFT, padx=5)

        # 小节数
        tk.Label(row2, text="小节数:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(20, 0))
        self.random_bars_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row2, text="随机", variable=self.random_bars_var, bg="#16213e", fg="#fff",
                      selectcolor="#16c79a", indicatoron=False, padx=6, pady=1,
                      command=self._on_random_bars_changed).pack(side=tk.LEFT, padx=3)
        self.bars_var = tk.IntVar(value=16)
        self.bars_scale = tk.Scale(row2, from_=4, to=32, orient=tk.HORIZONTAL,
                                    variable=self.bars_var, length=100, bg="#16213e", fg="#fff",
                                    troughcolor="#4a4a4a", highlightthickness=0, showvalue=False)
        self.bars_scale.pack(side=tk.LEFT, padx=5)
        self.bars_label = tk.Label(row2, text="16", fg="#16c79a", bg="#16213e", font=("Consolas", 10), width=5)
        self.bars_label.pack(side=tk.LEFT)

        # 第三行：乐器选择与特效
        row3 = tk.Frame(param_frame, bg="#16213e")
        row3.pack(side=tk.TOP, fill=tk.X, pady=5, padx=15)

        # 乐器选择（按钮式复选框，适合深色主题）
        tk.Label(row3, text="乐器:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.melody_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row3, text="旋律", variable=self.melody_var,
                      bg="#16213e", fg="#e94560", selectcolor="#e94560",
                      indicatoron=False, padx=8, pady=2).pack(side=tk.LEFT, padx=3)
        self.bass_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row3, text="低音", variable=self.bass_var,
                      bg="#16213e", fg="#f39c12", selectcolor="#f39c12",
                      indicatoron=False, padx=8, pady=2).pack(side=tk.LEFT, padx=3)
        self.drums_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row3, text="鼓", variable=self.drums_var,
                      bg="#16213e", fg="#16c79a", selectcolor="#16c79a",
                      indicatoron=False, padx=8, pady=2).pack(side=tk.LEFT, padx=3)
        self.pad_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row3, text="Pad", variable=self.pad_var,
                      bg="#16213e", fg="#5f6caf", selectcolor="#5f6caf",
                      indicatoron=False, padx=8, pady=2).pack(side=tk.LEFT, padx=3)

        # 混响开关
        tk.Label(row3, text="特效:", fg="#eee", bg="#16213e", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(30, 0))
        self.reverb_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row3, text="混响", variable=self.reverb_var,
                      bg="#16213e", fg="#9b59b6", selectcolor="#9b59b6",
                      indicatoron=False, padx=8, pady=2).pack(side=tk.LEFT, padx=3)

        # 绑定滑块事件更新显示
        self.bpm_scale.config(command=lambda v: self.bpm_label.config(text=str(int(float(v)))))
        self.bars_scale.config(command=lambda v: self.bars_label.config(text=str(int(float(v)))))

        # 可视化画布
        self.canvas = tk.Canvas(self.root, bg="#0f0f23", height=380)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 底部信息栏
        info_frame = tk.Frame(self.root, bg="#1a1a2e", height=35)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_info = tk.Label(info_frame, text="", fg="#888", bg="#1a1a2e",
                                  font=("Consolas", 10), justify=tk.LEFT, anchor="w")
        self.lbl_info.pack(pady=5, padx=15, fill=tk.X)

        self.canvas.create_text(480, 190, text="点击「生成」开始", fill="#333", font=("微软雅黑", 24))

    # 随机切换回调
    def _on_random_bpm_changed(self):
        state = "normal" if not self.random_bpm_var.get() else "disabled"
        self.bpm_scale.config(state=state)
        self.bpm_label.config(fg="#555" if self.random_bpm_var.get() else "#16c79a")

    def _on_random_scale_changed(self):
        state = "readonly" if not self.random_scale_var.get() else "readonly"
        self.scale_menu.config(state="readonly" if not self.random_scale_var.get() else "disabled")

    def _on_random_root_changed(self):
        self.root_menu.config(state="readonly" if not self.random_root_var.get() else "disabled")

    def _on_random_melody_changed(self):
        self.melody_timbre_menu.config(state="readonly" if not self.random_melody_timbre_var.get() else "disabled")

    def _on_random_bass_changed(self):
        self.bass_timbre_menu.config(state="readonly" if not self.random_bass_timbre_var.get() else "disabled")

    def _on_random_bars_changed(self):
        state = "normal" if not self.random_bars_var.get() else "disabled"
        self.bars_scale.config(state=state)
        self.bars_label.config(fg="#555" if self.random_bars_var.get() else "#16c79a")

    def _get_param_or_none(self, random_var, value_var):
        """根据随机复选框返回参数值或None"""
        return None if random_var.get() else value_var.get()

    def on_generate(self):
        self.on_stop()
        self.lbl_status.config(text="生成中…", fg="#f39c12")
        self.root.update_idletasks()

        # 收集参数
        bpm = self._get_param_or_none(self.random_bpm_var, self.bpm_var)
        scale_name = self._get_param_or_none(self.random_scale_var, self.scale_var)
        root_note = self._get_param_or_none(self.random_root_var, self.root_var)
        root_octave = None if self.random_root_var.get() else self.octave_var.get()
        melody_timbre = self._get_param_or_none(self.random_melody_timbre_var, self.melody_timbre_var)
        bass_timbre = self._get_param_or_none(self.random_bass_timbre_var, self.bass_timbre_var)
        n_bars = self._get_param_or_none(self.random_bars_var, self.bars_var)
        add_reverb = self.reverb_var.get()

        # 收集选中的乐器
        instruments = []
        if self.melody_var.get():
            instruments.append("旋律")
        if self.bass_var.get():
            instruments.append("低音")
        if self.drums_var.get():
            instruments.append("鼓")
        if self.pad_var.get():
            instruments.append("Pad")

        try:
            output_path, params, samples, sr = generate_music(
                return_samples=True,
                sample_rate=44100,
                bpm=bpm,
                scale_name=scale_name,
                root_note=root_note,
                root_octave=root_octave,
                melody_timbre=melody_timbre,
                bass_timbre=bass_timbre,
                n_bars=n_bars,
                instruments=instruments,
                add_reverb=add_reverb
            )
            self.wav_path = output_path
            self.params = params
            self.samples = samples
            self.sample_rate = sr
            self.duration = len(samples) / sr

            self.lbl_status.config(text="分析频谱…", fg="#f39c12")
            self.root.update_idletasks()
            self.spectrum_frames = compute_spectrum(samples, sr,
                                                    window_size=2048, hop_size=1024)

            info_text = " | ".join([f"{k}: {v}" for k, v in params.items()])
            info_text += f"  |  时长: {self.duration:.1f}s"
            self.lbl_info.config(text=info_text)

            self.draw_static_preview()
            self.lbl_status.config(text="就绪", fg="#16c79a")
            messagebox.showinfo("完成", f"音乐已生成并保存至:\n{output_path}")
        except Exception as e:
            messagebox.showerror("错误", f"生成失败:\n{e}")
            self.lbl_status.config(text="错误", fg="#e94560")

    # 以下为之前已实现的全部可视化方法（draw_spectrum, draw_wave_scrolling, draw_wave_overview,
    # draw_spectrum_wave_mixed, draw_circular_spectrum, draw_ripple, init_particles, draw_particles,
    # draw_mountain, start_animation 等）需保留。因篇幅原因此处省略，实际使用时请将前面完整版的可视化部分复制至此。
    # ... [可视化方法代码] ...

    def draw_spectrum(self, progress_time):
        if not self.spectrum_frames:
            return
        idx = self.get_frame_index_for_time(progress_time)
        energies = self.spectrum_frames[idx]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return
        if self.viz_mode == 2:
            region_h = h * 0.4
            y_offset = 10
        else:
            region_h = h * 0.8
            y_offset = h * 0.1
        bar_w = (w - 20) / len(energies)
        max_energy = max(energies) if max(energies) > 0 else 1
        self.canvas.delete("spectrum")
        for i, eng in enumerate(energies):
            scaler = math.sqrt(eng / max_energy)
            bar_h = scaler * (region_h - 20)
            x0 = 10 + i * bar_w
            y0 = region_h + y_offset - bar_h
            x1 = x0 + bar_w - 2
            y1 = region_h + y_offset
            color = self.get_bar_color(i, len(energies))
            self.canvas.create_rectangle(x0, y0, x1, y1,
                                         fill=color, outline="", tags="spectrum")

    def get_bar_color(self, index, total):
        colors = ["#ff0000", "#ff8800", "#ffff00", "#00ff00",
                  "#0088ff", "#0000ff", "#8800ff", "#ff00ff"]
        return colors[index % len(colors)]

    def draw_wave_scrolling(self, elapsed):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50 or not self.samples:
            return
        center_sample = int(elapsed * self.sample_rate)
        window_samples = int(0.05 * self.sample_rate)
        half_win = window_samples // 2
        start = max(0, center_sample - half_win)
        end = min(len(self.samples), center_sample + half_win)
        pts = []
        for i in range(start, end):
            x = ((i - start) / (end - start)) * w
            y = h/2 + self.samples[i] * (h/2 - 20)
            pts.append((x, y))
        if len(pts) > 1:
            self.canvas.create_line(pts, fill="#00ff00", width=2, tags="wave")

    def draw_wave_overview(self, region_y_start=None, region_height=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if not self.samples or w < 50:
            return
        if region_y_start is None:
            region_y_start = 0
            region_height = h
        step = max(1, len(self.samples) // w)
        pts = []
        for i in range(0, len(self.samples), step):
            x = (i / len(self.samples)) * w
            y = region_y_start + region_height/2 + self.samples[min(i, len(self.samples)-1)] * (region_height/2 - 10)
            pts.append((x, y))
        if len(pts) > 1:
            self.canvas.create_line(pts, fill="#00ff00", width=1, tags="wave")

    def draw_spectrum_wave_mixed(self, elapsed):
        self.draw_spectrum(elapsed)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        region_y = h * 0.55
        region_h = h * 0.35
        center_sample = int(elapsed * self.sample_rate)
        window_samples = int(0.05 * self.sample_rate)
        half = window_samples // 2
        start = max(0, center_sample - half)
        end = min(len(self.samples), center_sample + half)
        pts = []
        for i in range(start, end):
            x = ((i - start) / (end - start)) * w
            y = region_y + region_h/2 + self.samples[i] * (region_h/2 - 10)
            pts.append((x, y))
        if len(pts) > 1:
            self.canvas.create_line(pts, fill="#00ff00", width=2, tags="wave")

    def draw_circular_spectrum(self, progress_time):
        if not self.spectrum_frames:
            return
        idx = self.get_frame_index_for_time(progress_time)
        energies = self.spectrum_frames[idx]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w // 2, h // 2
        max_energy = max(energies) if max(energies) > 0 else 1
        radius = min(w, h) * 0.35
        self.canvas.delete("circular")
        for i, eng in enumerate(energies):
            angle = i * (2 * math.pi / len(energies)) - math.pi / 2
            length = (eng / max_energy) * radius * 0.9
            inner_r = radius * 0.3
            x0 = cx + inner_r * math.cos(angle)
            y0 = cy + inner_r * math.sin(angle)
            x1 = cx + (inner_r + length) * math.cos(angle)
            y1 = cy + (inner_r + length) * math.sin(angle)
            color = self.get_bar_color(i, len(energies))
            self.canvas.create_line(x0, y0, x1, y1, fill=color, width=6, tags="circular")
        self.canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#ffffff", outline="", tags="circular")

    def draw_ripple(self, progress_time):
        if not self.spectrum_frames:
            return
        idx = self.get_frame_index_for_time(progress_time)
        energies = self.spectrum_frames[idx]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w // 2, h // 2
        max_energy = max(energies) if max(energies) > 0 else 1
        max_radius = min(w, h) * 0.45
        self.canvas.delete("ripple")
        for i, eng in enumerate(energies):
            radius = 20 + (eng / max_energy) * max_radius * 0.8
            gray = int(100 + 155 * (eng / max_energy))
            color = f"#{gray:02x}{gray:02x}{gray:02x}"
            self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                    outline=color, width=2, tags="ripple")
        self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill="#ffffff", outline="", tags="ripple")

    def init_particles(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.particles = []
        for _ in range(80):
            x = random.randint(0, w)
            y = random.randint(0, h)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-0.5, 0.5)
            self.particles.append([x, y, vx, vy])

    def draw_particles(self, progress_time):
        if not self.particles:
            self.init_particles()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        energy_factor = 0.3
        if self.spectrum_frames:
            idx = self.get_frame_index_for_time(progress_time)
            energies = self.spectrum_frames[idx]
            max_e = max(energies) if max(energies) > 0 else 1
            energy_factor = 0.1 + 0.9 * (sum(energies) / (len(energies) * max_e))
        self.canvas.delete("particle")
        for p in self.particles:
            p[2] += random.uniform(-0.2, 0.2)
            p[3] += random.uniform(-0.2, 0.2)
            p[0] += p[2] * energy_factor
            p[1] += p[3] * energy_factor
            if p[0] < 0: p[0] = 0; p[2] = abs(p[2])
            if p[0] > w: p[0] = w; p[2] = -abs(p[2])
            if p[1] < 0: p[1] = 0; p[3] = abs(p[3])
            if p[1] > h: p[1] = h; p[3] = -abs(p[3])
            gray = int(150 + 105 * energy_factor)
            color = f"#{gray:02x}{gray:02x}{gray:02x}"
            self.canvas.create_oval(p[0]-2, p[1]-2, p[0]+2, p[1]+2,
                                    fill=color, outline="", tags="particle")

    def draw_mountain(self, progress_time):
        if not self.spectrum_frames:
            return
        idx = self.get_frame_index_for_time(progress_time)
        energies = self.spectrum_frames[idx]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return
        self.canvas.delete("mountain")
        layers = [
            {"color": "#ff3300", "scale": 0.2, "offset": 0},
            {"color": "#ff9900", "scale": 0.3, "offset": 0.1},
            {"color": "#ffcc00", "scale": 0.4, "offset": 0.2},
            {"color": "#33cc33", "scale": 0.5, "offset": 0.3},
        ]
        base_y = h * 0.9
        for layer in layers:
            pts = []
            for i in range(len(energies) * 4 + 1):
                t = i / (len(energies) * 4)
                idx_float = t * (len(energies) - 1)
                idx_low = int(idx_float)
                idx_high = min(idx_low + 1, len(energies) - 1)
                frac = idx_float - idx_low
                eng = energies[idx_low] * (1 - frac) + energies[idx_high] * frac
                max_e = max(energies) if max(energies) > 0 else 1
                normalized = eng / max_e
                peak_h = normalized * h * layer["scale"] + h * layer["offset"]
                x = i * w / (len(energies) * 4)
                y = base_y - peak_h
                pts.append((x, y))
            pts.append((w, base_y))
            pts.append((0, base_y))
            self.canvas.create_polygon(pts, fill=layer["color"], outline="",
                                       stipple="gray25", tags="mountain")
            line_pts = [(x, y) for (x, y) in pts if y != base_y]
            self.canvas.create_line(line_pts, fill=layer["color"], width=2, tags="mountain")

    def start_animation(self):
        if not self.playing:
            return
        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.on_stop()
            self.draw_static_preview()
            return
        self.canvas.delete("all")
        if self.viz_mode == 0:
            self.draw_spectrum(elapsed)
        elif self.viz_mode == 1:
            self.draw_wave_scrolling(elapsed)
        elif self.viz_mode == 2:
            self.draw_spectrum_wave_mixed(elapsed)
        elif self.viz_mode == 3:
            self.draw_circular_spectrum(elapsed)
        elif self.viz_mode == 4:
            self.draw_ripple(elapsed)
        elif self.viz_mode == 5:
            self.draw_particles(elapsed)
        elif self.viz_mode == 6:
            self.draw_mountain(elapsed)
        self.after_id = self.root.after(50, self.start_animation)

    def draw_static_preview(self):
        self.canvas.delete("all")
        if not self.samples:
            return
        if self.viz_mode == 0:
            self.draw_spectrum(0.0)
        elif self.viz_mode == 1:
            self.draw_wave_overview()
        elif self.viz_mode == 2:
            self.draw_spectrum(0.0)
            self.draw_wave_overview(region_y_start=self.canvas.winfo_height()*0.55,
                                    region_height=self.canvas.winfo_height()*0.35)
        elif self.viz_mode == 3:
            self.draw_circular_spectrum(0.0)
        elif self.viz_mode == 4:
            self.draw_ripple(0.0)
        elif self.viz_mode == 5:
            self.init_particles()
            self.draw_particles(0.0)
        elif self.viz_mode == 6:
            self.draw_mountain(0.0)

    def on_play(self):
        if not self.wav_path or not self.samples:
            messagebox.showwarning("警告", "请先生成音乐")
            return
        if self.playing:
            return
        try:
            winsound.PlaySound(self.wav_path, winsound.SND_ASYNC)
            self.playing = True
            self.start_time = time.time()
            self.btn_play.config(text="⏸ 播放中")
            self.lbl_status.config(text=f"播放中… 模式: {VIZ_MODES[self.viz_mode]}")
            if self.viz_mode == 5:
                self.init_particles()
            self.start_animation()
        except Exception as e:
            messagebox.showerror("播放错误", str(e))

    def on_stop(self):
        if self.playing:
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.playing = False
            self.btn_play.config(text="▶ 播放")
            self.lbl_status.config(text="已停止")
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def toggle_viz_mode(self):
        self.viz_mode = (self.viz_mode + 1) % len(VIZ_MODES)
        self.lbl_status.config(text=f"可视化: {VIZ_MODES[self.viz_mode]}")
        self.draw_static_preview()
        if self.playing:
            self.start_animation()

    def get_frame_index_for_time(self, t):
        if not self.spectrum_frames:
            return 0
        hop_time = 1024 / self.sample_rate
        idx = int(t / hop_time)
        return max(0, min(idx, len(self.spectrum_frames) - 1))

    def on_closing(self):
        self.on_stop()
        self.root.destroy()


# ──────────────────────────────────────────
# 入口
# ──────────────────────────────────────────
def gui_mode():
    root = tk.Tk()
    app = MusicVisualizerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--gui" in args:
        gui_mode()
    elif "--help" in args or "-h" in args:
        print("""
用法:
  python music_gen.py              # 启动图形界面（含可视化+节奏增强）
  python music_gen.py --gui        # 同上
  python music_gen.py --random     # 直接随机生成一首 wav
  python music_gen.py --batch N    # 批量生成 N 首
        """)
    elif "--random" in args:
        path, _ = generate_music()
        print(f"  文件路径: {os.path.abspath(path)}")
    elif "--batch" in args:
        try:
            idx = args.index("--batch")
            n = int(args[idx + 1])
        except (IndexError, ValueError):
            n = 3
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for i in range(1, n + 1):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(script_dir, f"music_{i:02d}_{ts}.wav")
            print(f"\n── 第 {i} 首 ──")
            generate_music(output_path=out)
    else:
        gui_mode()