import { registerProductSignalTools } from "./webmcp.js";

const elements = {
  channel: document.querySelector("#channel-filter"),
  platform: document.querySelector("#platform-filter"),
  exportButton: document.querySelector("#export-button"),
  activation: document.querySelector("#metric-activation"),
  conversion: document.querySelector("#metric-conversion"),
  retention: document.querySelector("#metric-retention"),
  lift: document.querySelector("#metric-lift"),
  activationNote: document.querySelector("#activation-note"),
  conversionNote: document.querySelector("#conversion-note"),
  retentionNote: document.querySelector("#retention-note"),
  liftNote: document.querySelector("#lift-note"),
  segmentLabel: document.querySelector("#segment-label"),
  funnel: document.querySelector("#funnel"),
  retentionBody: document.querySelector("#retention-table tbody"),
  decisionTitle: document.querySelector("#decision-title"),
  decisionCopy: document.querySelector("#decision-copy"),
  controlBar: document.querySelector("#control-bar"),
  treatmentBar: document.querySelector("#treatment-bar"),
  controlRate: document.querySelector("#control-rate"),
  treatmentRate: document.querySelector("#treatment-rate"),
  absoluteLift: document.querySelector("#absolute-lift"),
  confidenceInterval: document.querySelector("#confidence-interval"),
  experimentSample: document.querySelector("#experiment-sample"),
  queryCode: document.querySelector("#query-code"),
  toast: document.querySelector("#toast"),
};

const queries = {
  funnel: "SELECT\n  COUNT(*) AS signed_up,\n  SUM(completed_onboarding) AS onboarded,\n  SUM(activated) AS activated,\n  SUM(subscribed) AS subscribed\nFROM user_journeys\nWHERE acquisition_channel = :channel;",
  retention: "SELECT cohort_week,\n  AVG(retained_w1) AS week_1,\n  AVG(retained_w2) AS week_2,\n  AVG(retained_w3) AS week_3,\n  AVG(retained_w4) AS week_4\nFROM user_journeys\nGROUP BY cohort_week\nORDER BY cohort_week;",
  experiment: "pooled = (converted_a + converted_b) / (n_a + n_b)\nstandard_error = sqrt(\n    pooled * (1 - pooled) * (1 / n_a + 1 / n_b)\n)\nz_score = (rate_b - rate_a) / standard_error\np_value = 2 * (1 - normal_cdf(abs(z_score)))",
};

let dataset;
let currentSegment;
let toastTimer;

function percent(value, digits = 1) {
  return (value * 100).toFixed(digits) + "%";
}

function signedPoints(value) {
  const points = value * 100;
  return (points >= 0 ? "+" : "") + points.toFixed(1) + " pts";
}

function integer(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function currentKey() {
  return elements.channel.value + "|" + elements.platform.value;
}

function segmentFor(filters = {}) {
  const channel = filters.channel || "All channels";
  const platform = filters.platform || "All platforms";
  const segment = dataset.segments[channel + "|" + platform];
  if (!segment) throw new RangeError("No data for " + channel + " and " + platform);
  return segment;
}

function setMetric(element, noteElement, value, note) {
  element.textContent = value;
  noteElement.textContent = note;
}

function renderFunnel(segment) {
  const rows = segment.funnel.map((stage) => {
    const item = document.createElement("li");
    item.style.setProperty("--width", Math.max(stage.rate * 100, 34) + "%");
    const label = document.createElement("span");
    label.textContent = stage.name;
    const count = document.createElement("strong");
    count.textContent = integer(stage.count);
    const rate = document.createElement("small");
    rate.textContent = percent(stage.rate);
    item.append(label, count, rate);
    return item;
  });
  elements.funnel.replaceChildren(...rows);
}

function renderRetention(segment) {
  const rows = segment.retention.map((cohort) => {
    const row = document.createElement("tr");
    const label = document.createElement("td");
    label.textContent = cohort.cohort;
    const users = document.createElement("td");
    users.textContent = integer(cohort.users);
    row.append(label, users);
    for (const rate of cohort.rates) {
      const cell = document.createElement("td");
      cell.textContent = percent(rate, 0);
      cell.style.setProperty("--heat", rate.toFixed(3));
      row.append(cell);
    }
    return row;
  });
  elements.retentionBody.replaceChildren(...rows);
}

function renderExperiment(segment) {
  const experiment = segment.experiment;
  elements.decisionTitle.textContent = experiment.decision;
  elements.decisionCopy.textContent =
    experiment.decision === "Ship treatment B"
      ? "The guided checklist improved activation with a statistically reliable lift and no week 4 retention regression."
      : "The observed activation change is not yet reliable enough for a rollout decision.";
  elements.controlRate.textContent = percent(experiment.control_rate);
  elements.treatmentRate.textContent = percent(experiment.treatment_rate);
  elements.controlBar.style.setProperty("--bar", percent(experiment.control_rate, 0));
  elements.treatmentBar.style.setProperty("--bar", percent(experiment.treatment_rate, 0));
  elements.absoluteLift.textContent = signedPoints(experiment.absolute_lift);
  elements.confidenceInterval.textContent =
    signedPoints(experiment.ci_low) + " to " + signedPoints(experiment.ci_high);
  elements.experimentSample.textContent =
    integer(experiment.control_users + experiment.treatment_users) + " users";
}

function render() {
  currentSegment = dataset.segments[currentKey()];
  const experiment = currentSegment.experiment;
  setMetric(elements.activation, elements.activationNote, percent(currentSegment.activation_rate), integer(currentSegment.users) + " users in segment");
  setMetric(elements.conversion, elements.conversionNote, percent(currentSegment.conversion_rate), "$" + integer(Math.round(currentSegment.revenue_90d)) + " revenue in 90 days");
  setMetric(elements.retention, elements.retentionNote, percent(currentSegment.retention_w4), "Active four weeks after signup");
  setMetric(elements.lift, elements.liftNote, percent(experiment.relative_lift), "p = " + experiment.p_value.toFixed(3) + (experiment.p_value < 0.05 ? " · significant" : " · directional"));
  elements.segmentLabel.textContent = currentSegment.label;
  renderFunnel(currentSegment);
  renderRetention(currentSegment);
  renderExperiment(currentSegment);
}

function summaryCsv(segment = currentSegment) {
  const rows = [
    ["metric", "value"],
    ["segment", segment.label],
    ["users", segment.users],
    ["activation_rate", segment.activation_rate],
    ["paid_conversion_rate", segment.conversion_rate],
    ["week_4_retention", segment.retention_w4],
    ["revenue_90d", segment.revenue_90d],
    ["experiment_absolute_lift", segment.experiment.absolute_lift],
    ["experiment_p_value", segment.experiment.p_value],
    ["experiment_decision", segment.experiment.decision],
  ];
  return rows.map((row) => row.map((value) => '"' + String(value).replaceAll('"', '""') + '"').join(",")).join("\n");
}

function downloadCsv() {
  const blob = new Blob([summaryCsv()], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "product-signal-" + elements.channel.value.toLowerCase().replaceAll(" ", "-") + "-" + elements.platform.value.toLowerCase().replaceAll(" ", "-") + ".csv";
  anchor.click();
  URL.revokeObjectURL(url);
  showToast("Filtered summary downloaded.");
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => elements.toast.classList.remove("visible"), 2600);
}

function setFilters({ channel, platform }) {
  if (channel !== undefined) {
    if (!dataset.filters.channels.includes(channel)) throw new RangeError("Unsupported channel");
    elements.channel.value = channel;
  }
  if (platform !== undefined) {
    if (!dataset.filters.platforms.includes(platform)) throw new RangeError("Unsupported platform");
    elements.platform.value = platform;
  }
  render();
  return readSummary();
}

function readSummary() {
  return {
    channel: elements.channel.value,
    platform: elements.platform.value,
    users: currentSegment.users,
    activation_rate: currentSegment.activation_rate,
    paid_conversion_rate: currentSegment.conversion_rate,
    week_4_retention: currentSegment.retention_w4,
    revenue_90d: currentSegment.revenue_90d,
    experiment: currentSegment.experiment,
  };
}

function compareSegments(left, right) {
  const a = segmentFor(left);
  const b = segmentFor(right);
  return {
    left: { label: a.label, users: a.users, activation_rate: a.activation_rate, conversion_rate: a.conversion_rate, retention_w4: a.retention_w4 },
    right: { label: b.label, users: b.users, activation_rate: b.activation_rate, conversion_rate: b.conversion_rate, retention_w4: b.retention_w4 },
    activation_gap: Number((b.activation_rate - a.activation_rate).toFixed(4)),
    conversion_gap: Number((b.conversion_rate - a.conversion_rate).toFixed(4)),
  };
}

async function initialize() {
  const response = await fetch("./data/summary.json");
  if (!response.ok) throw new Error("Analysis data could not be loaded");
  dataset = await response.json();
  elements.exportButton.disabled = false;
  render();
  registerProductSignalTools({
    setFilters,
    readSummary,
    exportSummary: summaryCsv,
    compareSegments,
    reportError: console.warn,
  });
}

elements.channel.addEventListener("change", render);
elements.platform.addEventListener("change", render);
elements.exportButton.addEventListener("click", downloadCsv);
document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-query]").forEach((item) => item.setAttribute("aria-selected", String(item === button)));
    elements.queryCode.textContent = queries[button.dataset.query];
  });
});

initialize().catch((error) => {
  elements.exportButton.disabled = true;
  showToast(error.message);
  console.error(error);
});
