const REQUEST = `curl -X POST https://assessiq1.onrender.com/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "messages": [
      { "role": "user", "content": "Hiring an SDE intern to test coding and problem solving" }
    ]
  }'`;

const RESPONSE = `{
  "reply": "For an SDE intern, Core Java covers OOP and data structures, while Automata — Fix the Code tests real debugging under time pressure.",
  "recommendations": [
    {
      "name": "Core Java",
      "url": "https://.../product-catalog/view/core-java/",
      "test_type": "K",
      "score": 1.0,
      "reason": "Evaluates Java fundamentals, OOP, collections, and data structures."
    }
  ],
  "end_of_conversation": true
}`;

export default function ApiSection() {
  return (
    <section id="api" className="border-b border-border bg-surface">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <p className="label rule-label">For developers</p>
        <h2 className="display mt-10 max-w-xl text-3xl sm:text-4xl">
          One endpoint. History in, next turn out.
        </h2>
        <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-muted">
          Stateless by design — send the whole conversation each time and get
          the agent&apos;s next turn back. No sessions to manage on either side.
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
    <div className="overflow-hidden border border-border bg-bg">
      <div className="border-b border-border px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
        {label}
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[13px] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
