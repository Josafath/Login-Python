import sys
from pathlib import Path

# Allow `pytest` from the v2/ folder without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
