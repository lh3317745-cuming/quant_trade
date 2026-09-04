from __future__ import annotations

import inspect
import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

# .env 位于仓库根目录（annotations 的上一级），故用 parent.parent 定位
DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

_F = TypeVar("_F", bound=Callable[..., Any])


def load_dotenv(path: Path | None = None) -> None:
    """从 .env 读取 KEY=VALUE 到 os.environ（不覆盖已存在的环境变量）。"""
    if path is None:
        path = DEFAULT_ENV_PATH
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def auto_load_env(func: _F) -> _F:
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            load_dotenv()
            return await func(*args, **kwargs)

        return cast(_F, async_wrapper)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        load_dotenv()
        return func(*args, **kwargs)

    return cast(_F, wrapper)
