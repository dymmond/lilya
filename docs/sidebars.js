/**
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  docs: [
    "index",
    {
      type: "category",
      label: "Resources",
      link: { type: "doc", id: "resources/index" },
      items: [
        "applications",
        "settings",
        "routing",
        "controllers",
        "requests",
        "responses",
        "caching",
        "websockets",
        "encoders",
        "context",
        "authentication",
        "logging",
        "serializers",
        "security",
        "threadpool",
      ],
    },
    {
      type: "category",
      label: "Features",
      link: { type: "doc", id: "features/index" },
      items: [
        "tasks",
        "lifespan",
        "middleware",
        "permissions",
        "dependencies",
        "observables",
        "static-files",
        "templates",
        "server-push",
        "exceptions",
        "parameters",
        "wsgi",
        "environments",
      ],
    },
    {
      type: "category",
      label: "Clients",
      link: { type: "doc", id: "clients/index" },
      items: [
        {
          type: "category",
          label: "Lilya Client",
          items: [
            "lilya-cli",
            "directives/discovery",
            "directives/directives",
            "directives/custom-directives",
            "directives/directive-decorator",
            "directives/shell",
          ],
        },
        "test-client",
      ],
    },
    {
      type: "category",
      label: "Deployment",
      link: { type: "doc", id: "deployment/index" },
      items: [
        "intro",
        "docker",
      ],
    },
    {
      type: "category",
      label: "Contrib",
      link: { type: "doc", id: "contrib/index" },
      items: [
        "contrib/openapi",
        "contrib/forms-and-body-inference",
        "contrib/sse",
        {
          type: "category",
          label: "Schedulers",
          link: { type: "doc", id: "contrib/schedulers/index" },
          items: [
            "contrib/schedulers/config",
            "contrib/schedulers/handler",
            "contrib/schedulers/scheduler",
          ],
        },
        {
          type: "category",
          label: "Security",
          link: { type: "doc", id: "contrib/security/index" },
          items: [
            "contrib/security/introduction",
            "contrib/security/interaction",
            "contrib/security/simple-oauth2",
            "contrib/security/oauth-jwt",
            {
              type: "category",
              label: "Advanced",
              items: [
                "contrib/security/advanced/oauth2-scopes",
                "contrib/security/advanced/basic-auth",
              ],
            },
            "contrib/security/available-security",
            "contrib/security/signed-urls",
            {
              type: "category",
              label: "CSRF",
              items: ["contrib/security/csrf"],
            },
          ],
        },
        {
          type: "category",
          label: "Files",
          items: [
            "contrib/files/send-file",
            "contrib/files/jsonify",
          ],
        },
        {
          type: "category",
          label: "Proxy",
          items: ["contrib/proxy/relay"],
        },
        {
          type: "category",
          label: "Shortcuts",
          items: [
            "contrib/shortcuts/abort",
            "contrib/shortcuts/responses",
          ],
        },
        "contrib/mail",
        "contrib/opentelemetry",
      ],
    },
    "contributing",
    "sponsorship",
    "release-notes",
  ],
};

module.exports = sidebars;
