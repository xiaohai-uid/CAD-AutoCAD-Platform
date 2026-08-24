"""统一操作结果与错误码体系（宪法 IV / 契约公共约定）"""
from __future__ import annotations
from typing import Any

NOT_RUNNING = "NOT_RUNNING"
NO_DOCUMENT = "NO_DOCUMENT"
INVALID_PARAM = "INVALID_PARAM"
BUSY_MODAL = "BUSY_MODAL"
SAVE_CONFLICT = "SAVE_CONFLICT"
PARTIAL = "PARTIAL"
COM_FAILURE = "COM_FAILURE"
PATH_IN_USE = "PATH_IN_USE"
FILE_NOT_FOUND = "FILE_NOT_FOUND"
MISSING_DEP = "MISSING_DEP"
VALIDATION_FAILED = "VALIDATION_FAILED"

HINTS: dict[str, str] = {
    NOT_RUNNING: "请先启动 AutoCAD 并新建或打开一张图纸，然后重试",
    NO_DOCUMENT: "AutoCAD 已启动但无活动文档：请新建一张图纸（Ctrl+N）后重试",
    INVALID_PARAM: "请修正参数后重试；错误信息中已指明非法字段",
    BUSY_MODAL: "请检查 AutoCAD 是否有未关闭的对话框或正在进行的命令，处理后重试",
    SAVE_CONFLICT: "目标文件已存在：确认要覆盖时带 overwrite=true 重试",
    PARTIAL: "部分图元创建失败：见 items 中逐项原因；成功部分已保留并计入撤销日志",
    COM_FAILURE: "AutoCAD 接口调用异常：请保存工作后重试；反复出现请重启 AutoCAD",
    PATH_IN_USE: "目标文件正被本会话内另一文档标签占用：请换一个文件名，或先在 AutoCAD 中关闭该标签",
    FILE_NOT_FOUND: "文件不存在：请核对路径（支持 /mnt/X/... 形式）",
    MISSING_DEP: "缺少可选依赖：按提示安装后重试",
    VALIDATION_FAILED: "计划校验存在 error 级问题：见 issues 清单修正后重新执行",
}


def ok(message: str, handles: list[str] | None = None,
       data: dict[str, Any] | None = None) -> dict[str, Any]:
    r: dict[str, Any] = {"ok": True, "message": message}
    if handles is not None:
        r["handles"] = handles
    if data is not None:
        r["data"] = data
    return r


def fail(code: str, message: str, hint: str | None = None) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message,
                                   "hint": hint or HINTS.get(code, "请联系开发者补充指引")}}


def partial(created_handles: list[str], items: list[dict[str, Any]],
            message: str) -> dict[str, Any]:
    """尽力而为语义（Q2 决议）：成功保留+逐项成败；整体 ok=False 但句柄仍返回。"""
    r = fail(PARTIAL, message)
    r["handles"] = list(created_handles)
    r["items"] = items
    return r
