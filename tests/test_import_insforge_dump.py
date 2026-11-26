"""InsForge dump importer (T-131)."""

import gzip
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DUMP = """--
-- PostgreSQL database dump
--

COPY public.users (id, email) FROM stdin;
1\ta@example.com
2\tb@example.com
\\.

COPY public.tasks (id, title) FROM stdin;
7\tWrite the migration

\\.

COPY auth.users (id, email) FROM stdin;
9\towner@example.com
\\.

COPY storage.objects (bucket, key) FROM stdin;
taskflow-attachments\tattachments/1/file.txt
\\.

SELECT pg_catalog.setval('public.users_id_seq', 2, true);
SELECT pg_catalog.setval('auth.users_id_seq', 9, false);
"""


def _load_importer():
    spec = importlib.util.spec_from_file_location(
        "import_insforge_dump", ROOT / "scripts" / "import_insforge_dump.py"
    )
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules, so register it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


importer = _load_importer()


def test_parse_dump_keeps_only_the_requested_schema():
    contents = importer.parse_dump(DUMP)

    assert [block.table for block in contents.blocks] == ["public.users", "public.tasks"]
    assert "auth.users" in contents.skipped_tables
    assert "storage.objects" in contents.skipped_tables


def test_parse_dump_counts_rows_and_columns():
    contents = importer.parse_dump(DUMP)
    users = contents.blocks[0]

    assert users.columns == "id, email"
    assert users.row_count == 2


def test_parse_dump_handles_copy_without_column_list():
    contents = importer.parse_dump("COPY public.teams FROM stdin;\n1\tTeam\n\\.\n")

    assert contents.blocks[0].columns is None
    assert contents.blocks[0].row_count == 1


def test_parse_dump_only_keeps_sequences_of_the_schema():
    contents = importer.parse_dump(DUMP)

    assert contents.sequences == [("public.users_id_seq", 2, True)]


def test_read_dump_supports_gzip(tmp_path):
    dump = tmp_path / "dump.sql.gz"
    with gzip.open(dump, "wt", encoding="utf-8") as handle:
        handle.write(DUMP)

    assert "COPY public.users" in importer.read_dump(dump)


def test_read_dump_supports_plain_sql(tmp_path):
    dump = tmp_path / "dump.sql"
    dump.write_text(DUMP, encoding="utf-8")

    assert "COPY public.tasks" in importer.read_dump(dump)


def test_redact_url_hides_credentials():
    redacted = importer.redact_url("postgresql://user:secret@db.example.com:5432/taskflow")

    assert redacted == "postgresql://db.example.com:5432/taskflow"
    assert "secret" not in redacted
