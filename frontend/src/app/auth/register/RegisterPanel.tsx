"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

import { getSafeCallbackUrl } from "@/lib/authRedirect";
import styles from "../page.module.css";

export function RegisterPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = getSafeCallbackUrl(searchParams.get("callbackUrl"));
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    const formData = new FormData(event.currentTarget);
    const name = String(formData.get("name") ?? "");
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    const response = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    const payload = (await response.json()) as { error?: string };

    if (!response.ok) {
      setError(payload.error ?? "Could not create your account.");
      setIsLoading(false);
      return;
    }

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
      callbackUrl,
    });

    setIsLoading(false);

    if (result?.ok) {
      router.push(result.url ?? callbackUrl);
      router.refresh();
      return;
    }

    router.push(`/auth?callbackUrl=${encodeURIComponent(callbackUrl)}`);
  }

  return (
    <div className={styles.card}>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden>
          A
        </span>
        <span className={styles.brandName}>Architext</span>
      </div>

      <p className={styles.copy}>
        Create your studio account with an email and password.
      </p>

      <form className={styles.form} onSubmit={handleRegister}>
        {error ? <p className={styles.error}>{error}</p> : null}

        <label className={styles.field}>
          <span className={styles.label}>Name</span>
          <input
            className={styles.input}
            type="text"
            name="name"
            autoComplete="name"
            placeholder="Your name"
            disabled={isLoading}
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Email</span>
          <input
            className={styles.input}
            type="email"
            name="email"
            autoComplete="email"
            placeholder="you@example.com"
            disabled={isLoading}
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Password</span>
          <input
            className={styles.input}
            type="password"
            name="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            minLength={8}
            disabled={isLoading}
            required
          />
        </label>

        <button type="submit" className={styles.submitBtn} disabled={isLoading}>
          {isLoading ? "Creating account..." : "Create account"}
        </button>
      </form>

      <p className={styles.authSwitch}>
        Already have an account?{" "}
        <Link href={`/auth?callbackUrl=${encodeURIComponent(callbackUrl)}`} className={styles.inlineLink}>
          Login
        </Link>
      </p>

      <Link href={callbackUrl} className={styles.secondaryLink}>
        Back
      </Link>
    </div>
  );
}
