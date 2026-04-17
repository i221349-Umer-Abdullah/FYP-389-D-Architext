import type { Metadata } from "next";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { SiteHeader } from "@/components/layout/SiteHeader";
import { authOptions } from "@/lib/auth";
import { readFloorPlans } from "@/lib/floorPlans";

import { DashboardClient } from "../dashboard/DashboardClient";
import styles from "../dashboard/dashboard.module.css";

export const metadata: Metadata = {
  title: "Floor Plans | Architext",
  description: "Browse, preview, comment on, version, and download shared floor plans.",
};

export default async function FloorPlansPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect(`/auth?callbackUrl=${encodeURIComponent("/floor-plans")}`);
  }

  const floorPlans = await readFloorPlans(session.user?.email);

  return (
    <div className={styles.page}>
      <SiteHeader />
      <main className={styles.main}>
        <div className="app-container">
          <DashboardClient initialFloorPlans={floorPlans} mode="floorPlans" />
        </div>
      </main>
    </div>
  );
}
