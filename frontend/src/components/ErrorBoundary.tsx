import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('UI render error', error, info)
  }

  private handleReset = (): void => {
    this.setState({ hasError: false })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <section className="rounded-xl border border-red-500/30 bg-red-500/10 p-6" role="alert" aria-live="assertive">
          <h2 className="text-lg font-semibold text-red-200">Something went wrong in the dashboard view</h2>
          <p className="mt-2 text-sm text-red-100">Try reloading this section. If the error persists, refresh the page.</p>
          <button
            type="button"
            onClick={this.handleReset}
            className="mt-4 rounded-lg border border-red-400/40 px-4 py-2 text-sm font-medium text-red-100 transition-colors duration-200 hover:bg-red-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300"
          >
            Retry view
          </button>
        </section>
      )
    }

    return this.props.children
  }
}
