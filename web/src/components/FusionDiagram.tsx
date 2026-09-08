"use client";

import { useReveal } from "@/lib/useReveal";

const LEXICAL = ["Core Java", "Java 8 (New)", "SQL Server", "Selenium"];
const SEMANTIC = ["Java 8 (New)", "OPQ32r", "Verify - Numerical", "Core Java"];
const FUSED = ["Java 8 (New)", "Core Java", "OPQ32r", "SQL Server"];

const CONNECTORS: { col: "lex" | "sem"; rank: number; toRank: number }[] = [
  { col: "lex", rank: 1, toRank: 0 },
  { col: "sem", rank: 0, toRank: 0 },
  { col: "lex", rank: 0, toRank: 1 },
  { col: "sem", rank: 3, toRank: 1 },
  { col: "sem", rank: 1, toRank: 2 },
  { col: "lex", rank: 2, toRank: 3 },
];

const ROW_Y = (rank: number) => 44 + rank * 70;
const BOX_H = 46;

const LEX_X = { boxLeft: 16, boxRight: 236, textX: 126 };
const FUSED_X = { boxLeft: 310, boxRight: 470, textX: 390 };
const SEM_X = { boxLeft: 544, boxRight: 764, textX: 654 };

export default function FusionDiagram() {
  const { ref, visible } = useReveal<HTMLDivElement>(0.15);

  return (
    <div ref={ref} className="w-full overflow-x-auto">
      <svg
        viewBox="0 0 780 320"
        className="mx-auto min-w-[640px]"
        role="img"
        aria-label="Diagram showing BM25 keyword results (solid) and FAISS semantic results (dashed) converging into one fused, ranked list via Reciprocal Rank Fusion"
      >
        <text
          x={LEX_X.textX}
          y={20}
          textAnchor="middle"
          className="fill-muted font-mono text-[11px] uppercase tracking-wide"
        >
          BM25 · lexical
        </text>
        <text
          x={FUSED_X.textX}
          y={20}
          textAnchor="middle"
          className="fill-muted font-mono text-[11px] uppercase tracking-wide"
        >
          Fused (RRF)
        </text>
        <text
          x={SEM_X.textX}
          y={20}
          textAnchor="middle"
          className="fill-muted font-mono text-[11px] uppercase tracking-wide"
        >
          FAISS · semantic
        </text>

        {CONNECTORS.map((c, i) => {
          const fromX = c.col === "lex" ? LEX_X.boxRight : SEM_X.boxLeft;
          const toX = c.col === "lex" ? FUSED_X.boxLeft : FUSED_X.boxRight;
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
                strokeOpacity: visible ? 0.75 : 0,
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
              transform: visible ? "translateX(0)" : "translateX(-8px)",
              transition: `opacity 500ms ease ${rank * 80}ms, transform 500ms ease ${rank * 80}ms`,
            }}
          >
            <rect
              x={LEX_X.boxLeft}
              y={ROW_Y(rank) - BOX_H / 2}
              width={LEX_X.boxRight - LEX_X.boxLeft}
              height={BOX_H}
              rx={4}
              className="fill-bg stroke-ink"
              strokeOpacity={0.7}
            />
            <text
              x={LEX_X.textX}
              y={ROW_Y(rank) + 4}
              textAnchor="middle"
              className="fill-ink text-[13px]"
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
              transform: visible ? "translateX(0)" : "translateX(8px)",
              transition: `opacity 500ms ease ${rank * 80}ms, transform 500ms ease ${rank * 80}ms`,
            }}
          >
            <rect
              x={SEM_X.boxLeft}
              y={ROW_Y(rank) - BOX_H / 2}
              width={SEM_X.boxRight - SEM_X.boxLeft}
              height={BOX_H}
              rx={4}
              className="fill-surface stroke-ink"
              strokeDasharray="4 3"
              strokeOpacity={0.7}
            />
            <text
              x={SEM_X.textX}
              y={ROW_Y(rank) + 4}
              textAnchor="middle"
              className="fill-ink text-[13px]"
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
              x={FUSED_X.boxLeft}
              y={ROW_Y(rank) - BOX_H / 2}
              width={FUSED_X.boxRight - FUSED_X.boxLeft}
              height={BOX_H}
              rx={4}
              className={
                rank === 0 ? "fill-ink stroke-ink" : "fill-bg stroke-ink"
              }
            />
            <text
              x={FUSED_X.textX}
              y={ROW_Y(rank) + 4}
              textAnchor="middle"
              className={
                rank === 0
                  ? "fill-bg text-[13px] font-medium"
                  : "fill-ink text-[13px] font-medium"
              }
            >
              {name}
            </text>
          </g>
        ))}

        <g
          style={{
            opacity: visible ? 1 : 0,
            transition: "opacity 500ms ease 900ms",
          }}
        >
          <path
            d="M441 44 l5 6 l11 -14"
            fill="none"
            className="stroke-bg"
            strokeWidth={2.25}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
      </svg>
    </div>
  );
}
