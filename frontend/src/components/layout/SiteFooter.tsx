import Link from "next/link";

import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className="app-container">
        <div className={styles.inner}>
          <div className={styles.brandBlock}>
            <p className={styles.brand}>Architext</p>
            <p className={styles.tagline}>
              Natural language to spatial intelligence.
            </p>
          </div>
          <div className={styles.meta}>
            <p className={styles.label}>Created by</p>
            <p className={styles.names}>Jalal &amp; Umer</p>
          </div>
          <div className={styles.contacts}>
            <Link href="mailto:jalalhaier5050@gmail.com" className={styles.contact}>
              jalalhaier5050@gmail.com
            </Link>
            <Link href="mailto:umer6969@gmail.com" className={styles.contact}>
              umer6969@gmail.com
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
