"""Configuration loader for CAD Direct Control Platform"""
from __future__ import annotations

import os
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
    with open(CONFIG_PATH, encoding="utf-8") as f:
        _config_cache = yaml.safe_load(f)
    # Expand output dir relative to project root
    output_dir = _config_cache.get("output", {}).get("dir", "./output")
    if not os.path.isabs(output_dir):
        output_dir = str(Path(CONFIG_PATH).parent.parent / output_dir)
    _config_cache.setdefault("output", {})["dir"] = output_dir
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
            "type": "AutoCAD",
            "default_unit": "mm",
            "com_timeout": 30,
            "com_progid": "AutoCAD.Application",
            "startup_wait_time": 3,
            "command_delay": 0.1,
            "valid_lineweights": [
                0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53,
                60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211,
            ],
        },
        "output": {
            "dir": "./output",
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


def get_cad_config() -> dict:
    """Return the CAD-specific configuration block."""
    return load_config().get("cad", {})


def get_output_dir() -> str:
    """Return the absolute output directory path."""
    return load_config().get("output", {}).get("dir", "./output")
