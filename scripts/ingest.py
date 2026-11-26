"""Archive one source delivery and extract addressable pages using local tools."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


class ExtractionError(Exception):
    """Stable reason recorded in the delivery manifest."""


def run_tool(args):
    try:
        result = subprocess.run(args, capture_output=True, timeout=60,
                                env={**os.environ, "LC_ALL": "C"})
    except FileNotFoundError as error:
        raise ExtractionError(f"{args[0]}_unavailable") from error
    except subprocess.TimeoutExpired as error:
        raise ExtractionError(f"{args[0]}_timeout") from error
    if result.returncode:
        raise ExtractionError(f"{args[0]}_failed")
    return result.stdout


def store_page(root, number, text, status):
    path = f"pages/{number:06}.txt"
    raw = text.encode("utf-8")
    (root / path).write_bytes(raw)
    return {"page": number, "status": status, "text_path": path,
            "byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def pdf_pages(raw, root):
    info = run_tool(["pdfinfo", str(raw)])
    count = re.search(rb"^Pages:\s+([1-9][0-9]*)\s*$", info, re.MULTILINE)
    if not count:
        raise ExtractionError("pdf_page_count_unavailable")
    pages = []
    for number in range(1, int(count[1]) + 1):
        try:
            output = run_tool(["pdftotext", "-f", str(number), "-l", str(number),
                               "-layout", "-nopgbrk", "-enc", "UTF-8", str(raw), "-"])
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
    return [store_page(root, i, page, "extracted" if page.strip() else "empty")
            for i, page in enumerate(text.split("\f"), start=1)]


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
        shutil.copyfile(source, raw)
        record = {"schema": 1, "format": kind, "original": {
            "path": raw.name, "byte_length": raw.stat().st_size, "sha256": digest(raw)},
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
        root.rename(destination)
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
