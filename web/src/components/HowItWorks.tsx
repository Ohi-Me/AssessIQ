import FusionDiagram from "./FusionDiagram";
import Stamp from "./Stamp";

const STAGES = [
  {
    n: "01",
    title: "Guardrails",
    body: "Classifies intent per turn — clarify, recommend, refine, compare, or refuse. Blocks prompt-injection attempts and off-topic requests before they reach retrieval.",
  },
  {
    n: "03",
    title: "LLM generation",
    body: "Grounded strictly in the retrieved catalog entries — the model is instructed to only reference assessments it was shown, never invent one.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-b border-border bg-surface">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
          Architecture
        </p>
        <h2 className="mt-3 max-w-xl font-display text-3xl tracking-tight sm:text-4xl">
          Four stages, one request.
        </h2>

        <div className="mt-16 grid gap-x-10 gap-y-12 lg:grid-cols-2">
          <StageCard {...STAGES[0]} />

          <div className="rounded-md border border-border bg-bg p-6 lg:row-span-2">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-sm text-muted-2">02</span>
              <h3 className="font-display text-xl">Hybrid retrieval</h3>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              BM25 keyword search and FAISS semantic search run independently,
              then merge via{" "}
              <span className="text-ink">Reciprocal Rank Fusion</span> —
              boosted by seniority, skill, and test-type match. An item that
              ranks well on both sides wins.
            </p>
            <div className="mt-8">
              <FusionDiagram />
            </div>
          </div>

          <StageCard {...STAGES[1]} />

          <div className="rounded-md border border-border bg-bg p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-sm text-muted-2">04</span>
                  <h3 className="font-display text-xl">Validator</h3>
                </div>
                <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
                  Last stop before the response leaves the service: every
                  URL is checked against the real catalog, invalid entries
                  are dropped, results capped at 10.
                </p>
              </div>
              <Stamp className="h-16 w-16 shrink-0 -rotate-6 text-ink opacity-80" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function StageCard({
  n,
  title,
  body,
}: {
  n: string;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-md border border-border bg-bg p-6">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-sm text-muted-2">{n}</span>
        <h3 className="font-display text-xl">{title}</h3>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
    </div>
  );
}
