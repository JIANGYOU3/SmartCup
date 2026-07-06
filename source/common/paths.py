"""项目路径工具 —— 统一项目根目录获取，消除重复的 parent.parent.parent 模式"""

from pathlib import Path

# 当前文件位于 source/common/，项目根目录在两级之上
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_project_root() -> Path:
    """返回 SmartCup 项目根目录"""
    return _PROJECT_ROOT


def get_data_dir(subdir: str = "zhihu") -> Path:
    """返回 res/data/{subdir}/ 目录"""
    return _PROJECT_ROOT / "res" / "data" / subdir


def get_raw_dir(subdir: str = "zhihu") -> Path:
    """返回 res/data/{subdir}/raw/ 目录"""
    return get_data_dir(subdir) / "raw"


def get_output_dir(subdir: str = "zhihu") -> Path:
    """返回 res/data/{subdir}/output/ 目录"""
    return get_data_dir(subdir) / "output"


def load_env():
    """加载项目 .env 文件，返回 True 表示加载成功"""
    from dotenv import load_dotenv
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        return True
    return False
