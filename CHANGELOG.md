# Changelog

本项目所有值得注意的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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