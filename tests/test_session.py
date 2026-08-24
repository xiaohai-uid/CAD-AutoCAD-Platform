"""T007 配套：惰性重连恰好一次 + 错误分类（假 App 离线测试，宪法 III）"""
import pytest
from cad_mcp.session import AutoCADSession, SessionError
from cad_mcp.result import NOT_RUNNING, COM_FAILURE


class FlakyApp:
    """第一次调用抛错，之后正常——模拟实例被关后重开。"""
    def __init__(self, fail_first=1):
        self.remaining = fail_first
        self.calls = 0
    def ping(self):
        self.calls += 1
        if self.remaining > 0:
            self.remaining -= 1
            raise RuntimeError("RPC 服务器不可用")
        return "pong"


def test_lazy_reconnect_retry_exactly_once():
    bad, good = FlakyApp(999), FlakyApp(0)   # bad 永远失败, good 正常
    apps = iter([bad, good])
    s = AutoCADSession(app_getter=lambda pid: next(apps))
    s.execute(lambda app: app.ping(), write_safe=False)         # 首次附着 bad → 失败 → 重连 good → 成功
    assert good.calls == 1 and bad.calls == 1  # 恰好各一次：无第三次尝试


def test_double_failure_maps_to_com_failure():
    apps = iter([FlakyApp(999), FlakyApp(999)])
    s = AutoCADSession(app_getter=lambda pid: next(apps))
    with pytest.raises(SessionError) as ei:
        s.execute(lambda app: app.ping())
    assert ei.value.code == COM_FAILURE


def test_attach_failure_is_not_running():
    def no_cad(pid):
        raise RuntimeError("操作超时")
    s = AutoCADSession(app_getter=no_cad)
    with pytest.raises(SessionError) as ei:
        s.execute(lambda app: 1)
    assert ei.value.code == NOT_RUNNING


def test_status_not_running_shape():
    s = AutoCADSession(app_getter=lambda pid: (_ for _ in ()).throw(RuntimeError()))
    st = s.status()
    assert st == {"attached": False, "doc_name": None, "entity_count": None}
