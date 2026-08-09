import { useState } from "react";
import "./login.css";

export default function Login({ onLogin, error }) {
  const [email, setEmail] = useState("admin@sentinel.dev");
  const [password, setPassword] = useState("admin123");
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setLocalError("");
    try {
      await onLogin(email, password);
    } catch (err) {
      setLocalError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-atmosphere" aria-hidden="true">
        <div className="scanline" />
      </div>
      <section className="login-hero fade-up">
        <p className="eyebrow">Incident intelligence</p>
        <h1 className="brand-mark">Sentinel</h1>
        <p className="lede">
          Triage alerts, investigate with an ops agent, and keep an audit trail you can defend.
        </p>
        <div className="signal" aria-hidden="true" />
      </section>

      <form className="login-form fade-up delay-1" onSubmit={submit}>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {(localError || error) && <p className="error">{localError || error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Enter console"}
        </button>
        <p className="hint">
          Demo: admin@sentinel.dev / admin123
        </p>
      </form>
    </div>
  );
}
