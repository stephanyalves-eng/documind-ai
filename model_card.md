# Extraction and matching card

**Version 0.1.2.** Deterministic rules with PyMuPDF for text acquisition and Pydantic for typed reports. There are no trainable weights or confidence scores.

**Intended use.** Assist a human comparing labeled supplier proposals with visible evidence. Inspect the underlying page and all validation issues before acting on commercial terms.

**Inputs and outputs.** Local PDFs. Physical page evidence, normalized field values, explicit abstentions, validation issues and comparison decisions. See [architecture](docs/architecture.md) for processing and [limitations](docs/limitations.md) for unsupported use.

**Data and splits.** No training data or training stage. Synthetic v1 is a frozen diagnostic set with versioned annotation and no randomized splits. Results and reproduction instructions are in the [evaluation report](docs/evaluation.md).

**Method decision.** Strict normalized equality is the comparison baseline. Controlled clause equivalence is the active comparator. Sentence-transformer weights were not downloaded or tested. Adoption requires evidence from a separately authored evaluation showing improvement over the active comparator, including false equivalence and review coverage.

**License.** [AGPL-3.0-only](LICENSE).
