const fs = require("fs");
const path = require("path");
const { visit } = require("unist-util-visit");

// Repo root = lilya/
const PROJECT_ROOT = path.resolve(__dirname, "../../..");

// Correct location of docs_src
const DOCS_SRC_ROOT = path.join(PROJECT_ROOT, "/");

module.exports = function remarkIncludeFiles() {
  return (tree, file) => {

    const resolveInclude = (includePath) => {
      // Remove leading ../ or ./ to avoid escaping
      const clean = includePath.replace(/^(\.\/|\.\.\/)+/, "");
      return path.join(DOCS_SRC_ROOT, clean);
    };

    // 1) Inside fenced blocks
    visit(tree, "code", (node) => {
      if (!node.value) return;
      const match = node.value.trim().match(/^\{\!>\s*(.*?)\s*\!\}$/);
      if (!match) return;

      const includePath = match[1];
      const absolutePath = resolveInclude(includePath);

      if (!fs.existsSync(absolutePath)) {
        throw new Error(`[remark-include-files] File not found: ${absolutePath}`);
      }

      let content = fs.readFileSync(absolutePath, "utf8");
      content = content.replace(/\n$/, "");  // remove final newline

      node.lang = node.lang || detectLanguage(includePath);
      node.value = content;
    });

    // 2) Standalone include
    visit(tree, "paragraph", (node, index, parent) => {
      if (!node.children?.length) return;

      const text = node.children[0].value || "";
      const match = text.trim().match(/^\{\!>\s*(.*?)\s*\!\}$/);
      if (!match) return;

      const includePath = match[1];
      const absolutePath = resolveInclude(includePath);

      if (!fs.existsSync(absolutePath)) {
        throw new Error(`[remark-include-files] File not found: ${absolutePath}`);
      }

      let content = fs.readFileSync(absolutePath, "utf8");
      content = content.replace(/\n$/, "");  // remove final newline

      parent.children[index] = {
        type: "code",
        lang: detectLanguage(includePath),
        value: content,
      };
    });
  };
};

function detectLanguage(filePath) {
  if (filePath.endsWith(".py")) return "python";
  if (filePath.endsWith(".ts")) return "ts";
  if (filePath.endsWith(".js")) return "javascript";
  if (filePath.endsWith(".json")) return "json";
  if (filePath.endsWith(".html")) return "html";
  return "";
}
