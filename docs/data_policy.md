# Data policy

Runtime reads the named local PDFs and report files. It uses no APIs, remote inference, telemetry, persistent cache or training. It writes report content to stdout on request. Redirected JSON and CSV contain document-derived values and, in extraction exports, verbatim evidence. Store private inputs and exports outside synced folders and shared repositories. Evidence is page text as read by the parser and should be checked against the rendered PDF in a consequential decision.

`data/synthetic-v1.json` contains fictional proposals authored for this repository. `data/gold-v1.json` contains separately specified values, page and line references, and comparison annotations. Generated pages with text carry a prominent SYNTHETIC heading. The deliberately blank page in the mixed PDF exercises partial ingestion. Fixtures require no external data or redistribution permission. The repository license covers both checked-in fixture manifests. The generator is deterministic without random sampling.

The parser receives PDF bytes through a process pipe without creating scratch PDFs. The evaluation generator writes temporary synthetic PDFs and the harness cleans up its temporary directory. Generated fixtures and benchmark files use atomic replacement and remove staging files on handled failures. Local file paths and remote folder synchronization are controlled by the operator. Explicit UNC and device namespaces are rejected on Windows. Mapped drives and OS-level synchronization remain outside the CLI's control.

For sensitive corrections, provide the value and reason over stdin to keep them out of process arguments. The invoking shell or application still controls its own history, logs and storage. Reports and exports contain private data if their inputs do.

Git excludes PDFs, CSV, output directories and JSON by default, with named exceptions for the synthetic data and benchmark. Git ignores reduce accidental commits. Source files, text files and forced additions still require review for private data.
