import FusionDiagram from "./FusionDiagram";

const STAGES = [
  {
    n: "01",
    title: "Guardrails",
    body: "Classifies intent per turn — clarify, recommend, refine, compare, or refuse. Injection attempts and off-topic requests stop here.",
  },
  {
    n: "02",
    title: "Hybrid retrieval",
    body: "BM25 and FAISS search the catalog independently, then merge via Reciprocal Rank Fusion, boosted on seniority, skill, and test-type match.",
  },
  {
    n: "03",
    title: "LLM generation",
    body: "Groq's gpt-oss-120b writes the reply, grounded strictly in the retrieved entries. Gemini 2.5 Flash covers the fallback path.",
  },
  {
    n: "04",
    title: "Validation",
    body: "Every URL is checked against the real catalog, unverifiable entries are dropped, and the list is capped at ten.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-b border-border bg-surface">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <p className="label rule-label">Architecture</p>

        <h2 className="display mt-10 max-w-lg text-3xl sm:text-4xl">
          Four stages between a sentence and a shortlist.
        </h2>

        <ol className="mt-14 grid gap-x-12 gap-y-10 sm:grid-cols-2">
          {STAGES.map((s) => (
            <li key={s.n} className="flex gap-5">
              <span className="mt-1 font-mono text-[11px] tracking-[0.14em] text-muted-2">
                {s.n}
              </span>
              <div className="flex-1 border-t border-border pt-3">
                <h3 className="font-display text-lg">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">
                  {s.body}
                </p>
              </div>
            </li>
          ))}
        </ol>

        <figure className="mt-20 border border-border bg-bg p-6 sm:p-10">
          <FusionDiagram />
          <figcaption className="mt-8 border-t border-border pt-4 text-sm leading-relaxed text-muted">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-2">
              Fig. 2 —{" "}
            </span>
            Keyword search locks onto &ldquo;Python&rdquo; and
            &ldquo;data&rdquo; — and drags in Excel along the way; semantic
            search understands this is intern screening but ranks the Python
            test lower. Fusion covers both, and Python (New) — strong on each
            side — goes to the top.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
