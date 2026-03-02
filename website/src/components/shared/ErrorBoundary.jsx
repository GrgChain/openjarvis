import { Component } from 'react'

/**
 * Catches render errors in child components and shows a fallback
 * instead of blanking the entire page.
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-banner" style={{ margin: '12px' }}>
          <span className="error-banner-icon">⚠</span>
          <span>渲染出错：{this.state.error.message}</span>
        </div>
      )
    }
    return this.props.children
  }
}
