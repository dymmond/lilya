import React, { useEffect } from "react";
import Layout from "@theme/Layout";
import CodeBlock from "@theme/CodeBlock";
import styles from "./index.module.css";

const example = `
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.responses import Ok

async def welcome():
    return Ok({"message": "Welcome to Lilya"})

app = Lilya(
    routes=[
        Path("/", welcome),
    ]
)
`.trim();

export default function Home() {
  // body background for homepage
  useEffect(() => {
    document.body.classList.add("homepage");
    return () => document.body.classList.remove("homepage");
  }, []);

  return (
    <Layout title="Lilya" description="The ASGI toolkit that delivers.">
      <main>
        <Hero />
        <Showcase />
        <Features />
      </main>
    </Layout>
  );
}

function Hero() {
  return (
    <header className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.heroText}>
          <p className={styles.badge}>ASGI Toolkit</p>
          <h1>The ASGI Toolkit That Delivers</h1>
          <p className={styles.tagline}>
            A lightweight, fast, elegant and fully typed Python ASGI toolkit for
            building powerful and scalable applications with minimum boilerplate.
          </p>

          <div className={styles.heroActions}>
            <a className="button button--lilya" href="/docs">
              Get Started
            </a>
            <a
              className="button button--secondary"
              href="https://github.com/dymmond/lilya"
            >
              GitHub
            </a>
          </div>
        </div>

        <div className={styles.heroLogoWrapper}>
          <img src="/img/logo.png" alt="Lilya logo" className={styles.heroLogo} />
        </div>
      </div>
    </header>
  );
}

function Showcase() {
  return (
    <section className={styles.showcase}>
      <div className={styles.showcaseInner}>
        <CodeBlock language="python">{example}</CodeBlock>
      </div>
    </section>
  );
}

function Features() {
  const items = [
    {
      title: "Native ASGI",
      body: "Lightweight, flexible and built entirely on the ASGI spec.",
    },
    {
      title: "Typed Routing",
      body: "Automatic parameter extraction and fully typed request handlers.",
    },
    {
      title: "Controllers & Dependencies",
      body: "Powerful patterns for scalable application structure.",
    },
    {
      title: "Middlewares",
      body: "CORS, CSRF, compression, sessions and more built-in.",
    },
    {
      title: "Settings System",
      body: "Native configuration system for clean and maintainable apps.",
    },
    {
      title: "WebSocket Support",
      body: "Real-time applications made simple.",
    },
  ];

  return (
    <section className={styles.featuresSection}>
      <h2>What Lilya Brings</h2>
      <p className={styles.featuresIntro}>
        Build production-ready ASGI applications with an elegant minimal syntax.
      </p>

      <div className={styles.featuresGrid}>
        {items.map((item) => (
          <article key={item.title} className={styles.featureCard}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
