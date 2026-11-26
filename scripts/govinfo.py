"""Fingerprint one edition-specific GovInfo U.S. Code section HTML granule."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen


def identity(granule):
    match = re.fullmatch(r"USCODE-([0-9]{4})-title([0-9]+)-([A-Za-z0-9-]+)-sec([0-9]+[a-z]*)", granule)
    if not match:
        raise ValueError("expected an edition-specific GovInfo section granule ID")
    return match.groups()


def source_url(granule):
    edition, title, _, _ = identity(granule)
    return f"https://www.govinfo.gov/content/pkg/USCODE-{edition}-title{title}/html/{granule}.htm"


def inspect(granule, raw):
    edition, title, _, section = identity(granule)
    if f"United States Code, {edition} Edition".encode() not in raw:
        raise ValueError("edition in the document differs from the granule ID")
    metadata = re.search(rb"<!-- documentid:(\S+)\s+[^>]*?currentthrough:(\d{8})\b", raw)
    if not metadata or metadata[1].decode() != f"{title}_{section}":
        raise ValueError("section identity or currency metadata missing or mismatched")
    stamp = metadata[2].decode()
    current_through = date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:]))
    start, end = b"<!-- field-start:statute -->", b"<!-- field-end:statute -->"
    if raw.count(start) != 1 or raw.count(end) != 1:
        raise ValueError("expected one statutory-body field")
    _, _, suffix = raw.partition(start)
    body, closed, _ = suffix.partition(end)
    if not closed or not body.strip():
        raise ValueError("empty or unclosed statutory-body field")
    return {
        "schema": 1,
        "granule_id": granule,
        "citation": f"{title} U.S.C. § {section}",
        "edition": int(edition),
        "publisher": "Office of the Law Revision Counsel, U.S. House of Representatives",
        "distributor": "U.S. Government Publishing Office (GovInfo)",
        "source_url": source_url(granule),
        "current_through": current_through.isoformat(),
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "statute_html_sha256": hashlib.sha256(body).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("inspect", help="emit candidate metadata for a supplied file")
    snapshot.add_argument("granule")
    snapshot.add_argument("file", type=Path)
    verify = commands.add_parser("verify", help="verify supplied bytes or download from GovInfo")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--file", type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        print(json.dumps(inspect(args.granule, args.file.read_bytes()), ensure_ascii=False, indent=2))
        return

    record = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected = record["source"]
    granule = expected["granule_id"]
    # Resolve the publisher URL from a constrained ID before any network request.
    url = source_url(granule)
    if args.file:
        raw = args.file.read_bytes()
    else:
        with urlopen(url, timeout=30) as response:
            raw = response.read()
    actual = inspect(granule, raw)
    if actual != expected:
        fields = sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        raise ValueError(f"{granule}: metadata mismatch in {', '.join(fields)}")
    date.fromisoformat(record["retrieved_on"])
    print(f"verified {granule} {actual['sha256']}")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError) as error:
        sys.exit(f"govinfo: {error}")
