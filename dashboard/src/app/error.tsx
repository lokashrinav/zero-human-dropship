"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="error-shell">
      <p className="eyebrow">CONTROL ROOM DEGRADED</p>
      <h1>The company feeds are temporarily unavailable.</h1>
      <p>The dashboard can reconnect without interrupting the underlying workflow.</p>
      <button className="primary-button" type="button" onClick={reset}>
        Reconnect dashboard
      </button>
    </main>
  );
}
