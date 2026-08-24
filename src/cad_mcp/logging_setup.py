"""结构化日志（FR-17）：stderr 人话 + JSONL 轮转文件双通道。"""
from __future__ import annotations
import json
import logging
import logging.handlers
import os
import sys

_LOG_FIELDS = ("tool", "duration_ms", "ok", "code")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                   "level": record.levelname,
                   "msg": record.getMessage()}
        extra = {k: getattr(record, k) for k in _LOG_FIELDS if hasattr(record, k)}
        if extra:
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def setup(verbose: bool = False) -> logging.Logger:
    log_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~/tmp")),
                           "cad-mcp")
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger("cad-mcp")
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()

    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter(
        "%(asctime)s [cad-mcp] %(levelname)s %(name)s: %(message)s"))
    root.addHandler(sh)

    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "cad-mcp.jsonl"),
        maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(JsonFormatter())
    root.addHandler(fh)
    return root
