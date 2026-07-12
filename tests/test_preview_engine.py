from services.preview.engine import PreviewEngine


def test_screenshot_no_connection():
    engine = PreviewEngine()
    result = engine.screenshot("test_job", 1920, 1080, "png")
    assert result.success is False
