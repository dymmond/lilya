import React from "react";
import Layout from "@theme/Layout";
import CodeBlock from "@theme/CodeBlock";

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
  React.useEffect(() => {
    document.body.classList.add("homepage");
    return () => document.body.classList.remove("homepage");
  }, []);

  return (
    <Layout title="Lilya" description="The ASGI toolkit that delivers.">
      <Hero />
      <Showcase />
      <Features />
    </Layout>
  );
}

/* ----------------------------------------------------
   HERO — LITESTAR-STYLE LEFT/RIGHT LAYOUT
---------------------------------------------------- */
function Hero() {
  return (
    <section
      className="hero"
      style={{
        padding: "5rem 2rem 12rem",
        background:
          "radial-gradient(circle at 30% 30%, rgba(124,58,237,0.35), transparent 70%), linear-gradient(90deg, #0f172a 0%, #1e1b4b 100%)",
        color: "white",
      }}
    >
      <div
        style={{
          maxWidth: "1400px",
          margin: "0 auto",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "3rem",
          flexWrap: "wrap",
        }}
      >
        {/* LEFT SIDE */}
        <div style={{ flex: 1, minWidth: "300px" }}>
          <img
            src="/img/logo.png"
            alt="Lilya Logo"
            style={{ height: "110px", marginBottom: "1.5rem" }}
          />

          <h1 style={{ fontSize: "3.4rem", lineHeight: 1.1, marginBottom: "1rem" }}>
            The ASGI toolkit
            <br />that delivers
          </h1>

          <p
            style={{
              fontSize: "1.25rem",
              opacity: 0.9,
              maxWidth: "520px",
              lineHeight: 1.5,
              marginBottom: "2rem",
            }}
          >
            A lightweight, fast, elegant and fully typed Python ASGI toolkit
            for building powerful and scalable applications with minimum boilerplate.
          </p>

          <div>
            <a className="button button--lilya" href="/docs" style={{ marginRight: 12 }}>
              Get Started
            </a>
            <a className="button button--secondary" href="https://github.com/dymmond/lilya">
              GitHub
            </a>
          </div>
        </div>

        {/* RIGHT SIDE */}
        <div
          style={{
            flex: 1,
            textAlign: "left",
            minWidth: "300px",
          }}
        >
          <CodeBlock language="python">{example}</CodeBlock>
        </div>
      </div>
    </section>
  );
}

/* ----------------------------------------------------
   FLOATING CODE SHOWCASE (OPTIONAL)
---------------------------------------------------- */
function Showcase() {
  return (
    <div
      style={{
        marginTop: "-6rem",
        maxWidth: "900px",
        marginInline: "auto",
        padding: "0 1rem",
        zIndex: 20,
        position: "relative",
      }}
    ></div>
  );
}

/* ----------------------------------------------------
   FEATURES SECTION
---------------------------------------------------- */
function Features() {
  const items = [
    { title: "Native ASGI", description: "Lightweight and flexible on ASGI." },
    { title: "Controllers", description: "Powerful OOP structure patterns." },
    { title: "Middlewares", description: "CORS, CSRF, compression, sessions." },
    { title: "Settings System", description: "Clean and maintainable config." },
    { title: "WebSockets", description: "Real-time made simple." },
    { title: "Optional Batteries", description: "The contrib section is your best friend." },
  ];

  return (
    <section
      style={{
        background: "#f8fafc",
        padding: "6rem 1rem",
        color: "#1e293b",
      }}
    >
      <h2 style={{ fontSize: "2.3rem", textAlign: "center", marginBottom: "3rem" }}>
        What Lilya Brings
      </h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "2rem",
          maxWidth: "1100px",
          margin: "0 auto",
        }}
      >
        {items.map((item, i) => (
          <div
            key={i}
            style={{
              background: "white",
              padding: "1.8rem",
              borderRadius: "14px",
              border: "1px solid #e5e7eb",
              boxShadow: "0 6px 18px rgba(0,0,0,0.08)",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", marginBottom: "0.6rem" }}>{item.title}</h3>
            <p style={{ color: "#475569" }}>{item.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
