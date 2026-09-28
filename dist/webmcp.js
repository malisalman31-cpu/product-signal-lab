const FILTER_SCHEMA = {
  type: "object",
  properties: {
    channel: { type: "string" },
    platform: { type: "string" },
  },
  additionalProperties: false,
};

function requireCallback(value, name) {
  if (typeof value !== "function") throw new TypeError(name + " must be a function");
}

export function registerProductSignalTools({
  modelContext = typeof document === "undefined" ? undefined : document.modelContext,
  setFilters,
  readSummary,
  exportSummary,
  compareSegments,
  reportError = () => {},
} = {}) {
  if (!modelContext?.registerTool) return { supported: false, dispose() {} };
  requireCallback(setFilters, "setFilters");
  requireCallback(readSummary, "readSummary");
  requireCallback(exportSummary, "exportSummary");
  requireCallback(compareSegments, "compareSegments");

  const lifecycle = new AbortController();
  const tools = [
    {
      name: "set_product_signal_filters",
      title: "Set product analytics filters",
      description: "Update the visible acquisition-channel and platform filters.",
      inputSchema: FILTER_SCHEMA,
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      execute: async (input = {}) => setFilters(input),
    },
    {
      name: "read_product_signal_summary",
      title: "Read product analytics summary",
      description: "Read the visible funnel, retention, revenue, and experiment result.",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute: async () => readSummary(),
    },
    {
      name: "export_product_signal_summary",
      title: "Export product analytics summary",
      description: "Return the active segment summary as CSV text.",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute: async () => ({ csv: exportSummary() }),
    },
    {
      name: "compare_product_signal_segments",
      title: "Compare product analytics segments",
      description: "Compare two channel and platform segments without changing the visible filters.",
      inputSchema: {
        type: "object",
        properties: {
          left: FILTER_SCHEMA,
          right: FILTER_SCHEMA,
        },
        required: ["left", "right"],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute: async (input) => {
        if (!input?.left || !input?.right) throw new TypeError("left and right segments are required");
        return compareSegments(input.left, input.right);
      },
    },
  ];

  for (const tool of tools) {
    try {
      void Promise.resolve(modelContext.registerTool(tool, { signal: lifecycle.signal })).catch(reportError);
    } catch (error) {
      reportError(error);
    }
  }
  return { supported: true, tools: tools.map((tool) => tool.name), dispose: () => lifecycle.abort() };
}
