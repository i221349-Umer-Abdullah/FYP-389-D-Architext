import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "architext_prompt_history";
const MAX_ENTRIES = 15;

export function usePromptHistory() {
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setHistory(JSON.parse(stored) as string[]);
    } catch {
      // ignore parse errors
    }
  }, []);

  const addEntry = useCallback((prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed) return;
    setHistory((prev) => {
      const deduped = [trimmed, ...prev.filter((p) => p !== trimmed)].slice(0, MAX_ENTRIES);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(deduped));
      } catch {
        // ignore quota errors
      }
      return deduped;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return { history, addEntry, clearHistory };
}
