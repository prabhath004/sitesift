"""Export the FastAPI OpenAPI schema to docs/openapi.json.

The spec is a build artifact of the backend, and the frontend's types are a build
artifact of the spec. Checking both in means a contract change shows up as a diff
in review instead of as a runtime surprise.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402

if __name__ == "__main__":
    target = ROOT / "docs" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {target.relative_to(ROOT)}")
