"use client";

import Link from "next/link";
import type { MouseEvent } from "react";
import { signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

import styles from "./SiteHeader.module.css";

export function AuthButton() {
  const { data: session, status } = useSession();
  const router = useRouter();

  function handleLoginClick(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    const callbackUrl = `${window.location.pathname}${window.location.search}`;
    router.push(`/auth?callbackUrl=${encodeURIComponent(callbackUrl)}`);
  }

  if (status === "loading") {
    return <span className={styles.link}>Checking...</span>;
  }

  if (session?.user) {
    const name = session.user.name ?? session.user.email ?? "User";
    const initial = name.charAt(0).toUpperCase();

    return (
      <div className={styles.authRow}>
        {session.user.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={session.user.image} alt="" className={styles.avatar} />
        ) : (
          <span className={styles.avatarFallback} aria-hidden>
            {initial}
          </span>
        )}
        <button type="button" className={styles.linkButton} onClick={() => signOut({ callbackUrl: "/" })}>
          Sign out
        </button>
      </div>
    );
  }

  return (
    <Link href="/auth" className={styles.link} onClick={handleLoginClick}>
      Login
    </Link>
  );
}
