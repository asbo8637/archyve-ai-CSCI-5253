import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for relative_path in ("packages/python-common", "apps/api", "apps/worker"):
    path = str(ROOT / relative_path)
    if path not in sys.path:
        sys.path.append(path)
