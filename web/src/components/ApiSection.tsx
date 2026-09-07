const REQUEST = `curl -X POST https://assessiq1.onrender.com/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "messages": [
      { "role": "user", "content": "Hiring a Java developer who works with stakeholders" }
    ]
  }'`;

const RESPONSE = `{
  "reply": "For a mid-level Java developer who works with stakeholders, Java 8 (New) evaluates OOP, collections, and backend Java fundamentals.",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/.../java-8-new/",
      "test_type": "K",
      "score": 1.0,
      "reason": "Assesses modern Java 8 concepts relevant for backend development."
    }
  ],
  "end_of_conversation": true
}`;

export default function ApiSection() {
  return (
    <section id="api" className="border-b border-border bg-surface">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
          For developers
        </p>
        <h2 className="mt-3 max-w-xl font-display text-3xl tracking-tight sm:text-4xl">
          One endpoint. Full history in, next reply out.
        </h2>
        <p className="mt-4 max-w-xl text-sm leading-relaxed text-muted">
          Stateless by design — send the whole conversation each time, get
          the agent&apos;s next turn back. No sessions to manage.
        </p>

        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <CodeBlock label="Request" code={REQUEST} />
          <CodeBlock label="Response" code={RESPONSE} />
        </div>

        <a
          href="https://github.com/Ohi-Me/AssessIQ#api-reference"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-block text-sm underline decoration-border hover:decoration-ink"
        >
          Full API reference ↗
        </a>
      </div>
    </section>
  );
}

function CodeBlock({ label, code }: { label: string; code: string }) {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-bg">
      <div className="border-b border-border px-4 py-2.5 font-mono text-xs uppercase tracking-wide text-muted">
        {label}
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[13px] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
