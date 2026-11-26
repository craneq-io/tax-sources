"""Archive one source delivery and extract addressable pages using local tools."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import tempfile
import time


MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_PAGES = 2048
MAX_PAGE_BYTES = 4 * 1024 * 1024
MAX_TEXT_BYTES = 32 * 1024 * 1024
PDF_SECONDS = 180


def copy_original(source, target):
    result = hashlib.sha256()
    size = 0
    with os.fdopen(os.open(source, os.O_RDONLY | os.O_NONBLOCK), "rb") as stream, target.open("xb") as output:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT_BYTES:
            raise ValueError("source must be a regular file within the input size limit")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            if size > MAX_INPUT_BYTES:
                raise ValueError("source exceeded the input size limit during copy")
            output.write(chunk)
            result.update(chunk)
    return {"path": target.name, "byte_length": size, "sha256": result.hexdigest()}


def publish(root, destination):
    # Ordinary POSIX rename can silently replace an existing empty directory.
    # Use the kernel's atomic exclusive rename or fail closed.
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(os.fsencode(root), os.fsencode(destination), 0x4)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        result = libc.renameat2(-100, os.fsencode(root), -100, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    else:
        raise OSError("an atomic exclusive rename is required to publish deliveries")
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


class ExtractionError(Exception):
    """Stable reason recorded in the delivery manifest."""


def run_tool(args, limit, deadline):
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                env={**os.environ, "LC_ALL": "C"})
    except FileNotFoundError as error:
        raise ExtractionError(f"{args[0]}_unavailable") from error
    data = bytearray()
    deadline = min(deadline, time.monotonic() + 60)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise ExtractionError(f"{args[0]}_timeout")
                chunk = os.read(proc.stdout.fileno(), min(65536, limit - len(data) + 1))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > limit:
                    raise ExtractionError("extracted_output_limit")
        if proc.wait(timeout=max(0, deadline - time.monotonic())):
            raise ExtractionError(f"{args[0]}_failed")
    except subprocess.TimeoutExpired as error:
        raise ExtractionError(f"{args[0]}_timeout") from error
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()
    return bytes(data)


def store_page(root, number, text, status):
    path = f"pages/{number:06}.txt"
    raw = text.encode("utf-8")
    (root / path).write_bytes(raw)
    return {"page": number, "status": status, "text_path": path,
            "byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def pdf_pages(raw, root):
    deadline = time.monotonic() + PDF_SECONDS
    info = run_tool(["pdfinfo", str(raw)], 1024 * 1024, deadline)
    count = re.search(rb"^Pages:\s+([1-9][0-9]*)\s*$", info, re.MULTILINE)
    if not count:
        raise ExtractionError("pdf_page_count_unavailable")
    if len(count[1]) > len(str(MAX_PAGES)) or int(count[1]) > MAX_PAGES:
        raise ExtractionError("page_count_limit")
    pages = []
    available = MAX_TEXT_BYTES
    for number in range(1, int(count[1]) + 1):
        try:
            if available == 0:
                raise ExtractionError("extracted_output_limit")
            if time.monotonic() >= deadline:
                raise ExtractionError("document_timeout")
            output = run_tool(["pdftotext", "-f", str(number), "-l", str(number),
                               "-layout", "-nopgbrk", "-enc", "UTF-8", str(raw), "-"],
                              min(MAX_PAGE_BYTES, available), deadline)
            available -= len(output)
            text = output.decode("utf-8")
            pages.append(store_page(root, number, text, "extracted" if text.strip() else "ocr_needed"))
        except (ExtractionError, UnicodeDecodeError) as error:
            pages.append({"page": number, "status": "extraction_failed",
                          "reason": str(error) if isinstance(error, ExtractionError) else "invalid_utf8"})
    return pages


def text_pages(raw, root):
    try:
        text = raw.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ExtractionError("invalid_utf8") from error
    if text.count("\f") + 1 > MAX_PAGES:
        raise ExtractionError("page_count_limit")
    if raw.stat().st_size > MAX_TEXT_BYTES:
        raise ExtractionError("extracted_output_limit")
    pages = text.split("\f")
    if any(len(page.encode("utf-8")) > MAX_PAGE_BYTES for page in pages):
        raise ExtractionError("extracted_output_limit")
    return [store_page(root, i, page, "extracted" if page.strip() else "empty")
            for i, page in enumerate(pages, start=1)]


def ingest(source, destination, kind=None):
    kind = kind or {".pdf": "pdf", ".txt": "text"}.get(source.suffix.lower())
    if kind not in {"pdf", "text"}:
        raise ValueError("choose --format pdf or text for an unrecognized extension")
    if destination.exists():
        raise FileExistsError(f"output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
        root = Path(staging) / "delivery"
        (root / "pages").mkdir(parents=True)
        raw = root / ("original.pdf" if kind == "pdf" else "original.txt")
        record = {"schema": 1, "format": kind, "original": copy_original(source, raw),
            "extractor": "poppler-pdftotext-layout" if kind == "pdf" else "utf8-form-feed",
            "pages": []}
        try:
            pages = pdf_pages(raw, root) if kind == "pdf" else text_pages(raw, root)
            record["pages"] = pages
            statuses = {page["status"] for page in pages}
            record["status"] = next((s for s in ("extraction_failed", "ocr_needed")
                                     if s in statuses), "empty" if statuses == {"empty"} else "extracted")
        except ExtractionError as error:
            record.update(status="extraction_failed", reason=str(error))
        (root / "manifest.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        publish(root, destination)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=["pdf", "text"])
    args = parser.parse_args()
    try:
        record = ingest(args.input, args.output, args.format)
    except (OSError, ValueError) as error:
        parser.exit(1, f"ingest: {error}\n")
    print(args.output / "manifest.json")
    return 0 if record["status"] == "extracted" else 2


if __name__ == "__main__":
    sys.exit(main())
