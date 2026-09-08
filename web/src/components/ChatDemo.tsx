"use client";

import { useEffect, useRef, useState } from "react";
import {
  BackendUnreachableError,
  ChatMessage,
  Recommendation,
  TEST_TYPE_LABELS,
  sendChat,
} from "@/lib/api";
import GradeMark from "./GradeMark";

const STARTERS = [
  "Hiring an SDE intern — need to test coding and problem solving",
  "Screening AI/ML interns for Python and data skills",
  "Campus hiring for graduate engineers, mix of aptitude and coding",
];

const WAKE_UP_MS = 6000;
const GIVE_UP_MS = 90000;

interface Turn {
  message: ChatMessage;
  recommendations?: Recommendation[];
}

export default function ChatDemo() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<
    "idle" | "sending" | "waking" | "error"
  >("idle");
  const [ended, setEnded] = useState(false);
  const [errorText, setErrorText] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const wakeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, status]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || status === "sending" || status === "waking") return;

    const nextTurns: Turn[] = [...turns, { message: { role: "user", content: trimmed } }];
    setTurns(nextTurns);
    setInput("");
    setStatus("sending");
    setErrorText("");

    wakeTimer.current = setTimeout(() => setStatus("waking"), WAKE_UP_MS);

    const controller = new AbortController();
    const giveUp = setTimeout(() => controller.abort(), GIVE_UP_MS);

    try {
      const res = await sendChat(
        nextTurns.map((t) => t.message),
        controller.signal,
      );
      setTurns([
        ...nextTurns,
        {
          message: { role: "assistant", content: res.reply },
          recommendations: res.recommendations,
        },
      ]);
      setEnded(res.end_of_conversation && res.recommendations.length > 0);
      setStatus("idle");
    } catch (err) {
      if (err instanceof BackendUnreachableError) {
        setErrorText(
          "Couldn't reach the assessment engine. It's hosted on Render's free tier and sleeps after inactivity — first request can take up to a minute. Try again.",
        );
      } else if (err instanceof DOMException && err.name === "AbortError") {
        setErrorText(
          "Still no response after a while. The server may be waking from sleep — give it another try.",
        );
      } else {
        setErrorText("Something went wrong on this end. Try again.");
      }
      setStatus("error");
    } finally {
      if (wakeTimer.current) clearTimeout(wakeTimer.current);
      clearTimeout(giveUp);
    }
  }

  function reset() {
    setTurns([]);
    setEnded(false);
    setStatus("idle");
    setErrorText("");
  }

  const busy = status === "sending" || status === "waking";

  return (
    <div className="flex h-full flex-col overflow-hidden border border-border bg-bg">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <span className="font-mono text-xs text-muted">POST /chat</span>
        <span className="ml-auto flex items-center gap-1.5 font-mono text-[11px] text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-ink" />
          live
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto px-4 py-4"
        aria-live="polite"
      >
        {turns.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm text-muted">
              Try a real hiring need — the same request a recruiter would
              type.
            </p>
            <div className="flex flex-col gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="border border-border bg-surface px-3 py-2 text-left text-sm transition-colors hover:border-ink"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className="space-y-3">
            <div
              className={
                t.message.role === "user"
                  ? "ml-auto max-w-[85%] bg-ink px-4 py-2.5 text-sm text-bg"
                  : "mr-auto max-w-[90%] border border-border bg-surface px-4 py-2.5 text-sm"
              }
            >
              {t.message.content}
            </div>

            {t.recommendations && t.recommendations.length > 0 && (
              <ul className="space-y-2">
                {t.recommendations.map((r, idx) => (
                  <li
                    key={r.name}
                    className="relative border border-border bg-bg p-3"
                  >
                    {idx === 0 && (
                      <GradeMark className="absolute -right-2 -top-4 h-7 w-12 text-ink" />
                    )}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{r.name}</span>
                          <span className="border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
                            {r.test_type} ·{" "}
                            {TEST_TYPE_LABELS[r.test_type] ?? "Assessment"}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-muted">{r.reason}</p>
                        <a
                          href={r.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 inline-block text-xs underline decoration-border hover:decoration-ink"
                        >
                          View assessment ↗
                        </a>
                      </div>
                      <span className="shrink-0 font-mono text-xs text-muted">
                        {r.score.toFixed(2)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {busy && (
          <div className="mr-auto flex max-w-[80%] items-center gap-2 border border-border bg-surface px-4 py-3">
            <span className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted" />
            </span>
            {status === "waking" && (
              <span className="text-xs text-muted">
                Waking the server up — free-tier cold start, ~30&ndash;60s
              </span>
            )}
          </div>
        )}

        {status === "error" && (
          <div className="border border-danger/40 bg-danger/5 px-4 py-3 text-sm text-danger">
            {errorText}
          </div>
        )}
      </div>

      <div className="border-t border-border p-3">
        {ended ? (
          <button
            onClick={reset}
            className="w-full bg-ink px-4 py-2.5 text-sm font-medium text-bg"
          >
            Start a new conversation
          </button>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe who you're hiring…"
              disabled={busy}
              className="flex-1 border border-border bg-surface px-3 py-2.5 text-sm placeholder:text-muted-2 focus:border-ink"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="bg-ink px-4 py-2.5 text-sm font-medium text-bg disabled:opacity-30"
            >
              Send
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
