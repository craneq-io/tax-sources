import hashlib
import os
import sys
import time
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import ingest


def sample_pdf():
    """Small two-page PDF with a text layer on just the first physical page."""
    content = b"BT /F1 12 Tf 20 80 Td (Synthetic statute) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(b"%d 0 obj\n" % n + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 7\n0000000000 65535 f \n")
    for offset in offsets:
        data.extend(b"%010d 00000 n \n" % offset)
    data.extend(b"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref)
    return bytes(data)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / "out"

    def delivery(self, name, data):
        source = self.root / name
        source.write_bytes(data)
        record = ingest.ingest(source, self.out)
        self.assertEqual((self.out / record["original"]["path"]).read_bytes(), data)
        self.assertEqual(record["original"]["sha256"], hashlib.sha256(data).hexdigest())
        return record

    def test_utf8_pages_preserve_source_and_text_digests(self):
        record = self.delivery("example.txt", b"\xef\xbb\xbfArticle one\r\n\fArticle two")
        self.assertEqual(record["status"], "extracted")
        self.assertEqual([p["page"] for p in record["pages"]], [1, 2])
        for page, expected in zip(record["pages"], [b"Article one\r\n", b"Article two"]):
            self.assertEqual((self.out / page["text_path"]).read_bytes(), expected)
            self.assertEqual(page["sha256"], hashlib.sha256(expected).hexdigest())
        with self.assertRaises(FileExistsError):
            ingest.ingest(self.root / "example.txt", self.out)

    def test_invalid_text_keeps_evidence(self):
        record = self.delivery("example.txt", b"\xff")
        self.assertEqual((record["status"], record["reason"]), ("extraction_failed", "invalid_utf8"))

    def test_missing_pdf_tool_keeps_evidence(self):
        with patch("scripts.ingest.subprocess.Popen", side_effect=FileNotFoundError):
            record = self.delivery("example.pdf", sample_pdf())
        self.assertEqual(record["reason"], "pdfinfo_unavailable")

    @unittest.skipUnless(shutil.which("pdfinfo") and shutil.which("pdftotext"), "requires Poppler")
    def test_mixed_pdf(self):
        record = self.delivery("example.pdf", sample_pdf())
        self.assertEqual(record["status"], "ocr_needed")
        first, second = record["pages"]
        self.assertIn("Synthetic statute", (self.out / first["text_path"]).read_text())
        self.assertEqual((second["page"], second["status"]), (2, "ocr_needed"))

    def test_input_limit_leaves_no_destination(self):
        with patch.object(ingest, "MAX_INPUT_BYTES", 3), self.assertRaises(ValueError):
            self.delivery("test.txt", b"1234")
        self.assertFalse(self.out.exists())

    def test_page_limit_retains_original(self):
        with patch.object(ingest, "MAX_PAGES", 1):
            record = self.delivery("test.txt", b"A\fB")
        self.assertEqual(record["reason"], "page_count_limit")

    def test_pdf_page_limit_before_extraction(self):
        with patch.object(ingest, "run_tool", return_value=b"Pages: 999999\n") as run:
            record = self.delivery("test.pdf", sample_pdf())
        self.assertEqual(record["reason"], "page_count_limit")
        self.assertEqual(run.call_count, 1)

    def test_subprocess_output_limit(self):
        with self.assertRaisesRegex(ingest.ExtractionError, "extracted_output_limit"):
            ingest.run_tool([sys.executable, "-c", "print('x' * 100000)"], 100, time.monotonic() + 10)

    def test_publication_race_preserves_empty_destination(self):
        source = self.root / "input.txt"
        source.write_bytes(b"Source")
        publish = ingest.publish
        def race(staging, destination):
            destination.mkdir()
            inode = destination.stat().st_ino
            try:
                publish(staging, destination)
            finally:
                self.assertEqual(destination.stat().st_ino, inode)
        with patch.object(ingest, "publish", side_effect=race), self.assertRaises(FileExistsError):
            ingest.ingest(source, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    @unittest.skipUnless(os.environ.get("CRANEQ_RP_25_32_PDF") and shutil.which("pdfinfo") and
                         shutil.which("pdftotext"), "requires the pinned IRS PDF and Poppler")
    def test_pinned_revenue_procedure(self):
        raw = Path(os.environ["CRANEQ_RP_25_32_PDF"]).read_bytes()
        expected = "e9ada115fb43a4af5ea326ca91edd40ab0bf29b9be01d2c13d7b8fa96214635b"
        self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
        record = self.delivery("official.pdf", raw)
        self.assertFalse(any(page["status"] == "extraction_failed" for page in record["pages"]))
        self.assertTrue(any("$15,750" in (self.out / page["text_path"]).read_text()
                            for page in record["pages"]))
