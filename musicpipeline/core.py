"""
核心合成引擎
─────────────
纯 Python 标准库实现的随机音乐生成器：
- 音符频率表 / 音阶 / 和弦进行
- 基础波形与 14 种乐器音色模拟
- ADSR 包络、混响、低通滤波
- 旋律 / 低音 / 和弦铺底 / 鼓轨生成
- 多轨混音与 WAV 写入
- 顶层入口 generate_music()
"""

import wave
import struct
import math
import random
import os
import sys
import time
from datetime import datetime


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
        # 2.0.0：默认写入当前工作目录，而非脚本所在目录（避免污染安装位置）
        output_path = os.path.join(os.getcwd(), f"music_{ts}.wav")

    samples_to_wav(mixed, sample_rate, output_path)
    print(f"\n🎼 完成！时长约 {len(mixed) / sample_rate:.1f} 秒")

    if return_samples:
        return output_path, params, mixed, sample_rate
    return output_path, params
