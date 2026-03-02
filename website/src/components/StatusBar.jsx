export function StatusBar({ online, checkedAt }) {
  const label = online === null
    ? '检测中…'
    : online
      ? '服务在线'
      : '服务离线'

  const dotClass = online === null ? '' : online ? 'online' : 'offline'

  return (
    <div className="status-bar">
      <span className={`status-dot ${dotClass}`} />
      <span>{label}</span>
      {checkedAt && (
        <span style={{ marginLeft: 'auto' }}>
          更新于 {checkedAt.toLocaleTimeString()}
        </span>
      )}
    </div>
  )
}
