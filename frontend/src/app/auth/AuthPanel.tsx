"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { signIn, useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

import { getSafeCallbackUrl } from "@/lib/authRedirect";
import styles from "./page.module.css";

const errorMessages: Record<string, string> = {
  OAuthCallback:
    "Google approved the login, but the app could not finish the callback. Check the Google secret and MongoDB connection.",
  OAuthSignin:
    "The app could not start Google sign in. Check the Google client ID and redirect URI.",
  OAuthCreateAccount:
    "The app could not create your account after Google sign in. Check MongoDB access.",
  AccessDenied: "Google denied access for this account.",
  Configuration: "The auth server is missing or rejecting one of the required environment values.",
  CredentialsSignin: "The email or password is not correct.",
};

export function AuthPanel() {
  const { status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const error = searchParams.get("error");
  const callbackUrl = getSafeCallbackUrl(searchParams.get("callbackUrl"));
  const [credentialsError, setCredentialsError] = useState("");
  const [isCredentialsLoading, setIsCredentialsLoading] = useState(false);
  const errorMessage = error
    ? errorMessages[error] ?? "Google sign in could not complete. Check your OAuth setup and try again."
    : null;
  const isLoading = status === "loading";
  const isSignedIn = status === "authenticated";

  async function handleCredentialsSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCredentialsError("");
    setIsCredentialsLoading(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
      callbackUrl,
    });

    setIsCredentialsLoading(false);

    if (result?.ok) {
      router.push(result.url ?? callbackUrl);
      router.refresh();
      return;
    }

    setCredentialsError("The email or password is not correct.");
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
        Sign in with Google or your studio email and password.
      </p>

      {errorMessage ? (
        <p className={styles.error}>
          {errorMessage}
          <span className={styles.errorCode}>Error code: {error}</span>
        </p>
      ) : null}

      {isSignedIn ? (
        <Link href={callbackUrl} className={styles.submitBtn}>
          Continue
        </Link>
      ) : (
        <button
          type="button"
          className={styles.googleBtn}
          disabled={isLoading}
          onClick={() => signIn("google", { callbackUrl })}
        >
          <span className={styles.googleMark} aria-hidden>
            G
          </span>
          {isLoading ? "Checking session..." : "Continue with Google"}
        </button>
      )}

      {!isSignedIn ? (
        <>
          <div className={styles.divider}>or sign in with email</div>

          <form className={styles.form} onSubmit={handleCredentialsSignIn}>
            {credentialsError ? <p className={styles.error}>{credentialsError}</p> : null}

            <label className={styles.field}>
              <span className={styles.label}>Email</span>
              <input
                className={styles.input}
                type="email"
                name="email"
                autoComplete="email"
                placeholder="you@example.com"
                disabled={isCredentialsLoading}
                required
              />
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Password</span>
              <input
                className={styles.input}
                type="password"
                name="password"
                autoComplete="current-password"
                placeholder="Your password"
                disabled={isCredentialsLoading}
                required
              />
            </label>

            <button type="submit" className={styles.submitBtn} disabled={isCredentialsLoading}>
              {isCredentialsLoading ? "Signing in..." : "Login"}
            </button>
          </form>

          <p className={styles.authSwitch}>
            New to Architext?{" "}
            <Link
              href={`/auth/register?callbackUrl=${encodeURIComponent(callbackUrl)}`}
              className={styles.inlineLink}
            >
              Create account
            </Link>
          </p>
        </>
      ) : null}

      <Link href={callbackUrl} className={styles.secondaryLink}>
        Back
      </Link>
    </div>
  );
}
