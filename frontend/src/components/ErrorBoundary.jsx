import { Component } from "react";
import { useTranslation } from "react-i18next";

function ErrorFallback() {
  const { t } = useTranslation();
  return (
    <div role="alert" className="container-x py-24 text-center">
      <p className="font-display text-2xl font-semibold text-navy-900">{t("ui.refreshError")}</p>
      <p className="mt-2 text-muted">{t("ui.refreshText")}</p>
      <button onClick={() => window.location.reload()} className="mt-6 rounded-xl bg-navy-900 px-5 py-2.5 font-semibold text-white">
        {t("ui.refresh")}
      </button>
    </div>
  );
}

/** Contains render errors to the section that failed instead of blanking the page. */
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("UI error:", error, info?.componentStack);
  }

  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return <ErrorFallback />;
  }
}
