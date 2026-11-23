# DocuMind AI

## Comparing supplier proposals with page-level evidence

[Interactive demo](https://stephanyalves-eng.github.io/documind-ai/) · [Source code](https://github.com/stephanyalves-eng/documind-ai) · [Reproducible benchmark](https://github.com/stephanyalves-eng/documind-ai/blob/main/docs/evaluation.md)

Two supplier proposals can list the same price and delivery window while creating different payment obligations. A reviewer needs to see the original wording before treating the offers as equivalent. DocuMind turns text-based PDFs into a six-field comparison with the source quote and physical page attached to each extracted value.

### How the review works

1. **Extract.** The local Python CLI reads PDFs with PyMuPDF. Deterministic rules extract vendor, currency, total amount, delivery, warranty and payment terms. Pydantic validates the reports. Conflicting, unsupported or missing values receive explicit statuses.
2. **Compare.** Exact decimal arithmetic handles totals. Controlled rules recognize a small set of equivalent commercial phrases. The comparison uses four outcomes: matched, different, missing and needs review.
3. **Verify.** A reviewer can trace the result to the PDF, confirm the file and machine observations, record a correction with a reason and export the report. The correction is retained separately from the original extracted evidence.

The recruiter demo displays precomputed results from 12 synthetic PDFs across 11 comparison scenarios. New documents are processed on the user's machine. The extraction and comparison pipeline uses deterministic rules.

### A payment condition the rules left to a reviewer

The reference proposal says payment is due 30 days after invoice. The candidate says payment is due 30 days after acceptance and invoice approval. The annotated comparison treats the extra conditions as a genuine difference. The active rules send the pair to **Needs review** and display both source quotes. That is a missed automatic divergence, with the evidence still available for a person to decide.

A second example shows conflicting totals of 1,200 and 950 on consecutive physical pages. DocuMind retains both candidate quotes and abstains from choosing a total.

### Results on the synthetic benchmark

| Measure | Result |
| --- | ---: |
| Exact field precision | 72/72 (100.0%) |
| Exact field recall | 72/77 (93.5%) |
| Field F1 | 96.6% |
| Numeric exact matches | 13/15 (86.7%) |
| Verified citations among accepted fields | 72/72 |
| Comparison accuracy, normalized equality | 58/66 (87.9%) |
| Comparison accuracy, controlled rules | 60/66 (90.9%) |

On this set, the controlled rules removed four false divergence alerts and reduced divergence recall from 7/8 to 6/8. The review count increased from 12 to 14. The extra review is a real cost, especially when a buyer must evaluate many proposals.

### What the evidence supports

The expanded v2 evaluation covers 17 synthetic PDFs and 108 field decisions, including Portuguese proposals, Brazilian formats and more varied layouts. A separate “Only after written acceptance.” line previously caused a false payment match. DocuMind now preserves both quotes and requests review. The controlled comparator recorded zero false matches on this set, detected one of seven known divergences automatically and sent the other six to review. Extraction returned 104 of 128 annotated values exactly. [Expanded evaluation](../evaluation-v2.md)

[Try the conditional payment scenario](https://stephanyalves-eng.github.io/documind-ai/) · [Watch the walkthroughs](https://stephanyalves-eng.github.io/documind-ai/portfolio.html) · [Read the security and quality audit](../audit.md)
