# musicpipeline

> 仓库：<https://gitee.com/siwpan/mp> ｜ 许可：MIT（见 [LICENSE](LICENSE)）
> 注：文中 `<PATH>` 为路径占位符，请替换为你本机实际的目录 / 可执行文件路径。

随机音乐生成器 + WMP 风格可视化，纯 Python 标准库实现（tkinter 图形界面）。
独立仓 siwpan/mp（本地 `<PATH>`）。

## 类型
代码项目（Python）

## 目录要点
- `musicpipeline/`：Python 包，拆分为多模块：
  - `core.py`：合成引擎（音符/音阶/音色/ADSR/混响/滤波/旋律·低音·铺底·鼓轨生成/`generate_music`）
  - `analysis.py`：频谱分析（Goertzel 算法 + 帧能量）
  - `visualizer.py`：tkinter GUI 与 7 种可视化效果
  - `__init__.py`：公开接口与 `__version__`
  - `__main__.py`：`python -m musicpipeline` 命令行入口
- `*.wav / *.mp3`：生成的音频产物（已 gitignore，不入库）
- `mumu/`：本地采样/素材目录（音频产物，已 gitignore）

## 用途
随机生成音乐并做可视化演示，导出 WAV 文件，无外部依赖。

## 测试状态
包通过 `py_compile` 语法检查；`import musicpipeline` 与 `generate_music(return_samples=True)` 可生成有效 WAV（非 GUI 冒烟通过）；GUI 未运行。

## 运行

```bash
python -m musicpipeline            # 启动图形界面（默认）
python -m musicpipeline --random   # 直接随机生成一首 wav（写入当前目录）
python -m musicpipeline --batch 5  # 批量生成 5 首
```

安装后也可用 console_script：

```bash
pip install musicpipeline
musicpipeline --random
```

作为库调用：

```python
from musicpipeline import generate_music
path, params = generate_music(bpm=120, n_bars=8, scale_name="大调")
```

## 发布面与许可

- gitee：siwpan/mp，release `v2.0.0`（便携源码 zip）。
- PyPI：musicpipeline 2.0.0。
- 许可：MIT · Copyright (c) 2026 siwpan
