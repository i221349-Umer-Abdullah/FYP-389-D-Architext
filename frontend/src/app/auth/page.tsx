import { Suspense } from "react";

import { AuthPanel } from "./AuthPanel";
import styles from "./page.module.css";

export default function AuthPage() {
  return (
    <main className={styles.page}>
      <Suspense fallback={<div className={styles.card}>Loading sign in...</div>}>
        <AuthPanel />
      </Suspense>
    </main>
  );
}
