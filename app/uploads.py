"""Content validation for uploaded attachments (SEC-3.4).

The extension allowlist rejects dangerous names, but a client can rename any
payload. These checks ensure the bytes match the declared type and reject
executables regardless of the extension. Full antivirus scanning remains an
operational integration (see security-checklist.md).
"""

from __future__ import annotations

import json

ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
EXECUTABLE_SIGNATURES = (
    b"MZ",  # Windows PE
    b"\x7fELF",  # Linux ELF
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit
    b"\xca\xfe\xba\xbe",  # Mach-O universal
    b"#!",  # shebang scripts
)
TEXT_EXTENSIONS = {".txt", ".csv", ".json", ".md"}


def _normalize(extension: str) -> str:
    return extension.lower() if extension.startswith(".") else f".{extension.lower()}"


def _is_png(data: bytes) -> bool:
    return data.startswith(b"\x89PNG\r\n\x1a\n")


def _is_jpeg(data: bytes) -> bool:
    return data.startswith(b"\xff\xd8\xff")


def _is_gif(data: bytes) -> bool:
    return data.startswith((b"GIF87a", b"GIF89a"))


def _is_webp(data: bytes) -> bool:
    return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"


def _is_pdf(data: bytes) -> bool:
    # The PDF header may be preceded by up to 1024 bytes of junk.
    return b"%PDF-" in data[:1024]


def _is_zip(data: bytes) -> bool:
    return data.startswith(ZIP_SIGNATURES)


BINARY_CHECKS = {
    ".png": _is_png,
    ".jpg": _is_jpeg,
    ".jpeg": _is_jpeg,
    ".gif": _is_gif,
    ".webp": _is_webp,
    ".pdf": _is_pdf,
    ".zip": _is_zip,
    ".docx": _is_zip,
    ".xlsx": _is_zip,
    ".pptx": _is_zip,
}


def validate_file_signature(data: bytes, extension: str) -> None:
    """Validate the content against the declared extension.

    Raises:
        ValueError: If the content is an executable, is not valid UTF-8 text
            for a text extension, or does not match the binary signature.
    """
    normalized = _normalize(extension)

    if data.startswith(EXECUTABLE_SIGNATURES):
        raise ValueError("Executable content is not allowed")

    check = BINARY_CHECKS.get(normalized)
    if check is not None:
        if not check(data):
            raise ValueError(f"File content does not match the declared {normalized} type")
        return

    if normalized in TEXT_EXTENSIONS:
        if b"\x00" in data:
            raise ValueError("Binary content is not allowed for a text file")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must be valid UTF-8") from exc
        if normalized == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON file") from exc
        return
