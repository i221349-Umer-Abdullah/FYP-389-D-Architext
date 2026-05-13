"use client";

import { FormEvent, useRef, useState } from "react";
import gsap from "gsap";
import clsx from "clsx";

import styles from "./PromptBar.module.css";

interface PromptBarProps {
  onSubmit: (prompt: string) => Promise<void> | void;
  disabled?: boolean;
  placeholder?: string;
  buttonLabel?: string;
  className?: string;
  multiline?: boolean;
}

export function PromptBar({
  onSubmit,
  disabled,
  placeholder = "Design a four-bedroom floor plan with a central courtyard and daylight-first circulation.",
  buttonLabel = "Generate",
  className,
  multiline = false,
}: PromptBarProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const shellRef    = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const formRef     = useRef<HTMLFormElement | null>(null);

  const animateFocusState = (isFocused: boolean) => {
    if (!shellRef.current) return;
    const wideViewport = window.matchMedia("(min-width: 960px)").matches;
    gsap.to(shellRef.current, {
      maxWidth: wideViewport ? (isFocused ? 940 : 900) : "100%",
      boxShadow: isFocused
        ? "0 18px 56px rgba(10, 10, 10, 0.12), 0 0 0 1px rgba(10, 10, 10, 0.45)"
        : "0 10px 34px rgba(10, 10, 10, 0.08), 0 0 0 1px rgba(10, 10, 10, 0.18)",
      duration: 0.42,
      ease: "power3.out",
      overwrite: "auto",
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleaned = value.trim();
    if (!cleaned) {
      setError("Describe your floor plan intent to continue.");
      return;
    }
    setError("");
    await onSubmit(cleaned);
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  };

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter submits; Shift+Enter inserts newline
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  return (
    <form ref={formRef} className={clsx(styles.form, className)} onSubmit={handleSubmit}>
      <div ref={shellRef} className={clsx(styles.shell, multiline && styles.shellMultiline)}>
        <label className={styles.label} htmlFor="prompt-input">
          Floor plan prompt
        </label>

        {multiline ? (
          <textarea
            ref={textareaRef}
            id="prompt-input"
            className={clsx(styles.input, styles.textarea)}
            value={value}
            onFocus={() => animateFocusState(true)}
            onBlur={() => animateFocusState(false)}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError("");
              autoResize();
            }}
            onKeyDown={handleTextareaKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "prompt-error" : undefined}
            rows={3}
          />
        ) : (
          <input
            id="prompt-input"
            className={styles.input}
            value={value}
            onFocus={() => animateFocusState(true)}
            onBlur={() => animateFocusState(false)}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError("");
            }}
            placeholder={placeholder}
            disabled={disabled}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "prompt-error" : undefined}
          />
        )}

        <button className={clsx(styles.button, multiline && styles.buttonMultiline)} type="submit" disabled={disabled}>
          {buttonLabel}
        </button>
      </div>
      <p id="prompt-error" className={styles.error} aria-live="polite">
        {error}
      </p>
    </form>
  );
}
