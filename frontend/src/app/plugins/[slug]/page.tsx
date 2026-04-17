import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { SiteHeader } from "@/components/layout/SiteHeader";
import { getPlugin, PLUGINS } from "@/lib/plugins";

import styles from "../plugins.module.css";

type PluginDetailPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export function generateStaticParams() {
  return PLUGINS.map((plugin) => ({ slug: plugin.slug }));
}

export async function generateMetadata({ params }: PluginDetailPageProps): Promise<Metadata> {
  const { slug } = await params;
  const plugin = getPlugin(slug);

  if (!plugin) {
    return {
      title: "Plugin | Architext",
    };
  }

  return {
    title: `${plugin.name} | Architext`,
    description: plugin.summary,
  };
}

export default async function PluginDetailPage({ params }: PluginDetailPageProps) {
  const { slug } = await params;
  const plugin = getPlugin(slug);

  if (!plugin) {
    notFound();
  }

  return (
    <div className={styles.page}>
      <SiteHeader />
      <main className={styles.detail}>
        <div className="app-container">
          <div className={styles.detailGrid}>
            <section>
              <p className={styles.eyebrow}>{plugin.eyebrow}</p>
              <h1 className={styles.title}>{plugin.name}</h1>
              <p className={styles.description}>{plugin.description}</p>

              <ul className={styles.detailList}>
                {plugin.details.map((detail) => (
                  <li key={detail} className={styles.detailItem}>
                    {detail}
                  </li>
                ))}
              </ul>
            </section>

            <aside className={styles.downloadBox} aria-label={`${plugin.name} download`}>
              <h2 className={styles.downloadTitle}>{plugin.name} package</h2>
              <p className={styles.downloadCopy}>
                Download the starter package and replace it with the production plugin build when it is ready.
              </p>
              <Link href={plugin.downloadHref} className={styles.downloadButton} download>
                {plugin.downloadLabel}
              </Link>
              <Link href="/plugins" className={styles.backLink}>
                Back to plugins
              </Link>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
