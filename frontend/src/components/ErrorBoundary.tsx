import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-casino-bg flex items-center justify-center p-4">
          <div className="bg-casino-card border border-casino-border rounded-2xl p-8 max-w-md w-full text-center">
            <AlertTriangle size={48} className="mx-auto mb-4 text-red-500" />
            <h2 className="text-2xl font-bold mb-2 text-casino-gold">Something went wrong</h2>
            <p className="text-slate-400 mb-6">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <button
              onClick={this.handleReset}
              className="px-6 py-3 bg-casino-gold text-black rounded-lg font-semibold hover:opacity-90 transition-opacity flex items-center gap-2 mx-auto"
            >
              <RefreshCw size={18} />
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-6 py-3 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700 transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

