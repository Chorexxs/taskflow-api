"""Upload content validation (SEC-3.4)."""

import pytest

from app.uploads import validate_file_signature


def test_accepts_valid_png():
    validate_file_signature(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, ".png")


def test_rejects_png_with_text_content():
    with pytest.raises(ValueError, match="does not match"):
        validate_file_signature(b"not a png", ".png")


def test_accepts_valid_pdf_and_zip_based_office_files():
    validate_file_signature(b"%PDF-1.7\n...", ".pdf")
    validate_file_signature(b"PK\x03\x04rest", ".docx")


def test_rejects_executables_regardless_of_extension():
    for data in (b"MZ\x90\x00", b"\x7fELF", b"#!/bin/sh\nrm -rf /"):
        with pytest.raises(ValueError, match="Executable"):
            validate_file_signature(data, ".txt")


def test_text_files_must_be_utf8_and_valid_json():
    validate_file_signature(b"hello\n", ".txt")
    with pytest.raises(ValueError, match="UTF-8"):
        validate_file_signature(b"\xff\xfe\xfd", ".csv")
    with pytest.raises(ValueError, match="JSON"):
        validate_file_signature(b"{not json", ".json")
    validate_file_signature(b'{"ok": true}', ".json")
