import { useState, useEffect } from 'react'
import { api } from '../../api.js'
import { SpinnerCenter } from '../shared/Spinner.jsx'
import { ErrorBanner } from '../shared/ErrorBanner.jsx'
import '../../styles/workspace.css'

function formatSize(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

function fmtModified(ts) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleDateString()
}

function TreeNode({ node, depth = 0 }) {
  const isDir = node.type === 'directory'
  const [open, setOpen] = useState(depth < 2)

  const indent = Array.from({ length: depth }, (_, i) => (
    <span key={i} className="tree-indent" />
  ))

  return (
    <div className="tree-node">
      <div
        className="tree-row"
        data-dir={String(isDir)}
        onClick={() => isDir && setOpen((v) => !v)}
      >
        {indent}
        <span className="tree-toggle">
          {isDir ? (open ? '▾' : '▸') : ' '}
        </span>
        <span className="tree-icon">{isDir ? '📁' : '📄'}</span>
        <span className={`tree-name ${isDir ? 'dir' : 'file'}`}>
          {node.name}
        </span>
        <span className="tree-info">
          {isDir ? '' : formatSize(node.size)}
          {node.modified ? ` · ${fmtModified(node.modified)}` : ''}
        </span>
      </div>

      {isDir && open && node.children && (
        <div className="tree-children">
          {node.children.map((child, i) => (
            <TreeNode key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function WorkspacePanel() {
  const [tree, setTree] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.workspaceTree(4)
      .then((d) => setTree(d))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">📁 工作区</span>
      </div>
      <div className="panel-body">
        {loading && <SpinnerCenter />}
        {error && <ErrorBanner message={error} />}
        {!loading && !error && !tree && (
          <p className="workspace-empty">暂无工作区数据。</p>
        )}
        {!loading && !error && tree && (
          <div className="workspace-tree">
            {(tree.children ?? []).map((child, i) => (
              <TreeNode key={i} node={child} depth={0} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
