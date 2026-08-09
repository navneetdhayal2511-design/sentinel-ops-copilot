import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import Login from "./components/Login";
import Console from "./components/Console";

const TOKEN_KEY = "sentinel_token";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [user, setUser] = useState(null);
  const [bootError, setBootError] = useState("");
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.me(token);
        if (!cancelled) {
          setUser(me);
          setBootError("");
        }
      } catch (err) {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY);
          setToken("");
          setUser(null);
          setBootError(err.message || "Session expired");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const onLogin = async (email, password) => {
    const { access_token } = await api.login(email, password);
    localStorage.setItem(TOKEN_KEY, access_token);
    setToken(access_token);
  };

  const onLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setUser(null);
  };

  const content = useMemo(() => {
    if (loading) {
      return <div className="app-shell fade-up">Loading Sentinel…</div>;
    }
    if (!user) {
      return <Login onLogin={onLogin} error={bootError} />;
    }
    return <Console token={token} user={user} onLogout={onLogout} />;
  }, [loading, user, token, bootError]);

  return content;
}
