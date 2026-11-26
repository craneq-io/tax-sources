# CraneQ tax sources

This repository records the source bytes behind CraneQ rules. A manifest identifies one edition of one provision. Engine changes should pin the tax-sources commit, manifest path and statutory subdivision they implement.

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
