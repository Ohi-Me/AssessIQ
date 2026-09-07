export default function Stamp({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      aria-hidden="true"
      fill="none"
    >
      <circle
        cx="50"
        cy="50"
        r="42"
        stroke="currentColor"
        strokeWidth="2"
        opacity="0.8"
      />
      <circle
        cx="50"
        cy="50"
        r="35"
        stroke="currentColor"
        strokeWidth="1"
        opacity="0.5"
      />
      <path
        id="stamp-arc"
        d="M 50 15 A 35 35 0 0 1 85 50"
        fill="none"
      />
      <text
        fontSize="8.5"
        letterSpacing="2"
        fill="currentColor"
        opacity="0.85"
      >
        <textPath href="#stamp-arc" startOffset="2">
          VERIFIED
        </textPath>
      </text>
      <path
        d="M33 51l11 11 23-25"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
