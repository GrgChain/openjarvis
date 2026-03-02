import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const remarkPlugins = [remarkGfm]

// react-markdown v10: `inline` prop removed from code component.
// Detect inline code by absence of a language className.
function CodeBlock({ className, children, ...props }) {
  const isInline = !className
  return isInline ? (
    <code className="md-code-inline" {...props}>{children}</code>
  ) : (
    <code className={className} {...props}>{children}</code>
  )
}

function LinkNewTab({ href, children, ...props }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
  )
}

const components = { code: CodeBlock, a: LinkNewTab }

export function Markdown({ children }) {
  if (!children) return null
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        components={components}
      >
        {String(children)}
      </ReactMarkdown>
    </div>
  )
}
