"""Root conftest — adds src to path for test imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
