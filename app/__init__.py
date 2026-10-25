"""加载项目根目录的 .env（若有），必须在 app 的其他模块导入前执行。

已在系统环境变量里设置过的键不会被覆盖，方便部署时用真实环境变量优先。
"""
import os
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8-sig").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        _key = _key.strip().removeprefix("export ").strip()
        _val = _val.strip().strip("'\"")
        if _key and _val and _key not in os.environ:
            os.environ[_key] = _val
