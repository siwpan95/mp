# mp

> 仓库：<https://gitee.com/siwpan/mp> ｜ 许可：MIT（见 [LICENSE](LICENSE)）
> 注：文中 <PATH> 为路径占位符，请替换为你本机实际的目录 / 可执行文件路径。

随机音乐生成器 + WMP 风格可视化，纯 Python 标准库实现（tkinter 图形界面）。
独立仓 siwpan/mp（本地 `<PATH>`）。

## 类型
代码项目（Python）

## 目录要点
- autoav.py / autoavmaker.py / just.py / musav.py / orc.py：功能逐步增强的生成器迭代（多乐器模拟、鼓与和弦铺底、时长控制、多效果可视化）
- music_20260614_*.wav / music_v2_*.wav：生成的示例 WAV 输出
- mu.json：配置/数据
- mumu/：辅助目录

## 用途
随机生成音乐并做可视化演示，导出 WAV 文件，无外部依赖。

## 测试状态
5 个脚本全部通过 py_compile 语法检查（syntax_ok）；GUI 未运行。

## 运行

```bash
python orc.py      # 迭代终点版（多效果可视化）
python autoav.py   # 早期版（多乐器模拟）
```

## 发布面与许可

- gitee：siwpan/mp，release `v1.0.0`（便携源码 zip）。
- 许可：MIT · Copyright (c) 2026 siwpan
