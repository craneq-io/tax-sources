# CraneQ tax sources

This repository records the source bytes behind CraneQ rules. A manifest identifies one edition of one provision. Engine changes should pin the tax-sources commit, manifest path and statutory subdivision they implement.

## Public source registry

Use the [U.S. federal registry](registry/us-federal.json) to find the official publisher, publication series and update process. Each series has a stable ID. Follow its discovery URL for new releases and its repository-relative evidence paths or document snapshots for pinned editions.

The 2024 property-basis records follow § 1001 into §§ 1011, 1012, 1015 and 1016. The registry also pins the annual Treasury regulation on cost basis and the IRS Form 8949 filing materials for the same year. This gives reviewers a path from a rule about gain or loss to its basis inputs and the form used to report dispositions.

For an update, add a dated snapshot or manifest in a pull request, preserve the prior digest, and identify the changed provision or filing revision. Record the retrieval date in UTC and hash the original publisher bytes. Review effective dates, exceptions and transition language before using a source in an engine change. A discovery entry can exist before the first document is pinned.

## First source delivery

The first pair covers the **2023 and 2024 editions of 26 U.S.C. § 7703**, with subsection (a) as the engine review scope. Subsection (a) addresses when to determine marital status and the treatment of specified legal separation decrees. Its opening sentence limits where it applies. Subsection (b) has separate conditions. [2023 GovInfo section](https://www.govinfo.gov/content/pkg/USCODE-2023-title26/html/USCODE-2023-title26-subtitleF-chap79-sec7703.htm) · [2024 GovInfo section](https://www.govinfo.gov/content/pkg/USCODE-2024-title26/html/USCODE-2024-title26-subtitleF-chap79-sec7703.htm)

| GovInfo edition | Publisher's current-through date | Review record |
| --- | --- | --- |
| 2023 | 2024-01-03 | [2023 manifest](manifests/usc/26/7703/2023.json) |
| 2024 | 2025-01-06 | [2024 manifest](manifests/usc/26/7703/2024.json) |

These downloads have different whole-document checksums and identical bytes inside the statutory-body field. The changed bytes identify the edition, currency, page and a pagination comment inside an editorial note. This pair provides a control for update detection. A change to a note can still affect a review, even when the statutory body matches.

## Reproduce a delivery

From the repository root, run these commands with Python 3 in the project build environment. The verifier downloads each section directly from GovInfo unless given a local delivery file.

```sh
python3 -m unittest discover -s tests
python3 scripts/govinfo.py verify manifests/usc/26/7703/2023.json
python3 scripts/govinfo.py verify manifests/usc/26/7703/2024.json
python3 scripts/govinfo.py verify manifests/usc/26/7703/2024.json --file /path/to/section.htm
```

For a new delivery, retain the original bytes and the publisher's URL. Produce a candidate source record from a single GovInfo Code-section HTML file:

```sh
python3 scripts/govinfo.py inspect USCODE-2024-title26-subtitleF-chap79-sec7703 /path/to/section.htm
```

Record the output under `source`, enter the actual retrieval date, specify the review scope, and leave applicability pending until reviewed. Keep prior editions available. If a publisher replaces bytes under the same edition identifier, preserve the earlier manifest and add an explicitly named revision.

The first digest covers every downloaded byte. The second covers the exact bytes between GovInfo's statutory field markers, including headings, HTML and whitespace. A mismatch triggers comparison of the two documents. Review statutory text, source credits, amendment notes and effective-date or transition provisions. Record the affected citations and downstream rule IDs in the change. The verifier checks publisher-file identity, byte counts, hashes and extraction metadata. Legal applicability requires separate evidence and domain review.

## Authority and expansion

The Office of the Law Revision Counsel prepares the U.S. Code. GovInfo distributes the editions used here. The edition year, source currency date, retrieval date and a provision's applicability period each serve a different purpose. For the chosen subsection the manifests leave effective dates open. Review underlying public laws and their transition clauses before assigning a rule to tax years. [GovInfo collection guide](https://www.govinfo.gov/help/uscode) · [Statutes at Large](https://www.govinfo.gov/app/collection/statute)

The next intake adapter should accept official structured Title 26 releases, preserve their release identifiers and identify changed subdivisions. The same rule can then pin a passage across an edition boundary. Keep regulations and agency guidance as separately identified source types with their own publication and applicability metadata. [House U.S. Code downloads](https://uscode.house.gov/download/download.shtml)

## Enacted amendment evidence

The [basic standard deduction source inventory](evidence/26-usc-63/README.md) traces Public Law 119-21 § 70102 from the prior Code text through the amended statute and the IRS's replacement of its original 2025 table.

## Ingest a PDF or text delivery

Use Python 3.8+ for UTF-8 text. PDF extraction also requires Poppler's `pdfinfo` and `pdftotext` executables on PATH. Run the command in an approved ingestion environment with the original delivery file and a new output directory.

```sh
python3 scripts/ingest.py /deliveries/enacted-law.pdf --output /archive/law-119-21
python3 scripts/ingest.py /deliveries/section.txt --output /archive/section-text
```

Use `--format pdf` or `--format text` when the filename has another extension. A delivery contains `manifest.json`, `original.pdf` or `original.txt`, and numbered files under `pages/`. The schema-1 manifest pins the original's byte length and SHA-256 and records the same fields for each extracted UTF-8 page. Paths are relative to the manifest directory. Pair the original digest with the one-based page number to identify a passage's source page. Link the delivery to its publisher, edition, citation and applicability review separately.

PDF page numbers follow physical order. Poppler extracts the existing text layer with layout preservation. A page yielding only whitespace is marked `ocr_needed`, including a genuinely blank PDF page. An image beside a text caption can still require visual review. The extractor performs no OCR. Text deliveries accept UTF-8 with an optional leading BOM. Form-feed characters separate logical pages, including empty trailing pages. Other text and line endings are preserved.

A nonempty text page has status `extracted`. Empty text pages have status `empty`. If every text page is empty, the delivery is also `empty`. A PDF page extraction error produces `extraction_failed` for that page while other pages remain available. A document-level error such as invalid text encoding, missing PDF metadata or an unavailable PDF reader produces an empty page list and a reason code. Delivery status prioritizes extraction errors, then pages needing OCR. Consumers should read each page status.

The CLI prints the manifest path. Exit 0 means extraction succeeded, exit 2 means the archived delivery needs review, and exit 1 means intake failed before publication. Argument errors also use exit 2 and print usage without a manifest path. Supply a new output directory for each delivery. Concurrent writers to a published delivery are refused. Extraction and hashing run locally and accept no taxpayer data in the examples.

Intake accepts regular files up to 64 MiB and up to 2,048 pages per delivery. Extracted text is limited to 4 MiB per page and 32 MiB per delivery. Each PDF tool invocation has a 60-second timeout within a shared three-minute document deadline. An oversized input fails before publication. Page-count and extraction limits are recorded in the archived delivery. Publication requires atomic exclusive directory rename on macOS or Linux. An existing destination, including an empty directory created by another writer, is preserved.

The optional real-PDF test uses the byte-pinned IRS Rev. Proc. 2025-32. In the project test environment, set `CRANEQ_RP_25_32_PDF` to a previously downloaded copy and run the normal test suite with Poppler on PATH. It checks the official artifact digest and the extracted standard deduction figure. [Source inventory](evidence/26-usc-63/sources.json)

## Property disposition calculation

The [2024 § 1001 manifest](manifests/usc/26/1001/2024.json) anchors subsection (a). For a disposition with a single adjusted basis established for both gain and loss under § 1011, a positive excess of amount realized over that basis gives realized gain. The reverse excess gives realized loss. Equality gives neither. The caller establishes the disposition, amount realized, and applicable basis. Transactions with different gain and loss bases require separate treatment. Recognition, deductibility, character, rates and tax owed are outside this calculation. The edition's current-through date records publisher coverage. Applicability to an individual disposition requires separate review. [GovInfo, 26 U.S.C. § 1001(a)–(c)](https://www.govinfo.gov/content/pkg/USCODE-2024-title26/html/USCODE-2024-title26-subtitleA-chap1-subchapO-partI-sec1001.htm)
