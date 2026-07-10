"""
实时查看抖音评论拉取进度

用法：
  conda run -n SmartCup python progress.py           # 单次查看
  conda run -n SmartCup python -u progress.py --watch # 持续监控（5s刷新）
"""

import argparse
import csv
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CSV_PATH = PROJECT_ROOT / "res/data/douyin/output/爬取结果_全量_含评论.csv"
TOTAL = 1718


def get_rows() -> int:
    """读取已完成的条数（兼容多行内容）"""
    if not CSV_PATH.exists():
        return 0
    try:
        with open(CSV_PATH, encoding="utf-8-sig") as f:
            return sum(1 for _ in csv.DictReader(f))
    except Exception:
        return 0


def get_file_size_mb() -> float:
    if not CSV_PATH.exists():
        return 0.0
    return CSV_PATH.stat().st_size / (1024 * 1024)


def render_bar(current: int, total: int, width: int = 30) -> str:
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return f"│{bar}│ {pct:.1%}"


def check_process() -> bool:
    """检查 fetch_comments_only.py 是否在运行"""
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", "fetch_comments_only"],
            capture_output=True, text=True
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def show_progress():
    current = get_rows()
    size_mb = get_file_size_mb()
    running = check_process()
    status = "🟢 运行中" if running else "🔴 已停止"

    print(f"\n{'='*50}")
    print(f"  抖音评论拉取进度  {status}")
    print(f"{'='*50}")
    print(f"  总数: {TOTAL} 条")
    print(f"  已完成: {current} 条")
    print(f"  {render_bar(current, TOTAL)}")
    print(f"  文件大小: {size_mb:.1f} MB")
    if current > 0:
        eta_sec = (TOTAL - current) * 12  # 约12秒/条
        eta_min = eta_sec // 60
        print(f"  预计剩余: {eta_min} 分钟 (~{eta_min//60}h {eta_min%60}m)")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="抖音评论拉取进度监控")
    parser.add_argument("--watch", "-w", action="store_true", help="持续监控（每5秒刷新）")
    parser.add_argument("--interval", "-n", type=int, default=5, help="刷新间隔秒数（默认5）")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                os.system("clear" if os.name != "nt" else "cls")
                show_progress()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n👋 退出监控")
    else:
        show_progress()


if __name__ == "__main__":
    main()
