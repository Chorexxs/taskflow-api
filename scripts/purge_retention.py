"""Purge expired notifications and activity logs (Q-08, T-098).

Usage:
    python scripts/purge_retention.py

Windows come from ``NOTIFICATION_RETENTION_DAYS`` (default 90) and
``ACTIVITY_RETENTION_DAYS`` (default 365). Safe to run repeatedly.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import get_db_context
from app.jobs import purge_expired_data


def main() -> int:
    with get_db_context() as db:
        counts = purge_expired_data(db)
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
