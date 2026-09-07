const STACK = [
  ["Framework", "FastAPI"],
  ["Embeddings", "all-MiniLM-L6-v2"],
  ["Vector search", "FAISS"],
  ["Keyword search", "BM25"],
  ["LLM", "Groq · llama-3.3-70b-versatile"],
  ["Fallback LLM", "Gemini 2.0 Flash"],
];

export default function TechStack() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
          Stack
        </p>
        <dl className="mt-6 grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          {STACK.map(([label, value]) => (
            <div
              key={label}
              className="flex items-baseline justify-between border-b border-border py-2"
            >
              <dt className="text-sm text-muted">{label}</dt>
              <dd className="font-mono text-sm">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
