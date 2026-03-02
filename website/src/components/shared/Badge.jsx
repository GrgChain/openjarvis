/**
 * Badge component.
 * @param {Object} props
 * @param {string} props.color - 'green' | 'red' | 'blue' | 'gray'
 * @param {React.ReactNode} props.children
 */
export function Badge({ color = 'gray', children }) {
  return <span className={`badge ${color}`}>{children}</span>
}
