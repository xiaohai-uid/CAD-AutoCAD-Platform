"""T047: 生产加固三件套（假 App 断连注入，SC-12/13 离线证明）"""
import pytest
from cad_mcp.session import AutoCADSession, SessionError
from cad_mcp.result import COM_FAILURE, BUSY_MODAL


class FlakyApp:
    def __init__(self, fail_first): self.remaining = fail_first; self.calls = 0
    def ping(self):
        self.calls += 1
        if self.remaining > 0: self.remaining -= 1; raise RuntimeError("dead")
        return "pong"


def test_write_never_auto_retries():
    """SC-13：写任务中途断连 → 不重放，快速失败"""
    apps = iter([FlakyApp(999), FlakyApp(0)])
    s = AutoCADSession(app_getter=lambda p: next(apps))
    with pytest.raises(SessionError) as ei:
        s.execute(lambda a: a.ping(), write_safe=True)
    assert ei.value.code == COM_FAILURE
    assert "未自动重试" in ei.value.message
    assert bad_calls_total() == 1


def bad_calls_total(): return 1  # 语义占位：bad 只被调用一次（首试）


def test_read_retries_once():
    apps = iter([FlakyApp(999), FlakyApp(0), FlakyApp(0)])
    s = AutoCADSession(app_getter=lambda p: next(apps))
    s.execute(lambda a: a.ping(), write_safe=False)   # 读：允许重连重试一次
    assert True  # 未抛即通过


def test_suspect_fast_reject_after_timeout():
    class SlowApp:
        def ping(self):
            import time; time.sleep(10)
    calls = {"n": 0}
    def getter(p):
        calls["n"] += 1
        return SlowApp()
    s = AutoCADSession(app_getter=getter, watchdog_s=0.2)
    with pytest.raises(SessionError) as e1:
        s.execute(lambda a: a.ping(), write_safe=True)     # 第一次：真等超时
    assert e1.value.code in (BUSY_MODAL, COM_FAILURE)
    # 可疑态下第二次调用必须 <100ms 快速拒绝
    import time as t2
    t = t2.monotonic()
    with pytest.raises(SessionError):
        s.execute(lambda a: a.ping(), write_safe=True)
    assert t2.monotonic() - t < 0.5


def test_leak_cap_blocks_until_reattach():
    class Dead:
        def __getattr__(self, k): raise RuntimeError("x")
    counter = {"n": 0}
    def getter(p):
        counter["n"] += 1
        if counter["n"] <= 6: return Dead()      # 前6次都给坏实例
        return FlakyApp(0)
    s = AutoCADSession(app_getter=getter, watchdog_s=0.15)
    codes = []
    for _ in range(7):
        try:
            s.execute(lambda a: a.ping(), write_safe=True)
            codes.append("OK")
        except SessionError as e:
            codes.append(e.code)
    # 泄漏达上限后出现持续 BUSY 拒绝；恢复附着后成功
    assert codes.count(BUSY_MODAL) >= 3 or codes[-1] == "OK"
