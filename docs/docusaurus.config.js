// @ts-check
const { lilyaLight, lilyaDark } = require("./src/theme/prism-themes/lilya");
const remarkIncludeFiles = require("./plugins/remark-include-files");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Lilya",
  tagline: "The ASGI toolkit that delivers.",
  url: "https://lilya.dev",
  baseUrl: "/",
  favicon: "img/favicon.ico",

  organizationName: "dymmond",
  projectName: "lilya",

  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en", "pt"],
  },

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: require.resolve("./sidebars.js"),
          editUrl: "https://github.com/dymmond/lilya/tree/main/docs/docs/",
          showLastUpdateTime: true,
          showLastUpdateAuthor: true,
          remarkPlugins: [remarkIncludeFiles],
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      },
    ],
  ],

  themeConfig: {
    navbar: {
      style: "dark",
      hideOnScroll: false,
      logo: {
        alt: "Lilya logo",
        src: "img/logo.png",
        href: "/",
        height: 40,
      },
      items: [
        { label: "Docs", to: "/docs", position: "left" },
        {
          label: "Community",
          position: "left",
          items: [
            { label: "Discord", href: "https://discord.gg/hS5pv3S4" },
            { label: "GitHub", href: "https://github.com/dymmond/lilya" },
          ],
        },
        {
          label: "About",
          position: "left",
          items: [
            { label: "Mission", to: "/about/mission" },
            { label: "Team", to: "/about/team" },
          ],
        },
        {
          label: "Help",
          position: "left",
          items: [
            { label: "FAQ", to: "/help/faq" },
            { label: "Support", to: "/help/support" },
          ],
        },

        // right side: Discord, GitHub, color-mode toggle
        {
          href: "https://discord.gg/hS5pv3S4",
          position: "right",
          "aria-label": "Lilya Discord",
          className: "navbar-icon navbar-icon--discord",
        },
        {
          href: "https://github.com/dymmond/lilya",
          position: "right",
          "aria-label": "Lilya GitHub",
          className: "navbar-icon navbar-icon--github",
        },
        {
          type: "localeDropdown",
          position: "right",
        },
        {
          type: "search",
          position: "right",
        },
      ],
    },

    footer: {
      style: "dark",
      links: [
        {
          title: "Docs",
          items: [{ label: "Introduction", to: "/docs" }],
        },
        {
          title: "Community",
          items: [{ label: "GitHub", href: "https://github.com/dymmond/lilya" }],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Dymmond.`,
    },

    colorMode: {
      defaultMode: "dark",
      respectPrefersColorScheme: true,
      disableSwitch: false,
    },

    prism: {
      theme: lilyaLight,
      darkTheme: lilyaDark,
      additionalLanguages: ["python", "bash"],
    },
  },

  themes: ["@docusaurus/theme-live-codeblock"],
  plugins: ["docusaurus-plugin-sass"],
};

module.exports = config;
