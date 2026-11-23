"use strict";

const demo = window.DOCUMIND;
const fields = {
  vendor: "Vendor",
  currency: "Currency",
  amount: "Total amount",
  delivery_term: "Delivery",
  warranty: "Warranty",
  payment_terms: "Payment terms",
};
const statuses = {
  matched: "Matched",
  different: "Different",
  missing: "Missing",
  needs_review: "Needs review",
};
const reasons = {
  normalized_equality: "The normalized values are equal.",
  normalized_inequality: "The normalized values differ.",
  equivalent_controlled_clause: "The wording fits a known equivalence rule.",
  different_controlled_clause: "The supported durations or conditions differ.",
  missing_on_one_or_both_sides: "A supported label is missing from one or both proposals.",
  unresolved_input: "A document or field validation issue needs review.",
  unresolved_currency: "Confirm the currency before comparing the amounts.",
  cross_currency_amount: "The proposals use different currencies. Review the amounts in context.",
  unsupported_clause_relationship: "The rules cannot resolve the relationship between these clauses.",
};

function element(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  if (className) node.className = className;
  return node;
}

function badge(status) {
  return element("span", statuses[status], "pill " + status);
}

const scenario = document.getElementById("scenario");
const evidenceField = document.getElementById("evidence-field");
const tabButtons = Array.from(document.querySelectorAll("[data-view]"));
let currentCase = "conditional";
let currentField = "payment_terms";

function view(name, moveFocus = false) {
  for (const button of tabButtons) {
    const active = button.dataset.view === name;
    button.setAttribute("aria-pressed", String(active));
    document.getElementById(button.dataset.view).hidden = !active;
    if (moveFocus && active) button.focus();
  }
  document.getElementById("pair-controls").hidden = name === "benchmark";
  if (name === "evidence") renderEvidence();
}

function cellText(value) {
  return value === null ? "No value" : value;
}

function tableWithHeadings(headings) {
  const table = element("table");
  const header = table.createTHead().insertRow();
  for (const title of headings) {
    const cell = element("th", title);
    cell.scope = "col";
    header.append(cell);
  }
  table.createTBody();
  return table;
}

function renderStatuses(rows) {
  const cards = Object.keys(statuses).map((status) => {
    const card = element("div", undefined, "metric " + status);
    const dot = element("span", undefined, "indicator");
    dot.setAttribute("aria-hidden", "true");
    const count = rows.filter((row) => row.status === status).length;
    card.append(dot, element("b", count), element("span", statuses[status]));
    return card;
  });
  document.getElementById("status-cards").replaceChildren(...cards);
}

function renderTable(rows) {
  const table = tableWithHeadings(["Field", "Reference", "Candidate", "Decision"]);
  for (const row of rows) {
    const tr = table.tBodies[0].insertRow();
    const select = element("button", fields[row.field], "field-button");
    select.type = "button";
    select.dataset.field = row.field;
    select.addEventListener("click", () => selectField(row.field));
    tr.insertCell().append(select);
    tr.insertCell().textContent = cellText(row.left_value);
    tr.insertCell().textContent = cellText(row.right_value);
    tr.insertCell().append(badge(row.status));
  }
  document.getElementById("comparison-table").replaceChildren(table);
}

function addQuotes(container, docId, title, all = false) {
  const evidence = demo.documents[docId].fields[currentField].evidence;
  if (!evidence.length) {
    const quote = element("div", undefined, "quote");
    quote.append(element("p", title, "quote-label"), element("p", "No citation was extracted."));
    container.append(quote);
    return;
  }
  for (const item of all ? evidence : evidence.slice(0, 2)) {
    const quote = element("div", undefined, "quote");
    quote.append(
      element("p", title + " · Page " + item.source_page, "quote-label"),
      element("p", item.evidence_text)
    );
    container.append(quote);
  }
}

function renderInspector() {
  const row = demo.comparisons[currentCase].find((item) => item.field === currentField);
  const container = document.getElementById("inspector");
  document.getElementById("inspector-title").textContent = fields[currentField];
  container.replaceChildren(
    badge(row.status),
    element("p", reasons[row.reason] || "Check the values and original pages.", "decision-note")
  );
  addQuotes(container, "standard", "Reference");
  addQuotes(container, currentCase, "Candidate");
}

function sourceCard(docId, title) {
  const doc = demo.documents[docId];
  const evidence = doc.fields[currentField].evidence;
  const card = element("article", undefined, "card");
  const heading = element("header", undefined, "card-heading");
  heading.append(element("h2", title), element("p", docId === "standard" ? "Standard proposal" : demo.cases[docId]));
  const body = element("div", undefined, "document-body");
  const pageNumbers = [...new Set(evidence.map((item) => item.source_page))];
  if (!pageNumbers.length) {
    body.append(element("p", "This field has no cited page.", "decision-note"));
  }
  for (const page of pageNumbers) {
    body.append(element("h3", "Page " + page + " · Extracted PDF text"));
    const pageBody = element("div", undefined, "document-page");
    for (const line of doc.pages[page - 1].split("\n").filter((line) => line.trim())) {
      const matches = evidence.some((item) => item.source_page === page && item.evidence_text === line);
      pageBody.append(element("p", line, matches ? "highlight" : undefined));
    }
    body.append(pageBody);
  }
  for (const issue of doc.issues.filter((item) => item.code !== "required_field" && item.fields.includes(currentField))) {
    body.append(element("p", "Validation: " + issue.detail, "decision-note"));
  }
  const download = element("a", "Download synthetic PDF", "button secondary");
  download.href = "examples/" + docId + ".pdf";
  download.download = docId + ".pdf";
  body.append(download);
  card.append(heading, body);
  return card;
}

function renderEvidence() {
  document.getElementById("page-evidence").replaceChildren(
    sourceCard("standard", "Reference proposal"), sourceCard(currentCase, "Candidate proposal")
  );
}

function selectField(key) {
  currentField = key;
  evidenceField.value = key;
  for (const button of document.querySelectorAll("[data-field]")) {
    const selected = button.dataset.field === key;
    button.setAttribute("aria-pressed", String(selected));
    button.closest("tr").classList.toggle("is-selected", selected);
  }
  renderInspector();
  if (!document.getElementById("evidence").hidden) renderEvidence();
}

function selectCase(key) {
  currentCase = key;
  const rows = demo.comparisons[key];
  document.getElementById("json-download").href = "examples/" + key + ".json";
  renderStatuses(rows);
  renderTable(rows);
  const flag = rows.find((item) => item.status !== "matched");
  selectField(flag ? flag.field : "payment_terms");
  document.getElementById("live-status").textContent = demo.cases[key] + " loaded.";
}

function percent(value) {
  return value === null ? "Unavailable" : (value * 100).toFixed(1) + "%";
}

function renderEvaluation() {
  const { extraction, comparison } = demo.benchmark;
  const heading = document.querySelector("#benchmark .section-top p");
  heading.textContent = "Results from " + demo.benchmark.documents + " generated PDFs and " +
    demo.benchmark.pairs + " annotated comparison pairs.";
  const cards = element("div", undefined, "eval-cards");
  for (const [value, label] of [
    [percent(extraction.micro.f1), "Field F1"],
    [extraction.counts.numeric_correct + "/" + extraction.counts.numeric_gold, "Exact numeric matches"],
    [extraction.counts.citations_correct + "/" + extraction.counts.citations_predicted, "Verified accepted citations"],
  ]) {
    const card = element("div", undefined, "card");
    card.append(element("strong", value), element("p", label));
    cards.append(card);
  }
  const table = tableWithHeadings(["Comparator", "Status accuracy", "Divergence precision", "Divergence recall"]);
  for (const [key, label] of [["strict", "Normalized equality"], ["rules", "Controlled clause rules"]]) {
    const result = comparison[key];
    const row = table.tBodies[0].insertRow();
    for (const value of [label, percent(result.status_accuracy), percent(result.divergence.precision), percent(result.divergence.recall)]) {
      row.insertCell().textContent = value;
    }
  }
  const summary = element("div", undefined, "card");
  summary.append(
    table,
    element("p", "Controlled rules increased accuracy on these examples and routed more cases to review. The synthetic benchmark covers a narrow set of document layouts.", "eval-summary")
  );
  document.getElementById("evaluation").replaceChildren(cards, summary);
}

if (demo) {
  for (const [key, label] of Object.entries(demo.cases)) scenario.add(new Option(label, key));
  for (const [key, label] of Object.entries(fields)) evidenceField.add(new Option(label, key));
  scenario.value = currentCase;
  scenario.addEventListener("change", () => selectCase(scenario.value));
  evidenceField.addEventListener("change", () => selectField(evidenceField.value));
  for (const button of tabButtons) button.addEventListener("click", () => view(button.dataset.view));
  document.querySelector("[data-open-evidence]").addEventListener("click", () => view("evidence", true));
  selectCase(currentCase);
  renderEvaluation();
} else {
  document.getElementById("pair-controls").hidden = true;
  document.getElementById("workspace").append(element("p", "Demo data could not be loaded. Reload the page to try again.", "card noscript"));
}
