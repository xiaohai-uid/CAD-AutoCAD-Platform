"""Configuration loader for CAD Direct Control Platform"""
from __future__ import annotations

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"

_config_cache: dict | None = None


def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    if not CONFIG_PATH.exists():
        _config_cache = _default_config()
        return _config_cache
    with open(CONFIG_PATH) as f:
        _config_cache = yaml.safe_load(f)
    return _config_cache


def _default_config() -> dict:
    return {
        "services": {
            "gateway": {"host": "127.0.0.1", "port": 8000},
            "intake": {"host": "127.0.0.1", "port": 8001},
            "vision": {"host": "127.0.0.1", "port": 8002},
            "cadplan": {"host": "127.0.0.1", "port": 8003},
            "validation": {"host": "127.0.0.1", "port": 8004},
            "cad_com": {"host": "127.0.0.1", "port": 8005},
            "preview": {"host": "127.0.0.1", "port": 8006},
            "dwg_scan": {"host": "127.0.0.1", "port": 8007},
            "artifacts": {"host": "127.0.0.1", "port": 8008},
        },
        "cad": {
            "default_unit": "mm",
            "com_timeout": 30,
            "com_progid": "AutoCAD.Application",
        },
        "output": {
            "dir": "D:/Projects/cad-direct-control-platform/output",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    }


def get_service_url(name: str) -> str:
    cfg = load_config()
    svc = cfg["services"][name]
    return f"http://{svc['host']}:{svc['port']}"
