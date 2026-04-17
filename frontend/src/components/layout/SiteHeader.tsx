"use client";

import Link from "next/link";
import { useState } from "react";

import { APP_TITLE } from "@/lib/constants";
import { AuthButton } from "./AuthButton";

import styles from "./SiteHeader.module.css";

export function SiteHeader() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <header className={styles.header}>
      <div className="app-container">
        <div className={styles.inner}>
          <Link href="/" className={styles.brand}>
            {APP_TITLE}
          </Link>
          <button
            type="button"
            className={styles.menuButton}
            aria-expanded={navOpen}
            aria-controls="site-nav"
            onClick={() => setNavOpen((current) => !current)}
          >
            Menu
          </button>
          <nav
            id="site-nav"
            className={`${styles.nav} ${navOpen ? styles.navOpen : ""}`}
            aria-label="Main"
            onClick={() => setNavOpen(false)}
          >
            <Link href="/" className={styles.link}>
              Home
            </Link>
            <Link href="/studio" className={styles.link}>
              Studio
            </Link>
            <Link href="/floor-plans" className={styles.link}>
              Library
            </Link>
            <Link href="/dashboard" className={styles.link}>
              Dashboard
            </Link>
            <Link href="/plugins" className={styles.link}>
              Plugins
            </Link>
            <AuthButton />
          </nav>
        </div>
      </div>
    </header>
  );
}
