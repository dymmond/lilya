// @ts-check
const { themes } = require('prism-react-renderer');
const lightCodeTheme = themes.github;
const darkCodeTheme = themes.dracula;

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
          editUrl: "https://github.com/dymmond/lilya/tree/main/docs/",
          showLastUpdateTime: true,
          showLastUpdateAuthor: true,
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
      title: "Lilya",
      logo: {
        alt: "Lilya Logo",
        src: "img/white.png",
      },
      items: [
        { type: "doc", docId: "index", position: "left", label: "Docs" },
        {
          href: "https://github.com/dymmond/lilya",
          label: "GitHub",
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
          items: [
            { label: "GitHub", href: "https://github.com/dymmond/lilya" },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Dymmond.`,
    },

    prism: {
      theme: lightCodeTheme,
      darkTheme: darkCodeTheme,
    },
  },

  themes: ["@docusaurus/theme-live-codeblock"],

  plugins: [
    "docusaurus-plugin-sass",
  ],
};

module.exports = config;
