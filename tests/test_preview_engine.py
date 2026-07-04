import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.preview.engine import PreviewEngine

def test_screenshot_no_connection():
    engine = PreviewEngine()
    result = engine.screenshot("test_job", 1920, 1080, "png")
    assert result.success is False
