# Synthetic v2 evaluation

This diagnostic set measures the existing DocuMind extractor and comparators against **17 text-based synthetic PDFs, 18 annotated pairs and 108 field decisions**. The two v1 artifacts used by the recruiter showcase keep their original scope and results. See the [v1 report](evaluation.md).

## How to reproduce

```powershell
python -m scripts.generate_test_docs --dataset v2 --out outputs/evaluation-v2/fixtures
python -m scripts.evaluate --dataset v2 --output outputs/benchmark-v2.json
```

The [fixture manifest](../data/synthetic-v2.json) describes the PDF layouts and text. The [reference annotations](../data/gold-v2.json) include canonical values, one-based physical page numbers, exact evidence and the expected commercial relationship for each pair. The fixture author specified the reference answers separately from parser outputs. The harness verifies that each annotated evidence line appears on its stated page. A citation spread over multiple lines earns credit only when the extracted value is exact and its supplied evidence covers every annotated line on that page.

The set includes Brazilian Portuguese labels, prices such as `R$ 12.500,00`, dates in `DD/MM/YYYY` format, a table with labels and values in separate cells, two-column layouts, multipage offers and conditional clauses that change meaning. Cases also cover inconsistent arithmetic, ambiguous offer totals, cross-currency quotes and missing terms. A few pairs compare two variants directly. Many share one of two reference documents, which makes their decisions correlated.

## Captured results

Windows, CPython 3.12.10, PyMuPDF 2.1. For exact field metrics, an incorrect accepted value counts as a false positive and as a missed reference value when one exists. See the [benchmark JSON](benchmark-v2.json) for per-field scores, both confusion matrices, individual expected and observed decisions, input hashes and latency.

| Extraction metric | Result |
| --- | ---: |
| Exact field precision | 104/104 (100.0%) |
| Exact field recall | 104/128 (81.25%) |
| Field micro F1 | 89.7% |
| Numeric exact match | 21/30 (70.0%) |
| Citation accuracy on accepted fields | 104/104 (100.0%) |
| Required-field abstention | 17/102 (16.7%) |

| Comparison metric | Normalized equality | Controlled rules |
| --- | ---: | ---: |
| Status accuracy | 82/108 (75.9%) | 82/108 (75.9%) |
| Divergence precision | 4/7 (57.1%) | 1/1 (100.0%) |
| Divergence recall | 4/7 (57.1%) | 1/7 (14.3%) |
| Decisions sent to review | 9/108 (8.3%) | 12/108 (11.1%) |
| Known divergences incorrectly marked matched | 0 | 0 |

Controlled rules flagged one automatic divergence, an explicit currency change, and sent six genuine differences to review. The [pre-fix run](benchmark-v2-before-fix.json) captures the original false match. Both comparators now route that case to review, and the v1 counts and individual decisions reproduced exactly.

## What the cases exposed

| Finding | Evidence from the run |
| --- | --- |
| A continuation line can change a material term. | `en_wrapped_payment` adds “Only after written acceptance.” on the following line. The extractor retains both quotes with their page and returns `needs_review`. Both comparators carry that decision into the comparison against `en_reference`. |
| Locale support is the largest extraction gap in this set. | The seven Brazil-oriented fixtures yield 53 exact values out of 70 annotated. The all-Portuguese quote yields zero of its six required fields. Brazilian price and date formats also fail under recognized English labels. |
| Layout affects extraction even with familiar labels. | The separately positioned pricing table yields zero of six required fields. The labeled two-column layout and the two-page offer each yield all six exact values. |
| Several real differences still require review. | The localized increase in total price, the payment negation and the delivery holiday exception are routed to review by the active comparator. |

The continuation check covers recognizable condition markers on immediately following lines in the same page's extracted text order. Other multiline layouts can still hide a condition. Portuguese aliases and locale-aware amount and date parsing remain gaps. This benchmark uses authored templates and synthetic values, so its results apply to these fixtures.
