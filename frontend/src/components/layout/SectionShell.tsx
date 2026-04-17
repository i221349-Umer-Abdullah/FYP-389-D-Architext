import { ReactNode } from "react";
import clsx from "clsx";

import styles from "./SectionShell.module.css";

interface SectionShellProps {
  children: ReactNode;
  id?: string;
  className?: string;
}

export function SectionShell({ children, id, className }: SectionShellProps) {
  return (
    <section id={id} className={clsx(styles.section, className)}>
      <div className="app-container">{children}</div>
    </section>
  );
}
