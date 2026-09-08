"use client";

import { useReveal } from "@/lib/useReveal";

const LEXICAL = [
  "Python (New)",
  "Data Analysis",
  "SQL (New)",
  "Microsoft Excel (New)",
];
const SEMANTIC = [
  "Graduate 8.0",
  "Technology Professional",
  "Verify Numerical",
  "Python (New)",
];
const FUSED = [
  "Python (New)",
  "Data Analysis",
  "Graduate 8.0",
  "Technology Professional",
];

const CONNECTORS: { col: "lex" | "sem"; rank: number; toRank: number }[] = [
  { col: "lex", rank: 0, toRank: 0 },
  { col: "sem", rank: 3, toRank: 0 },
  { col: "lex", rank: 1, toRank: 1 },
  { col: "sem", rank: 0, toRank: 2 },
  { col: "sem", rank: 1, toRank: 3 },
];

const ROW_Y = (rank: number) => 78 + rank * 66;
const BOX_H = 46;

const LEX = { left: 1, right: 267, mid: 134 };
const FUSED_X = { left: 336, right: 584, mid: 460 };
const SEM = { left: 653, right: 919, mid: 786 };

export default function FusionDiagram() {
  const { ref, visible } = useReveal<HTMLDivElement>(0.15);

  return (
    <div ref={ref} className="w-full">
      <p className="mb-6 text-sm text-muted">
        For the request{" "}
        <span className="text-ink">
          “Screening AI/ML interns for Python and data skills”
        </span>
        , each retriever hears something different:
      </p>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox="0 0 920 330"
          className="mx-auto min-w-[720px]"
          role="img"
          aria-label="For the query 'Screening AI/ML interns for Python and data skills', BM25 keyword search returns Python and data tests while FAISS semantic search returns early-career screening assessments. Reciprocal Rank Fusion combines them into one shortlist covering both the technical skills and the intern-level screening."
        >
          <text
            x={LEX.mid}
            y={14}
            textAnchor="middle"
            className="fill-ink font-mono text-[11px] uppercase tracking-[0.12em]"
          >
            BM25 · lexical
          </text>
          <text
            x={LEX.mid}
            y={34}
            textAnchor="middle"
            className="fill-muted text-[12px]"
          >
            matches the words
          </text>

          <text
            x={FUSED_X.mid}
            y={14}
            textAnchor="middle"
            className="fill-ink font-mono text-[11px] uppercase tracking-[0.12em]"
          >
            Fused · RRF
          </text>
          <text
            x={FUSED_X.mid}
            y={34}
            textAnchor="middle"
            className="fill-muted text-[12px]"
          >
            what the agent sees
          </text>

          <text
            x={SEM.mid}
            y={14}
            textAnchor="middle"
            className="fill-ink font-mono text-[11px] uppercase tracking-[0.12em]"
          >
            FAISS · semantic
          </text>
          <text
            x={SEM.mid}
            y={34}
            textAnchor="middle"
            className="fill-muted text-[12px]"
          >
            matches the meaning
          </text>

          {CONNECTORS.map((c, i) => {
            const fromX = c.col === "lex" ? LEX.right : SEM.left;
            const toX = c.col === "lex" ? FUSED_X.left : FUSED_X.right;
            const fromY = ROW_Y(c.rank);
            const toY = ROW_Y(c.toRank);
            const midX = (fromX + toX) / 2;
            const d = `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`;
            return (
              <path
                key={i}
                d={d}
                fill="none"
                className="stroke-ink"
                strokeWidth={2}
                strokeDasharray={c.col === "sem" ? "6 4" : undefined}
                style={{
                  strokeOpacity: visible ? 0.7 : 0,
                  transition: `stroke-opacity 600ms ease ${i * 90}ms`,
                }}
              />
            );
          })}

          {LEXICAL.map((name, rank) => (
            <g
              key={name + rank}
              style={{
                opacity: visible ? 1 : 0,
                transition: `opacity 500ms ease ${rank * 80}ms`,
              }}
            >
              <rect
                x={LEX.left}
                y={ROW_Y(rank) - BOX_H / 2}
                width={LEX.right - LEX.left}
                height={BOX_H}
                rx={3}
                className="fill-bg stroke-ink"
                strokeOpacity={0.75}
              />
              <text
                x={LEX.mid}
                y={ROW_Y(rank)}
                textAnchor="middle"
                dominantBaseline="central"
                className="fill-ink text-[14px]"
              >
                {name}
              </text>
            </g>
          ))}

          {SEMANTIC.map((name, rank) => (
            <g
              key={name + rank}
              style={{
                opacity: visible ? 1 : 0,
                transition: `opacity 500ms ease ${rank * 80}ms`,
              }}
            >
              <rect
                x={SEM.left}
                y={ROW_Y(rank) - BOX_H / 2}
                width={SEM.right - SEM.left}
                height={BOX_H}
                rx={3}
                className="fill-surface stroke-ink"
                strokeDasharray="5 3"
                strokeOpacity={0.75}
              />
              <text
                x={SEM.mid}
                y={ROW_Y(rank)}
                textAnchor="middle"
                dominantBaseline="central"
                className="fill-ink text-[14px]"
              >
                {name}
              </text>
            </g>
          ))}

          {FUSED.map((name, rank) => (
            <g
              key={name + rank}
              style={{
                opacity: visible ? 1 : 0,
                transition: `opacity 500ms ease ${300 + rank * 100}ms`,
              }}
            >
              <rect
                x={FUSED_X.left}
                y={ROW_Y(rank) - BOX_H / 2}
                width={FUSED_X.right - FUSED_X.left}
                height={BOX_H}
                rx={3}
                className={
                  rank === 0 ? "fill-ink stroke-ink" : "fill-bg stroke-ink"
                }
              />
              <text
                x={FUSED_X.mid}
                y={ROW_Y(rank)}
                textAnchor="middle"
                dominantBaseline="central"
                className={
                  rank === 0
                    ? "fill-bg text-[14px] font-medium"
                    : "fill-ink text-[14px] font-medium"
                }
              >
                {name}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
