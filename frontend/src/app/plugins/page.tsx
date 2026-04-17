import type { Metadata } from "next";
import Link from "next/link";

import { SiteHeader } from "@/components/layout/SiteHeader";
import { PLUGINS } from "@/lib/plugins";

import styles from "./plugins.module.css";

export const metadata: Metadata = {
  title: "Plugins | Architext",
  description: "Download Architext plugins for Revit and Blender workflows.",
};

export default function PluginsPage() {
  return (
    <div className={styles.page}>
      <SiteHeader />
      <main>
        <section className={styles.intro}>
          <div className="app-container">
            <p className={styles.eyebrow}>Desktop connectors</p>
            <h1 className={styles.title}>Choose your plugin workflow.</h1>
            <p className={styles.subtitle}>
              Move generated plans from Architext into the tools used for BIM authoring and 3D review.
            </p>
          </div>
        </section>

        <section className={styles.split} aria-label="Plugin options">
          {PLUGINS.map((plugin) => (
            <Link key={plugin.slug} href={`/plugins/${plugin.slug}`} className={styles.pluginPanel}>
              <span className={styles.panelContent}>
                <span className={styles.panelEyebrow}>{plugin.eyebrow}</span>
                <span className={styles.panelTitle}>{plugin.name}</span>
                <span className={styles.panelCopy}>{plugin.summary}</span>
                <span className={styles.panelAction}>View details</span>
              </span>
            </Link>
          ))}
        </section>
      </main>
    </div>
  );
}
