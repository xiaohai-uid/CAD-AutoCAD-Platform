from services.artifacts.engine import ArtifactManager


def test_store_and_get():
    mgr = ArtifactManager()
    record = mgr.store("job1", {"dwg": "/path/to/job1.dwg"})
    assert record.job_id == "job1"
    assert record.files["dwg"] == "/path/to/job1.dwg"
    retrieved = mgr.get("job1")
    assert retrieved is not None

def test_get_nonexistent():
    mgr = ArtifactManager()
    result = mgr.get("nonexistent")
    assert result is None

def test_delete():
    mgr = ArtifactManager()
    mgr.store("job1", {"dwg": "/path/job1.dwg"})
    assert mgr.delete("job1") is True
    assert mgr.get("job1") is None
