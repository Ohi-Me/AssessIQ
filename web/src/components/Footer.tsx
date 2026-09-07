export default function Footer() {
  return (
    <footer className="mx-auto max-w-6xl px-6 py-12">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <p className="text-sm text-muted">
          Built by{" "}
          <a
            href="https://github.com/Ohi-Me"
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink underline decoration-border hover:decoration-ink"
          >
            Rohit Kumar
          </a>
          .
        </p>
        <div className="flex items-center gap-5 font-mono text-xs uppercase tracking-wide text-muted">
          <a
            href="https://github.com/Ohi-Me/AssessIQ"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink"
          >
            Source
          </a>
          <a
            href="https://github.com/Ohi-Me/AssessIQ/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink"
          >
            MIT license
          </a>
        </div>
      </div>
    </footer>
  );
}
