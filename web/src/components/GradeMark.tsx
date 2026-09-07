export default function GradeMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 60 34"
      className={className}
      aria-hidden="true"
      fill="none"
    >
      <path
        d="M2 19C4 8 12 2 20 3C30 4.2 26 15 17 15.5C10 15.8 9 9 15 7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.85"
      />
      <path
        d="M32 17L40 25L57 3"
        stroke="currentColor"
        strokeWidth="2.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
