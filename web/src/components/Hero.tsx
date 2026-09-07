import ChatDemo from "./ChatDemo";

export default function Hero() {
  return (
    <header className="relative overflow-hidden border-b border-border">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(to bottom, transparent, transparent 34px, var(--border) 34px, var(--border) 35px)",
          maskImage: "linear-gradient(to bottom, black, transparent 85%)",
        }}
      />

      <nav className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="font-display text-lg tracking-tight">
          Assess<span className="italic">IQ</span>
        </span>
        <div className="flex items-center gap-6 font-mono text-xs uppercase tracking-wide text-muted">
          <a href="#how-it-works" className="hover:text-ink">
            How it works
          </a>
          <a href="#api" className="hover:text-ink">
            API
          </a>
          <a
            href="https://github.com/Ohi-Me/AssessIQ"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded border border-border px-3 py-1.5 text-ink hover:border-ink"
          >
            GitHub ↗
          </a>
        </div>
      </nav>

      <div className="relative mx-auto grid max-w-6xl gap-14 px-6 pb-20 pt-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
            Conversational assessment recommender
          </p>
          <h1 className="mt-4 font-display text-[2.75rem] leading-[1.05] tracking-tight sm:text-6xl">
            Describe the hire.
            <br />
            Get the{" "}
            <span className="relative whitespace-nowrap">
              <span className="relative z-10">right assessment</span>
              <span
                aria-hidden="true"
                className="absolute inset-x-0 bottom-1 -z-0 h-3 bg-surface-2 sm:h-4"
              />
            </span>
            .
          </h1>
          <p className="mt-6 max-w-md text-base leading-relaxed text-muted">
            AssessIQ turns a plain-English hiring need into ranked, cited
            recommendations from SHL&apos;s real assessment catalog — asking
            one clarifying question at a time instead of dumping a list.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href="#demo"
              className="rounded-sm bg-ink px-5 py-2.5 text-sm font-medium text-bg"
            >
              Try it live →
            </a>
            <a
              href="#how-it-works"
              className="rounded-sm border border-border px-5 py-2.5 text-sm hover:border-ink"
            >
              See how it works
            </a>
          </div>
        </div>

        <div id="demo" className="h-[520px] scroll-mt-24">
          <ChatDemo />
        </div>
      </div>
    </header>
  );
}
