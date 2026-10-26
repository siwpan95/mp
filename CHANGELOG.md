# Changelog

本项目所有值得注意的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.0.1] - 2026-10-26

### Added
- 向后兼容垫片：在分发包顶层保留 `orc.py`，重新导出 `musicpipeline` 的全部公开接口（`generate_music` / `gui_mode` / `MusicVisualizerApp` / 各合成与频谱函数 / `VIZ_MODES` 等），导入时发出 `DeprecationWarning` 提示迁移到 `import musicpipeline`。
- 纯新增、非破坏性（`import musicpipeline` 行为不变），故为补丁版本。
- 打包配置：`[tool.setuptools]` 增加 `py-modules = ["orc"]`（与 `packages = ["musicpipeline"]` 并存），使 `import orc` 仍可解析。

## [2.0.0] - 2026-10-26

### Changed
- **破坏性变更（Breaking）**：将单文件 `orc.py` 重构为 Python 包 `musicpipeline/`，按职责拆分为多模块：
  - `core.py`：合成引擎（音符频率表 / 音阶 / 和弦进行 / 基础波形 / 14 种乐器音色 / ADSR / 混响·滤波 / 旋律·低音·铺底·鼓轨生成 / `generate_music`）。
  - `analysis.py`：频谱分析（Goertzel 算法 + 滑动窗口帧能量）。
  - `visualizer.py`：tkinter GUI 与 7 种可视化效果（`MusicVisualizerApp` / `gui_mode` / `VIZ_MODES`）。
  - `__init__.py`：公开接口与 `__version__ = "2.0.0"`；GUI 在非 Windows / 无显示环境下导入失败时降级为纯合成库。
  - `__main__.py`：`python -m musicpipeline` 命令行入口。
- 公开接口由 `import orc` 变更为 `import musicpipeline`；新增 console_script 入口 `musicpipeline`。
- `generate_music` 默认输出目录由「脚本所在目录」改为「当前工作目录」，避免污染安装位置。
- 打包配置：`py-modules = ["orc"]` → `packages = ["musicpipeline"]`；新增 `[project.scripts]`。

### Removed
- 删除单文件 `orc.py`（功能已 100% 迁移至 `musicpipeline/` 包，旧历史仍可从 git 恢复）。

## [1.1.0] - 2026-10-26

### Changed
- 整合去重：autoav.py / autoavmaker.py / just.py / musav.py / orc.py 五个渐进迭代合并为单一 `orc.py`（功能超集：14 种乐器音色、鼓组与和弦铺底、随机参数控制、7 种可视化）。旧文件仍保留于 git 历史，可随时恢复。
- 音频产物（*.wav / *.mp3 及 mumu/）移出版本控制并加入 .gitignore。
- 移除误提交的 junk mu.json（实为无关的 MCP 工具调用结果转储）。
- 打包收敛：py-modules 由 5 个改为 ["orc"]；版本 1.0.0 → 1.1.0。

## [1.0.0] - 2026-08-27

### Added

- 首个发行版：便携源码 zip（剔除 .venv/构建产物/输出物，依赖见 README）。
- 发布面：gitee [siwpan/mp](https://gitee.com/siwpan/mp) release `v1.0.0`（mp v1.0.0）。
