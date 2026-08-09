import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import "./console.css";

export default function Console({ token, user, onLogout }) {
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [investigations, setInvestigations] = useState([]);
  const [audit, setAudit] = useState([]);
  const [selected, setSelected] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [evalReport, setEvalReport] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "",
    service: "payments-api",
    severity: "high",
    message: "",
  });

  const refresh = useCallback(async () => {
    const [s, a, i, au] = await Promise.all([
      api.stats(token),
      api.alerts(token),
      api.investigations(token),
      api.audit(token),
    ]);
    setStats(s);
    setAlerts(a);
    setInvestigations(i);
    setAudit(au);
    if (!selected && i[0]) setSelected(i[0]);
  }, [token, selected]);

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, [refresh]);

  const runInvestigate = async (alertId) => {
    setBusyId(alertId);
    setError("");
    try {
      const inv = await api.investigate(token, alertId);
      setSelected(inv);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const runEval = async () => {
    setError("");
    try {
      const report = await api.runEval(token);
      setEvalReport(report);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const createAlert = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.createAlert(token, form);
      setForm({ title: "", service: "payments-api", severity: "high", message: "" });
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  const canAct = user.role === "admin" || user.role === "engineer";

  return (
    <div className="console app-shell">
      <header className="console-top fade-up">
        <div>
          <p className="eyebrow">Ops console</p>
          <h1 className="brand-mark">Sentinel</h1>
          <p className="sub">
            Signed in as {user.full_name} · {user.role}
          </p>
        </div>
        <div className="top-actions">
          {canAct && (
            <button type="button" className="ghost" onClick={runEval}>
              Run eval suite
            </button>
          )}
          <button type="button" className="ghost" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      {error && <p className="banner-error fade-up">{error}</p>}

      <section className="metrics fade-up delay-1" aria-label="Key metrics">
        <Metric label="Open alerts" value={stats?.open_alerts ?? "—"} />
        <Metric label="Critical" value={stats?.critical_alerts ?? "—"} hot />
        <Metric label="Investigations" value={stats?.investigations ?? "—"} />
        <Metric
          label="Avg confidence"
          value={stats ? `${Math.round(stats.avg_confidence * 100)}%` : "—"}
        />
      </section>

      <div className="console-grid fade-up delay-2">
        <section className="panel">
          <div className="panel-head">
            <h2>Alert inbox</h2>
            <span>{alerts.length} total</span>
          </div>
          <ul className="alert-list">
            {alerts.map((alert) => (
              <li key={alert.id}>
                <div>
                  <div className="alert-title-row">
                    <strong>{alert.title}</strong>
                    <span className={`sev ${alert.severity}`}>{alert.severity}</span>
                  </div>
                  <p>
                    {alert.service} · {alert.status}
                  </p>
                  <p className="muted">{alert.message}</p>
                </div>
                {canAct && (
                  <button
                    type="button"
                    onClick={() => runInvestigate(alert.id)}
                    disabled={busyId === alert.id}
                  >
                    {busyId === alert.id ? "Investigating…" : "Investigate"}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Investigation</h2>
            <span>{selected ? `#${selected.id}` : "none"}</span>
          </div>
          {!selected ? (
            <p className="muted">Run an investigation to see agent traces.</p>
          ) : (
            <div className="inv-detail">
              <p className="summary">{selected.summary}</p>
              <h3>Root cause</h3>
              <p>{selected.root_cause}</p>
              <h3>Recommended actions</h3>
              <pre>{selected.recommended_actions}</pre>
              <div className="meta-row">
                <span>{selected.model_name}</span>
                <span>{Math.round(selected.confidence * 100)}% conf</span>
                <span>{selected.latency_ms} ms</span>
              </div>
              <h3>Agent trace</h3>
              <ol className="trace">
                {(selected.traces || [])
                  .slice()
                  .sort((a, b) => a.step - b.step)
                  .map((t) => (
                    <li key={t.id || `${t.step}-${t.kind}`}>
                      <span className="trace-kind">{t.kind}</span>
                      <pre>{t.content}</pre>
                    </li>
                  ))}
              </ol>
            </div>
          )}
        </section>
      </div>

      <div className="console-grid secondary">
        {canAct && (
          <section className="panel">
            <div className="panel-head">
              <h2>Ingest alert</h2>
            </div>
            <form className="ingest" onSubmit={createAlert}>
              <input
                placeholder="Title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
              <select
                value={form.service}
                onChange={(e) => setForm({ ...form, service: e.target.value })}
              >
                <option value="payments-api">payments-api</option>
                <option value="auth-service">auth-service</option>
                <option value="checkout-web">checkout-web</option>
                <option value="ingest-worker">ingest-worker</option>
              </select>
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
              >
                <option value="critical">critical</option>
                <option value="high">high</option>
                <option value="medium">medium</option>
                <option value="low">low</option>
              </select>
              <textarea
                placeholder="Alert message / symptoms"
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                required
                rows={4}
              />
              <button type="submit">Create alert</button>
            </form>
          </section>
        )}

        <section className="panel">
          <div className="panel-head">
            <h2>Audit trail</h2>
          </div>
          <ul className="audit">
            {audit.map((ev) => (
              <li key={ev.id}>
                <span className="mono">{ev.action}</span>
                <span>
                  {ev.actor} — {ev.detail}
                </span>
              </li>
            ))}
          </ul>
        </section>

        {evalReport && (
          <section className="panel span-2">
            <div className="panel-head">
              <h2>Eval report</h2>
              <span>
                {evalReport.passed}/{evalReport.total} passed ·{" "}
                {Math.round(evalReport.accuracy * 100)}%
              </span>
            </div>
            <ul className="eval-list">
              {evalReport.results.map((r) => (
                <li key={r.case_id} className={r.passed ? "pass" : "fail"}>
                  <strong>{r.case_id}</strong>
                  <span>{r.passed ? "PASS" : "FAIL"}</span>
                  <p>{r.root_cause}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="panel span-2">
          <div className="panel-head">
            <h2>Recent investigations</h2>
          </div>
          <ul className="inv-list">
            {investigations.map((inv) => (
              <li key={inv.id}>
                <button type="button" className="linkish" onClick={() => setSelected(inv)}>
                  #{inv.id} · alert {inv.alert_id} · {Math.round(inv.confidence * 100)}%
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value, hot }) {
  return (
    <div className={`metric ${hot ? "hot" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
