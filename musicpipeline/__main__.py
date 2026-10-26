"""
命令行入口：python -m musicpipeline [--gui | --random | --batch N | -h]
也可经 PyPI console_script `musicpipeline` 调用。
"""

import os
import sys
from datetime import datetime

from .core import generate_music
from .visualizer import gui_mode


USAGE = """
用法:
  python -m musicpipeline            # 启动图形界面（默认）
  python -m musicpipeline --gui      # 同上
  python -m musicpipeline --random   # 直接随机生成一首 wav（写入当前目录）
  python -m musicpipeline --batch N  # 批量生成 N 首
"""


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if "--gui" in args:
        gui_mode()
    elif "--help" in args or "-h" in args:
        print(USAGE)
    elif "--random" in args:
        path, _ = generate_music()
        print(f"  文件路径: {os.path.abspath(path)}")
    elif "--batch" in args:
        try:
            idx = args.index("--batch")
            n = int(args[idx + 1])
        except (IndexError, ValueError):
            n = 3
        for i in range(1, n + 1):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(os.getcwd(), f"music_{i:02d}_{ts}.wav")
            print(f"\n── 第 {i} 首 ──")
            generate_music(output_path=out)
    else:
        gui_mode()


if __name__ == "__main__":
    main()
