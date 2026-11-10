"""The integration suite must exercise the production database engine.

ADR-008: SQLite is only acceptable for quick, unit-only runs through the
documented ``TEST_USE_SQLITE=1`` escape hatch.
"""

import os

from sqlalchemy.engine import Engine


def test_integration_suite_uses_postgresql(database_engine: Engine):
    if os.environ.get("TEST_USE_SQLITE") == "1":
        return
    assert database_engine.dialect.name == "postgresql"
