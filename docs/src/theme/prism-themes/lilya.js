const lilyaLight = {
  plain: {
    backgroundColor: "#f5f7fa",   // softer + higher contrast than #f8fafc
    color: "#1e293b",             // slate-800
  },
  styles: [
    {
      types: ["comment"],
      style: {
        color: "#94a3b8",         // slate-400
        fontStyle: "italic",
      },
    },
    {
      types: ["keyword", "operator"],
      style: {
        color: "#7c3aed",         // richer Lilya purple
        fontWeight: 600,
      },
    },
    {
      types: ["string"],
      style: {
        color: "#0ea5e9",         // sky-500
      },
    },
    {
      types: ["function"],
      style: {
        color: "#059669",         // emerald-600 (clean + readable)
      },
    },
    {
      types: ["class-name", "builtin"],
      style: {
        color: "#dc2626",         // red-600
      },
    },
    {
      types: ["punctuation"],
      style: {
        color: "#475569",         // slate-600
      },
    },
  ],
};

const lilyaDark = {
  plain: {
    backgroundColor: "#0f172a",
    color: "#e2e8f0",
  },
  styles: [
    { types: ["comment"], style: { color: "#64748b", fontStyle: "italic" } },
    { types: ["keyword"], style: { color: "#c084fc", fontWeight: 600 } },
    { types: ["string"], style: { color: "#38bdf8" } },
    { types: ["function"], style: { color: "#2dd4bf" } },
    { types: ["class-name"], style: { color: "#f87171" } },
    { types: ["punctuation"], style: { color: "#94a3b8" } },
  ],
};

module.exports = { lilyaLight, lilyaDark };
