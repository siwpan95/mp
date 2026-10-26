# mp

> 仓库：<https://gitee.com/siwpan/mp> ｜ 许可：MIT（见 [LICENSE](LICENSE)）
> 注：文中 <PATH> 为路径占位符，请替换为你本机实际的目录 / 可执行文件路径。

随机音乐生成器 + WMP 风格可视化，纯 Python 标准库实现（tkinter 图形界面）。
独立仓 siwpan/mp（本地 `<PATH>`）。

## 类型
代码项目（Python）

## 目录要点
- orc.py：统一音乐生成器 + 多乐器模拟 + 鼓与和弦铺底 + WMP 风格可视化（5 个渐进迭代已整合去重为单文件）
- *.wav / *.mp3：生成的音频产物（已 gitignore，不入库）
- mumu/：本地采样/素材目录（音频产物，已 gitignore）

## 用途
随机生成音乐并做可视化演示，导出 WAV 文件，无外部依赖。

## 测试状态
orc.py 通过 py_compile 语法检查；无 GUI 冒烟测试可生成有效 WAV；GUI 未运行。

## 运行

```bash
python orc.py            # 启动图形界面（默认）
python orc.py --random   # 直接随机生成一首 wav
python orc.py --batch 5  # 批量生成 5 首
```

## 发布面与许可

- gitee：siwpan/mp，release `v1.1.0`（便携源码 zip）。
- 许可：MIT · Copyright (c) 2026 siwpan
