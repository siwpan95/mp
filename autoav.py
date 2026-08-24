"""
随机音乐生成器 + WMP 风格可视化 - 纯 Python 标准库实现
无任何外部依赖，生成 WAV 格式音乐文件并提供图形界面
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
import threading
import winsound  # 仅用于 Windows 播放，若跨平台可替换


# ──────────────────────────────────────────
# 音符频率表 (Hz)  A4 = 440 Hz
# ──────────────────────────────────────────
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def note_freq(name: str, octave: int) -> float:
    """根据音名和八度返回频率"""
    semitone = NOTE_NAMES.index(name)
    midi = (octave + 1) * 12 + semitone
    return 440.0 * (2 ** ((midi - 69) / 12))


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
# 波形合成函数（音符内时间）
# ──────────────────────────────────────────
def sine_wave(freq: float, t: float) -> float:
    return math.sin(2 * math.pi * freq * t)

def square_wave(freq: float, t: float, duty: float = 0.5) -> float:
    phase = (freq * t) % 1.0
    return 1.0 if phase < duty else -1.0

def sawtooth_wave(freq: float, t: float) -> float:
    return 2.0 * ((freq * t) % 1.0) - 1.0

def triangle_wave(freq: float, t: float) -> float:
    p = (freq * t) % 1.0
    return 4.0 * p - 1.0 if p < 0.5 else 3.0 - 4.0 * p

def organ_wave(freq: float, t: float) -> float:
    return (
        sine_wave(freq, t) * 0.5 +
        sine_wave(freq * 2, t) * 0.3 +
        sine_wave(freq * 3, t) * 0.15 +
        sine_wave(freq * 4, t) * 0.05
    )

def piano_wave(freq: float, t: float, duration: float) -> float:
    harmonics = (
        sine_wave(freq, t) * 1.0 +
        sine_wave(freq * 2, t) * 0.5 +
        sine_wave(freq * 3, t) * 0.25 +
        sine_wave(freq * 4, t) * 0.1 +
        sine_wave(freq * 5, t) * 0.05
    )
    decay = math.exp(-t * 4.0 / max(duration, 0.01))
    return harmonics * decay

TIMBRES = ["钢琴", "管风琴", "正弦波", "方波", "三角波", "锯齿波"]


# ──────────────────────────────────────────
# ADSR 包络（修护极短音符保护）
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
# 音符渲染
# ──────────────────────────────────────────
def render_note(freq: float, duration: float, sample_rate: int,
                timbre: str, volume: float = 0.8) -> list:
    n_samples = int(duration * sample_rate)
    samples = []
    for i in range(n_samples):
        note_t = i / sample_rate
        if freq <= 0:
            samples.append(0.0)
            continue
        if timbre == "钢琴":
            raw = piano_wave(freq, note_t, duration)
        elif timbre == "管风琴":
            raw = organ_wave(freq, note_t)
        elif timbre == "方波":
            raw = square_wave(freq, note_t, duty=random.uniform(0.4, 0.6))
        elif timbre == "三角波":
            raw = triangle_wave(freq, note_t)
        elif timbre == "锯齿波":
            raw = sawtooth_wave(freq, note_t)
        else:
            raw = sine_wave(freq, note_t)
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
# 旋律 & 低音生成
# ──────────────────────────────────────────
def build_scale_notes(root_name: str, root_octave: int, scale_intervals: list) -> list:
    root_semitone = NOTE_NAMES.index(root_name) + (root_octave + 1) * 12
    notes = []
    for octave_offset in [0, 12]:
        for interval in scale_intervals:
            midi = root_semitone + interval + octave_offset
            freq = 440.0 * (2 ** ((midi - 69) / 12))
            notes.append(freq)
    return notes

def generate_melody(scale_notes: list, n_bars: int, bpm: int, time_sig=4) -> list:
    beat_dur = 60.0 / bpm
    rhythms = [
        [1, 1, 1, 1],
        [0.5, 0.5, 1, 1, 1],
        [2, 1, 1],
        [0.5, 0.5, 0.5, 0.5, 1, 1],
        [1.5, 0.5, 1, 1],
        [0.25, 0.25, 0.5, 1, 1, 1],
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

def generate_bass(scale_notes: list, chord_prog: list, n_bars: int, bpm: int, time_sig=4) -> list:
    beat_dur = 60.0 / bpm
    target_duration = n_bars * time_sig * beat_dur
    bass_notes = scale_notes[:len(scale_notes) // 2]
    bass = []
    total_dur = 0.0
    while total_dur < target_duration:
        for chord_idx in chord_prog:
            if total_dur >= target_duration:
                break
            root_idx = min(chord_idx - 1, len(bass_notes) - 1)
            fifth_idx = min(root_idx + 4, len(bass_notes) - 1)
            pattern = [
                (bass_notes[root_idx], beat_dur),
                (bass_notes[fifth_idx], beat_dur * 0.5),
                (bass_notes[root_idx], beat_dur * 0.5),
                (bass_notes[fifth_idx], beat_dur),
                (bass_notes[root_idx], beat_dur),
            ]
            for freq, dur in pattern:
                if total_dur >= target_duration:
                    break
                dur = min(dur, target_duration - total_dur)
                bass.append((freq, dur))
                total_dur += dur
    return bass


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
# 音频生成（返回样本数据用于可视化）
# ──────────────────────────────────────────
def generate_music(output_path: str = None,
                   bpm: int = None,
                   scale_name: str = None,
                   root_note: str = None,
                   root_octave: int = None,
                   timbre: str = None,
                   n_bars: int = None,
                   add_bass: bool = None,
                   add_reverb: bool = None,
                   sample_rate: int = 44100,
                   return_samples: bool = False):
    bpm = bpm or random.randint(70, 160)
    scale_name = scale_name or random.choice(list(SCALES.keys()))
    root_note = root_note or random.choice(["C", "D", "E", "F", "G", "A", "B"])
    root_octave = root_octave if root_octave is not None else random.choice([4, 5])
    timbre = timbre or random.choice(TIMBRES)
    n_bars = n_bars or random.randint(8, 24)
    add_bass = add_bass if add_bass is not None else random.choice([True, False])
    add_reverb = add_reverb if add_reverb is not None else random.choice([True, False])

    chord_prog = random.choice(CHORD_PROGRESSIONS)
    time_sig = 4

    params = {
        "bpm": bpm,
        "调式": scale_name,
        "主音": f"{root_note}{root_octave}",
        "音色": timbre,
        "小节数": n_bars,
        "低音声部": add_bass,
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

    print("  生成旋律…")
    melody_seq = generate_melody(scale_notes, n_bars, bpm, time_sig)
    melody_track = []
    for freq, dur in melody_seq:
        melody_track.extend(render_note(freq, dur, sample_rate, timbre, volume=0.75))

    tracks = [melody_track]

    if add_bass:
        print("  生成低音…")
        bass_seq = generate_bass(scale_notes, chord_prog, n_bars, bpm, time_sig)
        bass_track = []
        bass_timbre = "正弦波"
        for freq, dur in bass_seq:
            bass_track.extend(render_note(freq / 2, dur, sample_rate, bass_timbre, volume=0.45))
        tracks.append(bass_track)

    print("  混合音轨…")
    mixed = mix_tracks(tracks, sample_rate)

    if add_reverb:
        print("  应用混响…")
        mixed = apply_reverb(mixed, sample_rate,
                             delay_ms=random.uniform(60, 120),
                             decay=random.uniform(0.2, 0.45),
                             mix=0.3)

    if timbre in ("方波", "锯齿波"):
        mixed = low_pass_filter(mixed, cutoff_ratio=0.25)

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


# ──────────────────────────────────────────
# 可视化工具：Goertzel 算法计算频点能量
# ──────────────────────────────────────────
def goertzel(samples: list, target_freq: float, sample_rate: float) -> float:
    """返回指定频率的能量（幅度平方）"""
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


# 可视化使用的中心频率（Hz）—— 对应低音到高音
VIZ_FREQS = [50, 100, 200, 400, 800, 1600, 3200, 6000]

def compute_spectrum(samples, sample_rate, window_size=2048, hop_size=1024):
    """将整个音频切分为帧，计算每帧各频率的能量，返回列表 frame_energies"""
    frames = []
    for start in range(0, len(samples) - window_size, hop_size):
        window = samples[start:start + window_size]
        energies = [goertzel(window, f, sample_rate) for f in VIZ_FREQS]
        frames.append(energies)
    return frames


# ──────────────────────────────────────────
# 图形界面
# ──────────────────────────────────────────
class MusicVisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("随机音乐生成器 - WMP 风格可视化")
        self.root.geometry("900x500")
        self.root.resizable(False, False)

        # 数据
        self.samples = []          # 原始音频采样点（浮点）
        self.sample_rate = 44100
        self.spectrum_frames = []  # 频谱帧列表
        self.duration = 0.0        # 音频总时长（秒）
        self.playing = False
        self.start_time = 0.0
        self.after_id = None
        self.wav_path = None
        self.params = {}

        # 当前可视化模式 0:频谱 1:波形 2:频谱+波形
        self.viz_mode = 0

        self.setup_ui()

    def setup_ui(self):
        # 控制面板
        control_frame = tk.Frame(self.root, bg="#2b2b2b")
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        btn_gen = tk.Button(control_frame, text="🎲 随机生成", command=self.on_generate,
                            bg="#4a4a4a", fg="white", padx=10, pady=5)
        btn_gen.pack(side=tk.LEFT, padx=10)

        self.btn_play = tk.Button(control_frame, text="▶ 播放", command=self.on_play,
                                  bg="#4a4a4a", fg="white", padx=10, pady=5)
        self.btn_play.pack(side=tk.LEFT, padx=5)

        btn_stop = tk.Button(control_frame, text="⏹ 停止", command=self.on_stop,
                             bg="#4a4a4a", fg="white", padx=10, pady=5)
        btn_stop.pack(side=tk.LEFT, padx=5)

        btn_viz = tk.Button(control_frame, text="🔄 切换可视化", command=self.toggle_viz_mode,
                            bg="#4a4a4a", fg="white", padx=10, pady=5)
        btn_viz.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self.lbl_status = tk.Label(control_frame, text="准备就绪", fg="#a0a0a0", bg="#2b2b2b")
        self.lbl_status.pack(side=tk.RIGHT, padx=20)

        # 画布
        self.canvas = tk.Canvas(self.root, bg="#000000", height=400)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 参数显示区域
        info_frame = tk.Frame(self.root, bg="#1e1e1e")
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_info = tk.Label(info_frame, text="", fg="#808080", bg="#1e1e1e",
                                 font=("Consolas", 10), justify=tk.LEFT)
        self.lbl_info.pack(pady=5)

        # 初始提示
        self.canvas.create_text(450, 200, text="点击「随机生成」开始",
                                fill="#505050", font=("微软雅黑", 20))

    def on_generate(self):
        """生成新音乐，并预计算频谱"""
        self.on_stop()  # 停止当前播放
        self.lbl_status.config(text="生成中…")
        self.root.update_idletasks()

        try:
            output_path, params, samples, sr = generate_music(
                return_samples=True,
                sample_rate=44100
            )
            self.wav_path = output_path
            self.params = params
            self.samples = samples
            self.sample_rate = sr
            self.duration = len(samples) / sr

            # 计算频谱帧
            self.lbl_status.config(text="分析频谱…")
            self.root.update_idletasks()
            self.spectrum_frames = compute_spectrum(samples, sr,
                                                    window_size=2048, hop_size=1024)

            # 显示参数信息
            info_text = " | ".join([f"{k}: {v}" for k, v in params.items()])
            info_text += f"\n时长: {self.duration:.1f}s | 采样率: {sr}Hz"
            self.lbl_info.config(text=info_text)

            # 绘制静态预览（进度=0）
            self.draw_static_preview()
            self.lbl_status.config(text="就绪")
            messagebox.showinfo("完成", f"音乐已生成并保存至:\n{output_path}")
        except Exception as e:
            messagebox.showerror("错误", f"生成失败:\n{e}")
            self.lbl_status.config(text="错误")

    def draw_static_preview(self):
        """绘制频谱 / 波形的静态快照（进度=0）"""
        self.canvas.delete("all")
        if not self.samples:
            return
        if self.viz_mode == 0 or self.viz_mode == 2:
            self.draw_spectrum(0.0)
        if self.viz_mode == 1 or self.viz_mode == 2:
            self.draw_wave_overview()

    def get_frame_index_for_time(self, t):
        """根据播放时间 t (秒) 返回对应的频谱帧索引"""
        if not self.spectrum_frames:
            return 0
        hop_time = 1024 / self.sample_rate  # 每帧的时间跨度（秒）
        idx = int(t / hop_time)
        return max(0, min(idx, len(self.spectrum_frames) - 1))

    def draw_spectrum(self, progress_time):
        """绘制当前时间的频谱条形（旧版 WMP 风格）"""
        if not self.spectrum_frames:
            return
        idx = self.get_frame_index_for_time(progress_time)
        energies = self.spectrum_frames[idx]

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        # 确定绘制区域（如果同时显示波形，频谱放在上半部）
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
            scaler = math.sqrt(eng / max_energy)  # 使条形高度更明显
            bar_h = scaler * (region_h - 20)
            x0 = 10 + i * bar_w
            y0 = region_h + y_offset - bar_h
            x1 = x0 + bar_w - 2
            y1 = region_h + y_offset
            color = self.get_bar_color(i, len(energies))
            self.canvas.create_rectangle(x0, y0, x1, y1,
                                         fill=color, outline="", tags="spectrum")

    def draw_wave_overview(self):
        """绘制完整波形缩略图（底部）或滚动波形（根据模式）"""
        if not self.samples:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        if self.viz_mode == 1:  # 仅波形：显示整个波形概览
            self.canvas.delete("wave")
            pts = []
            step = max(1, len(self.samples) // w)
            for i in range(0, min(len(self.samples), w * step), step):
                idx = min(i, len(self.samples)-1)
                x = (i / step) * (w / (len(self.samples)/step))  # 适配宽度
                y = h/2 + self.samples[idx] * (h/2 - 20)
                pts.append((x, y))
            if len(pts) > 1:
                self.canvas.create_line(pts, fill="#00ff00", width=1, tags="wave")
        elif self.viz_mode == 2:  # 频谱+波形：波形放在下半部
            pass  # 可以在动画循环中绘制滚动波形，静态预览不显示滚动

    def get_bar_color(self, index, total):
        """根据位置赋予彩虹色（类似 WMP）"""
        colors = ["#ff0000", "#ff8800", "#ffff00", "#00ff00",
                  "#0088ff", "#0000ff", "#8800ff", "#ff00ff"]
        return colors[index % len(colors)]

    def toggle_viz_mode(self):
        """切换可视化模式"""
        self.viz_mode = (self.viz_mode + 1) % 3
        modes = ["频谱", "波形", "频谱+波形"]
        self.lbl_status.config(text=f"可视化: {modes[self.viz_mode]}")
        self.draw_static_preview()
        if self.playing:
            # 重启动画以新样式绘制
            self.start_animation()

    def on_play(self):
        """播放音乐并启动可视化动画"""
        if not self.wav_path or not self.samples:
            messagebox.showwarning("警告", "请先生成音乐")
            return
        if self.playing:
            return
        try:
            # 异步播放 wav（Windows Only）
            winsound.PlaySound(self.wav_path, winsound.SND_ASYNC)
            self.playing = True
            self.start_time = time.time()
            self.btn_play.config(text="⏸ 播放中")
            self.lbl_status.config(text="播放中…")
            self.start_animation()
        except Exception as e:
            messagebox.showerror("播放错误", str(e))

    def on_stop(self):
        """停止播放和动画"""
        if self.playing:
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.playing = False
            self.btn_play.config(text="▶ 播放")
            self.lbl_status.config(text="已停止")
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def start_animation(self):
        """启动可视化动画循环"""
        if not self.playing:
            return
        # 计算当前播放时间
        elapsed = time.time() - self.start_time
        if elapsed > self.duration:
            self.on_stop()
            self.draw_static_preview()
            return

        # 更新可视化
        self.canvas.delete("all")
        if self.viz_mode == 0:
            self.draw_spectrum(elapsed)
        elif self.viz_mode == 1:
            self.draw_wave_scrolling(elapsed)
        elif self.viz_mode == 2:
            # 上半部频谱，下半部波形滚动
            self.draw_spectrum(elapsed)
            self.draw_wave_slice(elapsed, region_y_start=self.canvas.winfo_height()*0.55,
                                 region_height=self.canvas.winfo_height()*0.35)

        # 调度下一帧
        self.after_id = self.root.after(50, self.start_animation)

    def draw_wave_scrolling(self, elapsed):
        """滚动波形（当前播放位置居中）"""
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50 or not self.samples:
            return
        center_sample = int(elapsed * self.sample_rate)
        window_samples = int(0.05 * self.sample_rate)  # 显示 ±50ms
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

    def draw_wave_slice(self, elapsed, region_y_start=0, region_height=300):
        """绘制波形切片（用于混合模式的下半部）"""
        w = self.canvas.winfo_width()
        if w < 50 or region_height < 20 or not self.samples:
            return
        center_sample = int(elapsed * self.sample_rate)
        window_samples = int(0.05 * self.sample_rate)
        half_win = window_samples // 2
        start = max(0, center_sample - half_win)
        end = min(len(self.samples), center_sample + half_win)
        pts = []
        for i in range(start, end):
            x = ((i - start) / (end - start)) * w
            y = region_y_start + region_height/2 + self.samples[i] * (region_height/2 - 10)
            pts.append((x, y))
        if len(pts) > 1:
            self.canvas.create_line(pts, fill="#00ff00", width=2, tags="wave")

    def on_closing(self):
        """窗口关闭时停止播放"""
        self.on_stop()
        self.root.destroy()


# ──────────────────────────────────────────
# 入口扩展
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
  python music_gen.py              # 交互式 CLI 模式
  python music_gen.py --gui        # 启动图形界面（含可视化）
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
        # 引用原来的 batch_mode，需要保留原 batch_mode 定义（此处略，可补充）
        # 临时实现
        for i in range(1, n+1):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            out = os.path.join(script_dir, f"music_{i:02d}_{ts}.wav")
            print(f"\n── 第 {i} 首 ──")
            generate_music(output_path=out)
    else:
        # 默认无参数时进入 GUI（更友好）
        gui_mode()