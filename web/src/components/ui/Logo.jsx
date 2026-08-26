export default function Logo({ className = '' }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className={className}>
      <rect width="64" height="64" rx="16" fill="#e2a75b" />
      <circle cx="26" cy="32" r="11.5" fill="none" stroke="#09090b" strokeWidth="8" />
      <rect x="42.5" y="20" width="8.5" height="24" rx="2.5" fill="#09090b" />
    </svg>
  )
}
