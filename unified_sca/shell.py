from __future__ import annotations

import shlex
import sys

from .cli import main as cli_main


HELP_TEXT = """可用命令：
  detect <path> [--first-level] [--keep-workdir] [--work-base <dir>]
  scan <path> --results-dir <dir>
  help
  exit / quit

示例：
  detect /path/to/test_project
  scan /path/to/sample_npm --results-dir /path/to/results
"""


def run_shell() -> int:
    print("SCA Shell (输入 help 查看用法，exit 退出)")
    while True:
        try:
            line = input("sca> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue
        if line in {"exit", "quit"}:
            return 0
        if line == "help":
            print(HELP_TEXT)
            continue

        try:
            argv = shlex.split(line)
        except ValueError as e:
            print(f"解析命令失败: {e}")
            continue

        # 调用同一套 CLI 逻辑执行子命令
        try:
            code = cli_main(argv)
            # cli_main 返回 int；为避免 shell 直接退出，这里只打印错误码
            if code not in (0, None):
                print(f"(exit code {code})")
        except SystemExit as e:
            # argparse 可能会抛 SystemExit
            code = e.code if isinstance(e.code, int) else 1
            if code != 0:
                print(f"(exit code {code})")
        except Exception as e:
            print(f"执行失败: {e}")


