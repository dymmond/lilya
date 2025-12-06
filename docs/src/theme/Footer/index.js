import React from "react";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import FooterLinkItem from "@theme/Footer/LinkItem";
import styles from "./styles.module.css";

export default function Footer() {
  const { siteConfig } = useDocusaurusContext();
  const footer = siteConfig.themeConfig.footer;

  if (!footer) return null;

  const { links = [], copyright } = footer;

  return (
    <footer className={styles.footer}>
      <div className={styles.container}>

        {/* Horizontal footer sections */}
        <div className={styles.sections}>
          {links.map((section, idx) => (
            <div key={idx} className={styles.section}>
              <h4 className={styles.title}>{section.title}</h4>
              <ul className={styles.list}>
                {section.items.map((item, i) => (
                  <li key={i} className={styles.listItem}>
                    <FooterLinkItem item={item} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Copyright */}
        <div className={styles.copy}>
          {copyright}
        </div>

      </div>
    </footer>
  );
}
