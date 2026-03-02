export function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="error-banner">
      <span className="error-banner-icon">⚠</span>
      <span>{message}</span>
    </div>
  )
}
