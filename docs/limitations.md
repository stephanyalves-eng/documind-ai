# Limitations

- The release foundation handles simple labeled digital PDFs. Wrapped values, tables, columns, attachments, image scans, missing text mappings and unsupported languages can lead to abstentions or incorrect observations.
- The quote verifies extracted text at a physical page index. Explicit invisible text spans trigger review. Occlusion, same-color text, layer interactions and incorrect commercial scope may evade this check. Duplicate identical labels can reflect different line items or offers.
- Amounts support a narrow numeric syntax and currency allowlist. No VAT rounding tolerance, exchange rates, credits, price-break totals, business-day conversions or automatic discovery of alternate date formats are included.
- Clause matching is limited to plain English. Literal matches assume a shared interpretation. Controlled patterns assume comparable units and anchors, including an invoice date for a simple invoice clause. Additional clauses, priorities and calendar conventions can change interpretation.
- Required-field checks are separate from comparison. A syntactically extracted amount can still have an arithmetic issue that blocks comparison. A blank page is conservatively treated as unreadable.
- Review overrides record value and reason. Local JSON files can be edited, so the history does not authenticate reviewer identity or prove file integrity.
- The native parser runs in a separate process with a timeout and Linux CPU and address space bounds. It inherits the local user's permissions. Windows and macOS lack the per-process memory ceiling. Public processing of adversarial PDFs requires an OS sandbox that limits file and network access and enforces resource quotas.
- The benchmark covers an authored synthetic challenge set. Its timing is machine-specific and its scores do not estimate accuracy on supplier documents.
- The recruiter showcase displays precomputed synthetic results. Independent review and isolation for unattended PDF intake remain separate from the static portfolio release.
