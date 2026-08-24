"""T015: 图层核心逻辑（假文档离线测试）"""
import pytest
from cad_mcp.layers import create_layer_core, ParamError


class FakeLayer:
    def __init__(self, name):
        self.Name = name; self.Color = 7
        self.Linetype = "Continuous"; self.LayerOn = True


class FakeLayers:
    def __init__(self): self.items = {}
    def Item(self, name):
        if name not in self.items: raise KeyError(name)
        return self.items[name]
    def Add(self, name):
        self.items[name] = FakeLayer(name)
        return self.items[name]
    def __iter__(self): return iter(self.items.values())
    def __len__(self): return len(self.items)


CATALOG = {"DASHED", "CENTER", "Continuous"}


class FakeLinetypes:
    def __init__(self): self.loaded = {"Continuous"}
    def Item(self, n):
        if n not in self.loaded: raise KeyError(n)
        return n
    def Load(self, n, f):
        # 模拟真实语义：文件合法但线型名不在目录中同样失败
        if f not in ("acad.lin", "acadiso.lin") or n not in CATALOG:
            raise OSError("not found")
        self.loaded.add(n)


class FakeDoc:
    def __init__(self):
        self.Layers = FakeLayers(); self.Linetypes = FakeLinetypes()


def test_create_new_layer_defaults():
    d = FakeDoc()
    assert create_layer_core(d, "中心线") is True
    assert d.Layers.items["中心线"].Name == "中心线"


def test_idempotent_returns_false():
    d = FakeDoc(); create_layer_core(d, "A")
    assert create_layer_core(d, "A") is False  # 已存在：不报错不重复建


def test_color_applied():
    d = FakeDoc(); create_layer_core(d, "红", color=1)
    assert d.Layers.items["红"].Color == 1


def test_linetype_load_from_fallback():
    d = FakeDoc()
    create_layer_core(d, "虚线层", linetype="DASHED")
    assert "DASHED" in d.Linetypes.loaded


def test_unknown_linetype_raises_paramerror():
    d = FakeDoc()  # Load 永远失败（文件不在 fallback 内的场景由实现控制）
    with pytest.raises(ParamError):
        create_layer_core(d, "X", linetype="NO_SUCH_LINE")
