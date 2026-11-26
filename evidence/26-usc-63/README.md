# Basic standard deduction amendment

This source inventory covers the change to 26 U.S.C. § 63(c)(7). The 2024 Code edition records the earlier text, including its sunset. The Office of the Law Revision Counsel's release through Public Law 119-120 records the amended text. That later release also incorporates unrelated legislation. Use the enacted law to attribute each change. [Pre-amendment Code](https://www.govinfo.gov/content/pkg/USCODE-2024-title26/html/USCODE-2024-title26-subtitleA-chap1-subchapB-partI-sec63.htm) · [Post-amendment Code](https://uscode.house.gov/us/usc/119-120/t26/s63/)

Congress enacted Public Law 119-21 on July 4, 2025. Section 70102(a) removes the sunset. Subsection (b) increases the base amounts and changes the inflation-adjustment years. Subsection (c) applies these amendments to taxable years beginning after December 31, 2024. A taxable year beginning January 1, 2025 therefore falls within the amendment even though it began before enactment. [Enacted law, § 70102, 139 Stat. 158–159](https://www.govinfo.gov/content/pkg/PLAW-119publ21/html/PLAW-119publ21.htm)

The following figures apply to an otherwise eligible unmarried individual outside the head-of-household and surviving-spouse categories. Filing status, elections, dependent limits, eligibility and additional deductions require separate determinations.

| Taxable year beginning in | Basic amount | Source and treatment |
| --- | ---: | --- |
| 2024 | $14,600 | [Rev. Proc. 2023-34 § 3.15(1)](https://www.irs.gov/pub/irs-drop/rp-23-34.pdf) |
| 2025, original publication | $15,000 | [Rev. Proc. 2024-40 § 2.15(1)](https://www.irs.gov/pub/irs-drop/rp-24-40.pdf), removed by Rev. Proc. 2025-32 § 3.01. Preserve only for historical comparison. |
| 2025, after amendment | $15,750 | [Rev. Proc. 2025-32 § 3.01](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf) |
| 2026 | $16,100 | [Rev. Proc. 2025-32 § 4.14(1)](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf) |

## Reproduce the source bytes

The inventory pins each official publication's URL, byte length and SHA-256 digest. Run the following from this directory using Bash, jq, curl and shasum. A publisher revision will fail verification and requires a fresh comparison against the prior inventory.

```bash
set -euo pipefail
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
while IFS=$'\t' read -r file url size digest; do
  curl --fail --silent --show-error --location "$url" --output "$tmp/$file"
  test "$(wc -c < "$tmp/$file")" -eq "$size"
  printf '%s  %s\n' "$digest" "$tmp/$file" | shasum -a 256 --check
done < <(jq -r '.sources[] | [.file, .url, .bytes, .sha256] | @tsv' sources.json)
```

The source comparison supports domain review and a future rule replay. The inventory records no determination of individual eligibility or approval of an engine rule.
