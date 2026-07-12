import sys
sys.path.insert(0, r"D:/Projects/cad-direct-control-platform")
from shared.models import JobStatus
print(JobStatus.completed.value)
