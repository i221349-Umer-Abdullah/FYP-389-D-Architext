import { Suspense } from "react";

import { RegisterPanel } from "./RegisterPanel";
import styles from "../page.module.css";

export default function RegisterPage() {
  return (
    <main className={styles.page}>
      <Suspense fallback={<div className={styles.card}>Loading registration...</div>}>
        <RegisterPanel />
      </Suspense>
    </main>
  );
}
