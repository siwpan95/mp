"""
可视化模块（WMP 风格）
──────────────────────
基于 tkinter 的图形界面：参数面板 + 7 种可视化效果
（频谱条形 / 滚动波形 / 频谱+波形 / 圆形频谱 / 声波涟漪 / 粒子舞蹈 / 频谱山脉），
并集成 generate_music 一键生成。仅依赖标准库（tkinter / winsound，Windows）。
"""

import math
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox
import winsound  # Windows 播放

from .core import generate_music, SCALES, TIMBRES
from .analysis import compute_spectrum, VIZ_FREQS


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
        state = "normal" if not self.random_scale_var.get() else "readonly"
        self.scale_menu.config(state=state)

    def _on_random_root_changed(self):
        self.root_menu.config(state="normal" if not self.random_root_var.get() else "readonly")

    def _on_random_melody_changed(self):
        self.melody_timbre_menu.config(state="normal" if not self.random_melody_timbre_var.get() else "readonly")

    def _on_random_bass_changed(self):
        self.bass_timbre_menu.config(state="normal" if not self.random_bass_timbre_var.get() else "readonly")

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


def gui_mode():
    root = tk.Tk()
    app = MusicVisualizerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
