"""Export or verify the committed OpenAPI snapshot.

Usage:
    python scripts/export_openapi.py
    python scripts/export_openapi.py --check

The check mode is used in CI so contract changes are reviewed explicitly.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app

TARGET = ROOT / "specs/taskflow/contracts/openapi.json"


def serialized_spec() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    content = serialized_spec()

    if "--check" in sys.argv:
        if not TARGET.exists():
            print(f"Missing OpenAPI snapshot: {TARGET}")
            return 1
        if TARGET.read_text(encoding="utf-8") != content:
            print(f"OpenAPI snapshot is out of date: {TARGET}")
            print("Run: python scripts/export_openapi.py")
            return 1
        print("OpenAPI snapshot is up to date")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8")
    print(f"Wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
