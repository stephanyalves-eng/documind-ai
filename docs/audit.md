# DocuMind security and quality audit

**Scope** · Prompt D, version 0.1.1, 2026-11-23. Reviewed the local CLI, PDF parser, report validation, exports and synthetic evaluation. Exercised the installed package on Windows and CPython 3.12.10 with synthetic input.

## Prioritized findings

| Priority | Finding | Change and verification |
|---|---|---|
| High | The previous PyMuPDF 1.28.2 pin predated two upstream security fixes. | Updated to PyMuPDF 2.1, pinned its dependency graph and verified that the worker refuses the previous version. The upstream fixes were released in 2.0. DocuMind calls text extraction and does not expose the upstream object-extraction or annotation-editing commands. |
| High | Native parsing previously ran in the CLI process. A malformed or expensive PDF could stop or stall the command. | Run the parser in a separate isolated-mode Python process. Pass bounded PDF bytes through stdin and discard native stderr. Enforce a 15-second deadline and add Linux ceilings of 10 CPU seconds and 512 MiB of address space. Existing tests cover invalid headers, structural damage, encrypted files, empty text and boundary limits. Regression tests cover timeout and abnormal worker exit. |
| High | A previously saved JSON report could be compared without indicating that its machine evidence had not been rechecked. | Comparison exports now carry `machine_evidence`. Optional `--source-pdfs` rechecks the source hashes and machine observations and rejects mismatches. Manual corrections retain their own attribution. Tests cover checked and unchecked comparisons, wrong PDFs and changed page references. |
| Medium | Invisible text could become an extraction candidate, and generic Unicode line splitting could promote an embedded separator into a field boundary. | Pages with explicit invisible text or zero-opacity text are unreadable and trigger review. Only parser newline boundaries create label candidates. Tests cover both invisibility indicators with controlled parser traces and check Unicode line handling. |
| Medium | An invalid supplied tax or subtotal could leave a total eligible for comparison when the other optional component was absent. Currency validation also accepted Unicode case normalization before checking the allowlist. | Flag unresolved arithmetic when any supplied component is invalid. Validate sums in a fixed Decimal context and require ASCII currency codes. Tests cover a partial invalid total and ambient Decimal precision. |
| Medium | Errors could echo unexpected command arguments, private corrections could appear in process arguments, and file checks differed between PDFs and reports. | Redact argument errors and add bounded correction input over stdin. Share regular-file checks for PDF and report reads and reject explicit UNC/device namespaces on Windows before a file probe. Tests check sanitized diagnostics, correction size and the Windows path guard. |
| Medium | Synthetic outputs were written directly to the final path. A failed write could leave a partial file and an existing link could change the write destination. | Validate fixture names before writing and stage generated PDFs and benchmark output beside their destination before atomic replacement. Test that simulated replacement failure preserves existing content and cleans staging. |

Upstream references cover the fixed dependency issues. [PyMuPDF releases](https://github.com/pymupdf/PyMuPDF/releases) · [CVE-2026-82035](https://github.com/advisories/GHSA-434w-92hw-f2m3) · [PyMuPDF issue 5112](https://github.com/pymupdf/PyMuPDF/issues/5112)

## Verification

All 64 local tests passed. The installed CLI exercised PDF extraction, correction through stdin, verification against the original PDF and source-checked CSV comparison. Ruff, formatting, Mypy and pip consistency checks passed. The PyPI advisory scan checked 43 pinned packages with zero skips and reported zero known vulnerabilities at the time of the run. It queried package names and versions. Documents remained local.

Reproduction from an activated compatible environment:

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pip check
python -m scripts.evaluate --output outputs/benchmark.json
pip-audit -r requirements.lock --disable-pip --no-deps --desc off
```

The rebuilt synthetic benchmark has 96.6% field F1, 13/15 numeric exact matches, 72/72 verified accepted citations and 60/66 correct decisions for the active comparator. The manifest and annotation hashes, extraction outcomes and comparison outcomes matched the foundation run. Generated PDF hashes were refreshed and reproduced within the audited environment. Median local read and extraction time was 326.849 ms, including subprocess startup. See the [captured benchmark](benchmark.json).

## Residual risks and release status

- **Block unattended public PDF intake.** The parser subprocess retains the account's permissions. It lacks a filesystem and network sandbox and has no per-worker memory ceiling on Windows or macOS. Verify Linux resource limits in hosted CI and use OS-level isolation before accepting adversarial uploads.
- **Review the rendered source before acting.** PDF layers, occlusion and ambiguous document structure can still make extracted text misleading. The verifier establishes agreement with the current parser and file bytes. It does not establish who authored the PDF or authenticate a manual correction history.
- **Treat exports as document data.** Local storage, shell logging and synchronization settings remain under operator control. The dependency advisory query is a point-in-time check of known package advisories.
- **Audit environment.** This audit used synthetic local files. The public static showcase and subsequent hosted quality checks are tracked by the [release workflow](https://github.com/stephanyalves-eng/documind-ai/actions/workflows/ci.yml).
