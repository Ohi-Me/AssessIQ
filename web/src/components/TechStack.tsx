const STACK = [
  ["Framework", "FastAPI"],
  ["Embeddings", "all-MiniLM-L6-v2"],
  ["Vector search", "FAISS"],
  ["Keyword search", "BM25 (rank-bm25)"],
  ["Fusion", "Reciprocal Rank Fusion"],
  ["LLM", "Groq · llama-3.3-70b"],
  ["Fallback", "Gemini 2.0 Flash"],
  ["Typical latency", "2–5s"],
  ["Hard timeout", "25s"],
];

export default function TechStack() {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <p className="label rule-label">Stack</p>
        <dl className="mt-8 grid grid-cols-1 gap-x-14 sm:grid-cols-2 lg:grid-cols-3">
          {STACK.map(([label, value]) => (
            <div
              key={label}
              className="flex items-baseline justify-between gap-4 border-b border-border py-3"
            >
              <dt className="text-sm text-muted">{label}</dt>
              <dd className="text-right font-mono text-[13px]">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
