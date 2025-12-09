/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    {
      type: "category",
      label: "Welcome",
      collapsed: false,
      items: ["index"], // docs/index.mdx
    },
    {
      type: "category",
      label: "Resources",
      collapsed: false,
      items: [
        "resources/installation",
        "resources/quickstart",
        "resources/cli",
      ],
    },
    {
      type: "category",
      label: "Features",
      collapsed: false,
      items: [
        "features/tasks",
        "features/lifespan",
        "features/middleware",
        "features/permissions",
        "features/dependencies",
        "features/observables",
        "features/static-files",
        "features/templates",
        "features/server-push",
      ],
    },
    {
      type: "category",
      label: "Contrib",
      collapsed: true,
      items: [
        "contrib/openapi",
        "contrib/schedulers",
        "contrib/security",
        "contrib/mail",
      ],
    },
  ],
};

module.exports = sidebars;
