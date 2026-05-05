import type { Metadata } from "next";
import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { SiteHeader } from "@/components/layout/SiteHeader";
import { authOptions } from "@/lib/auth";
import { readFloorPlans } from "@/lib/floorPlans";

import { DashboardClient } from "./DashboardClient";
import styles from "./dashboard.module.css";

export const metadata: Metadata = {
  title: "Dashboard | Architext",
  description: "Upload floor plan files to the shared Architext library.",
};

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user?.email) {
    redirect(`/auth?callbackUrl=${encodeURIComponent("/dashboard")}`);
  }

  const floorPlans = await readFloorPlans(session.user.email);

  return (
    <div className={styles.page}>
      <SiteHeader />
      <main className={styles.main}>
        <div className="app-container">
          <DashboardClient
            initialFloorPlans={floorPlans}
            mode="dashboard"
            currentUserEmail={session.user.email}
          />
        </div>
      </main>
    </div>
  );
}
