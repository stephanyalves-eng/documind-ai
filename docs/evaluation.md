# Synthetic v1 evaluation

Run `python -m scripts.evaluate --output outputs/benchmark.json` from the repository root. The harness regenerates the PDFs locally and compares results against the checked-in annotations. The [captured run](benchmark.json) includes exact counts, per-field decisions, a confusion matrix for each comparator, package versions, all PDF and annotation hashes, and timing samples.

## Protocol

The challenge set contains 12 original synthetic PDFs and 11 annotated proposal pairs, each comparing one variant with the same standard proposal. Values, source pages and comparison outcomes are specified independently of the extraction rules. A human-readable value can appear in the reference even if the implementation lacks the syntax or currency support to extract it. Comparison annotations reflect the commercial relation when specified and the expected review states for scenarios such as cross-currency amounts and contradictory totals. The set was authored alongside the baseline and is a diagnostic benchmark. Shared documents and repeated templates make its cases correlated.

- **Field micro precision, recall and F1** aggregate exact canonical values across all ten fields. An incorrect accepted value contributes a false positive and a false negative when a reference value exists. Missing annotations represent slots without a unique reference value.
- **Numeric exact match** counts expected amount, subtotal and tax slots with the exact canonical Decimal string. Abstentions on annotated numeric fields count as misses.
- **Citation accuracy** uses all accepted fields as the denominator. A correct citation requires the exact value, at least one annotated page and quote, and verification that every emitted evidence line occurs verbatim on its claimed physical page.
- **Extraction abstention** counts missing or needs-review observations among the six required fields. **Comparison abstention** counts needs-review decisions among all six-field comparisons.
- **Divergence precision and recall** treat `different` as the positive class. A genuine difference routed to review is a false negative. Status accuracy treats all four comparison statuses as distinct.
- **Latency** measures sequential reading and extraction, including parser subprocess startup for each PDF. It excludes fixture generation, parent CLI startup and comparison. The run reports per-file samples, median and range. Undefined ratios are emitted as JSON null.

## Captured results

Windows, CPython 3.12.10, PyMuPDF 2.1. All results are from synthetic fixtures.

| Extraction metric | Result |
|---|---:|
| Exact field precision | 72/72 (100.0%) |
| Exact field recall | 72/77 (93.5%) |
| Field micro F1 | 96.6% |
| Numeric exact match | 13/15 (86.7%) |
| Citation accuracy on accepted fields | 72/72 (100.0%) |
| Required-field abstention | 8/72 (11.1%) |

| Comparison metric | Normalized equality | Controlled rules |
|---|---:|---:|
| Status accuracy | 58/66 (87.9%) | 60/66 (90.9%) |
| Divergence precision | 7/11 (63.6%) | 6/6 (100.0%) |
| Divergence recall | 7/8 (87.5%) | 6/8 (75.0%) |
| Review rate | 12/66 (18.2%) | 14/66 (21.2%) |

The five extraction misses were three unlabeled fields, one unsupported currency and one locale-formatted amount. Controlled equivalence corrected three false differences in simple delivery, warranty and payment clauses. It routed both an equivalent free-form payment clause and a genuinely different payment clause with extra conditions to review. The unsupported currency difference also remained unresolved. These outcomes show the coverage cost of the conservative match rules.

The fixture set contains too few independent layouts and policy variants to estimate operational accuracy. It includes no real supplier documents and no experiment with sentence-transformers. A future embedding comparison needs separately authored scenarios, especially clauses that differ in dates, amounts, conditions or negation despite similar wording.
