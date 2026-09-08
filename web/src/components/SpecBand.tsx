const SPECS = [
  { figure: "37", label: "assessments indexed" },
  { figure: "8", label: "test types covered" },
  { figure: "2", label: "retrievers fused" },
  { figure: "0", label: "invented URLs" },
];

export default function SpecBand() {
  return (
    <section className="bg-ink text-bg">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-y-10 px-6 py-14 sm:grid-cols-4">
        {SPECS.map(({ figure, label }) => (
          <div key={label}>
            <div className="display text-4xl sm:text-5xl">{figure}</div>
            <div className="mt-2 font-mono text-[11px] uppercase tracking-[0.14em] opacity-55">
              {label}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
