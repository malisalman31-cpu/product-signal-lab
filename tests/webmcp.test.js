import assert from "node:assert/strict";
import test from "node:test";

import { registerProductSignalTools } from "../dist/webmcp.js";

function context() {
  const tools = [];
  return {
    tools,
    registerTool(tool, options) {
      tools.push({ ...tool, options });
    },
  };
}

test("returns unsupported without a model context", () => {
  assert.equal(registerProductSignalTools().supported, false);
});

test("requires all callbacks", () => {
  const modelContext = context();
  assert.throws(() => registerProductSignalTools({ modelContext }), /setFilters/);
});

test("registers four stable tools", () => {
  const modelContext = context();
  const result = registerProductSignalTools({
    modelContext,
    setFilters: () => ({}),
    readSummary: () => ({}),
    exportSummary: () => "",
    compareSegments: () => ({}),
  });
  assert.deepEqual(result.tools, [
    "set_product_signal_filters",
    "read_product_signal_summary",
    "export_product_signal_summary",
    "compare_product_signal_segments",
  ]);
  assert.equal(modelContext.tools.length, 4);
});

test("annotations distinguish reads and writes", () => {
  const modelContext = context();
  registerProductSignalTools({
    modelContext,
    setFilters: () => ({}),
    readSummary: () => ({}),
    exportSummary: () => "",
    compareSegments: () => ({}),
  });
  assert.equal(modelContext.tools[0].annotations.readOnlyHint, false);
  assert.equal(modelContext.tools[1].annotations.readOnlyHint, true);
  assert.ok(modelContext.tools.every((tool) => tool.options.signal instanceof AbortSignal));
});

test("filter executor forwards inputs", async () => {
  const modelContext = context();
  let received;
  registerProductSignalTools({
    modelContext,
    setFilters: (input) => { received = input; return { users: 42 }; },
    readSummary: () => ({}),
    exportSummary: () => "",
    compareSegments: () => ({}),
  });
  const result = await modelContext.tools[0].execute({ channel: "Referral", platform: "iOS" });
  assert.deepEqual(received, { channel: "Referral", platform: "iOS" });
  assert.equal(result.users, 42);
});

test("export wraps CSV output", async () => {
  const modelContext = context();
  registerProductSignalTools({
    modelContext,
    setFilters: () => ({}),
    readSummary: () => ({}),
    exportSummary: () => "metric,value",
    compareSegments: () => ({}),
  });
  assert.deepEqual(await modelContext.tools[2].execute({}), { csv: "metric,value" });
});

test("comparison requires both segments", async () => {
  const modelContext = context();
  registerProductSignalTools({
    modelContext,
    setFilters: () => ({}),
    readSummary: () => ({}),
    exportSummary: () => "",
    compareSegments: () => ({}),
  });
  await assert.rejects(modelContext.tools[3].execute({ left: {} }), /left and right/);
});
