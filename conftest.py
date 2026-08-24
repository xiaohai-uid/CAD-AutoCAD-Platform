import os, sys
# 让 Windows/WSL 任意 cwd 下 pytest 都能导入 src/cad_mcp
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
