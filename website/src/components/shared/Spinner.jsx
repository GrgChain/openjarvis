export function Spinner({ size = '' }) {
  return <div className={`spinner ${size}`} />
}

export function SpinnerCenter({ size = '' }) {
  return (
    <div className="spinner-center">
      <Spinner size={size} />
    </div>
  )
}
