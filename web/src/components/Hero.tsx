import ChatDemo from "./ChatDemo";

export default function Hero() {
  return (
    <header className="relative">
      <nav className="relative z-10 mx-auto flex max-w-6xl items-center justify-between border-b border-border px-6 py-5">
        <span className="font-display text-lg tracking-tight">
          Assess<span className="italic">IQ</span>
        </span>
        <div className="flex items-center gap-7 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
          <a href="#how-it-works" className="hover:text-ink">
            How it works
          </a>
          <a href="#guardrails" className="hidden hover:text-ink sm:inline">
            Guardrails
          </a>
          <a href="#api" className="hover:text-ink">
            API
          </a>
          <a
            href="https://github.com/Ohi-Me/AssessIQ"
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink underline decoration-border underline-offset-4 hover:decoration-ink"
          >
            GitHub ↗
          </a>
        </div>
      </nav>

      <div className="relative mx-auto grid max-w-6xl gap-y-16 px-6 pb-16 pt-20 lg:grid-cols-[1.1fr_0.9fr] lg:gap-x-16 lg:pb-24">
        <div className="flex flex-col justify-center">
          <p className="label">Hiring assessments, retrieved not guessed</p>

          <h1 className="display mt-6 text-[3.25rem] sm:text-[4.5rem] lg:text-[5rem]">
            Describe
            <br />
            the hire.
            <br />
            Get the test.
          </h1>

          <p className="mt-8 max-w-lg text-[15px] leading-relaxed text-muted">
            A conversational agent that turns a plain-English hiring need into
            ranked, cited assessments from SHL&apos;s real catalog. It asks for
            the one signal it&apos;s missing instead of dumping a list — and it
            can only recommend what it actually retrieved.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <a
              href="#demo"
              className="bg-ink px-6 py-3 text-sm font-medium text-bg transition-opacity hover:opacity-85"
            >
              Try the live agent
            </a>
            <a
              href="#how-it-works"
              className="border border-border px-6 py-3 text-sm transition-colors hover:border-ink"
            >
              How it works
            </a>
          </div>
        </div>

        <figure className="flex flex-col lg:pt-2">
          <div className="h-[470px]" id="demo">
            <ChatDemo />
          </div>
          <figcaption className="mt-3 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-2">
            Fig. 1 — live endpoint, not a recording
          </figcaption>
        </figure>
      </div>
    </header>
  );
}
