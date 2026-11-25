import unittest

from scripts.govinfo import inspect


GRANULE = "USCODE-2024-title26-subtitleF-chap79-sec7703"
SYNTHETIC = b"""United States Code, 2024 Edition
<!-- documentid:26_7703  currentthrough:20250106 -->
<!-- field-start:statute --><p>synthetic provision</p><!-- field-end:statute -->
<p>synthetic editorial note</p>
"""


class TestGovInfo(unittest.TestCase):
    def test_editorial_and_statutory_signals(self):
        baseline = inspect(GRANULE, SYNTHETIC)
        notes = inspect(GRANULE, SYNTHETIC.replace(b"editorial", b"new editorial"))
        provision = inspect(GRANULE, SYNTHETIC.replace(b"provision", b"changed provision"))
        self.assertNotEqual(baseline["sha256"], notes["sha256"])
        self.assertEqual(baseline["statute_html_sha256"], notes["statute_html_sha256"])
        self.assertNotEqual(baseline["statute_html_sha256"], provision["statute_html_sha256"])
        self.assertEqual(baseline["current_through"], "2025-01-06")

    def test_misidentified_delivery(self):
        for token in (b"2024 Edition", b"26_7703", b"field-end:statute", b"20250106"):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    inspect(GRANULE, SYNTHETIC.replace(token, b"wrong"))
