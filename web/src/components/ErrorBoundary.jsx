import React from 'react';

// Catches render crashes in a subtree and shows a recovery panel instead of
// blanking the whole app (e.g. malformed ticket data from the API).
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    if (console?.error) console.error('UI crash contained:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="cl-drawer" role="alert">
          <h3>Something failed to render</h3>
          <p style={{ fontSize: 13, color: 'var(--ink-2)' }}>
            {this.props.message || 'This panel crashed. The rest of the app is fine.'}
          </p>
          <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', color: 'var(--ink-3)' }}>
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <button className="btn-ghost" onClick={() => this.setState({ error: null })}>
            Dismiss
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
