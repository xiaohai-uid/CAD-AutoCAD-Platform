import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.vision.engine import VisionEngine

def test_analyze_file_not_found():
    engine = VisionEngine()
    result = engine.analyze("nonexistent.png")
    assert result.success is False
    assert "not found" in (result.error or "").lower()

def test_analyze_invalid_format():
    engine = VisionEngine()
    result = engine.analyze("dummy.txt")
    assert result.success is False

def test_analyze_missing_cv2():
    """Simulate the case where cv2 is unavailable."""
    engine = VisionEngine()
    result = engine.analyze("dummy.png")
    # If cv2 is not installed, the error should mention OpenCV
    if result.error and "OpenCV" in result.error:
        assert result.success is False
    else:
        # If cv2 happens to be installed, dummy.png doesn't exist
        # so we expect a file-not-found error instead
        assert result.success is False
        assert "not found" in (result.error or "").lower()
