import sys
from pathlib import Path

# Run the tests without installing the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
