const API = import.meta.env.VITE_API_URL || "";

function authHeaders(token) {
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

async function request(path, { token, method = "GET", body } = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: authHeaders(token),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  login: (email, password) =>
    request("/api/auth/login/json", { method: "POST", body: { email, password } }),
  me: (token) => request("/api/auth/me", { token }),
  stats: (token) => request("/api/stats", { token }),
  alerts: (token) => request("/api/alerts", { token }),
  investigations: (token) => request("/api/investigations", { token }),
  audit: (token) => request("/api/audit", { token }),
  investigate: (token, alertId) =>
    request(`/api/investigations/alerts/${alertId}/run`, {
      token,
      method: "POST",
      body: { use_llm: true },
    }),
  runEval: (token) => request("/api/eval/run?use_llm=false", { token, method: "POST" }),
  createAlert: (token, payload) =>
    request("/api/alerts", { token, method: "POST", body: payload }),
};
