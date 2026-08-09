const TOKEN_KEY = "sentinel_token";
const app = document.getElementById("app");

const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  user: null,
  stats: null,
  alerts: [],
  investigations: [],
  audit: [],
  selected: null,
  evalReport: null,
  error: "",
  busyId: null,
};

async function api(path, { method = "GET", body, token } = {}) {
  const res = await fetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
  return data;
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderLogin(error = "") {
  app.innerHTML = `
    <div class="login-page">
      <div class="login-atmosphere" aria-hidden="true"><div class="scanline"></div></div>
      <section class="login-hero fade-up">
        <p class="eyebrow">Incident intelligence</p>
        <h1 class="brand-mark">Sentinel</h1>
        <p class="lede">Triage alerts, investigate with an ops agent, and keep an audit trail you can defend.</p>
        <div class="signal" aria-hidden="true"></div>
      </section>
      <form class="login-form fade-up delay-1" id="login-form">
        <label>Email<input name="email" value="admin@sentinel.dev" autocomplete="username" /></label>
        <label>Password<input name="password" type="password" value="admin123" autocomplete="current-password" /></label>
        ${error ? `<p class="error">${esc(error)}</p>` : ""}
        <button type="submit">Enter console</button>
        <p class="hint">Demo: admin@sentinel.dev / admin123</p>
      </form>
    </div>
  `;
  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const tok = await api("/api/auth/login/json", {
        method: "POST",
        body: { email: fd.get("email"), password: fd.get("password") },
      });
      state.token = tok.access_token;
      localStorage.setItem(TOKEN_KEY, state.token);
      await boot();
    } catch (err) {
      renderLogin(err.message);
    }
  });
}

function metric(label, value, hot = false) {
  return `<div class="metric ${hot ? "hot" : ""}"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
}

function renderConsole() {
  const canAct = state.user.role === "admin" || state.user.role === "engineer";
  const selected = state.selected;
  const traces = (selected?.traces || []).slice().sort((a, b) => a.step - b.step);

  app.innerHTML = `
    <div class="console app-shell">
      <header class="console-top fade-up">
        <div>
          <p class="eyebrow">Ops console</p>
          <h1 class="brand-mark">Sentinel</h1>
          <p class="sub">Signed in as ${esc(state.user.full_name)} · ${esc(state.user.role)}</p>
        </div>
        <div class="top-actions">
          ${canAct ? `<button type="button" class="ghost" id="btn-eval">Run eval suite</button>` : ""}
          <button type="button" class="ghost" id="btn-logout">Sign out</button>
        </div>
      </header>
      ${state.error ? `<p class="banner-error fade-up">${esc(state.error)}</p>` : ""}
      <section class="metrics fade-up delay-1">
        ${metric("Open alerts", state.stats?.open_alerts ?? "—")}
        ${metric("Critical", state.stats?.critical_alerts ?? "—", true)}
        ${metric("Investigations", state.stats?.investigations ?? "—")}
        ${metric("Avg confidence", state.stats ? `${Math.round(state.stats.avg_confidence * 100)}%` : "—")}
      </section>
      <div class="console-grid fade-up delay-2">
        <section class="panel">
          <div class="panel-head"><h2>Alert inbox</h2><span>${state.alerts.length} total</span></div>
          <ul class="alert-list">
            ${state.alerts
              .map(
                (a) => `
              <li>
                <div>
                  <div class="alert-title-row">
                    <strong>${esc(a.title)}</strong>
                    <span class="sev ${esc(a.severity)}">${esc(a.severity)}</span>
                  </div>
                  <p>${esc(a.service)} · ${esc(a.status)}</p>
                  <p class="muted">${esc(a.message)}</p>
                </div>
                ${
                  canAct
                    ? `<button type="button" data-investigate="${a.id}" ${
                        state.busyId === a.id ? "disabled" : ""
                      }>${state.busyId === a.id ? "Investigating…" : "Investigate"}</button>`
                    : ""
                }
              </li>`
              )
              .join("")}
          </ul>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>Investigation</h2><span>${selected ? `#${selected.id}` : "none"}</span></div>
          ${
            !selected
              ? `<p class="muted">Run an investigation to see agent traces.</p>`
              : `
            <div class="inv-detail">
              <p class="summary">${esc(selected.summary)}</p>
              <h3>Root cause</h3>
              <p>${esc(selected.root_cause)}</p>
              <h3>Recommended actions</h3>
              <pre>${esc(selected.recommended_actions)}</pre>
              <div class="meta-row">
                <span>${esc(selected.model_name)}</span>
                <span>${Math.round(selected.confidence * 100)}% conf</span>
                <span>${selected.latency_ms} ms</span>
              </div>
              <h3>Agent trace</h3>
              <ol class="trace">
                ${traces
                  .map(
                    (t) => `
                  <li>
                    <span class="trace-kind">${esc(t.kind)}</span>
                    <pre>${esc(t.content)}</pre>
                  </li>`
                  )
                  .join("")}
              </ol>
            </div>`
          }
        </section>
      </div>
      <div class="console-grid secondary">
        ${
          canAct
            ? `<section class="panel">
          <div class="panel-head"><h2>Ingest alert</h2></div>
          <form class="ingest" id="ingest-form">
            <input name="title" placeholder="Title" required />
            <select name="service">
              <option value="payments-api">payments-api</option>
              <option value="auth-service">auth-service</option>
              <option value="checkout-web">checkout-web</option>
              <option value="ingest-worker">ingest-worker</option>
            </select>
            <select name="severity">
              <option value="critical">critical</option>
              <option value="high" selected>high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
            <textarea name="message" rows="4" placeholder="Alert message / symptoms" required></textarea>
            <button type="submit">Create alert</button>
          </form>
        </section>`
            : ""
        }
        <section class="panel">
          <div class="panel-head"><h2>Audit trail</h2></div>
          <ul class="audit">
            ${state.audit
              .map(
                (ev) => `
              <li>
                <span class="mono">${esc(ev.action)}</span>
                <span>${esc(ev.actor)} — ${esc(ev.detail)}</span>
              </li>`
              )
              .join("")}
          </ul>
        </section>
        ${
          state.evalReport
            ? `<section class="panel span-2">
          <div class="panel-head">
            <h2>Eval report</h2>
            <span>${state.evalReport.passed}/${state.evalReport.total} passed · ${Math.round(
                state.evalReport.accuracy * 100
              )}%</span>
          </div>
          <ul class="eval-list">
            ${state.evalReport.results
              .map(
                (r) => `
              <li class="${r.passed ? "pass" : "fail"}">
                <strong>${esc(r.case_id)}</strong>
                <span>${r.passed ? "PASS" : "FAIL"}</span>
                <p>${esc(r.root_cause)}</p>
              </li>`
              )
              .join("")}
          </ul>
        </section>`
            : ""
        }
        <section class="panel span-2">
          <div class="panel-head"><h2>Recent investigations</h2></div>
          <ul class="inv-list">
            ${state.investigations
              .map(
                (inv) => `
              <li>
                <button type="button" class="linkish" data-select-inv="${inv.id}">
                  #${inv.id} · alert ${inv.alert_id} · ${Math.round(inv.confidence * 100)}%
                </button>
              </li>`
              )
              .join("")}
          </ul>
        </section>
      </div>
    </div>
  `;

  document.getElementById("btn-logout")?.addEventListener("click", () => {
    localStorage.removeItem(TOKEN_KEY);
    state.token = "";
    state.user = null;
    renderLogin();
  });

  document.getElementById("btn-eval")?.addEventListener("click", async () => {
    try {
      state.error = "";
      state.evalReport = await api("/api/eval/run?use_llm=false", {
        method: "POST",
        token: state.token,
      });
      await refresh();
    } catch (err) {
      state.error = err.message;
      renderConsole();
    }
  });

  document.querySelectorAll("[data-investigate]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.getAttribute("data-investigate"));
      state.busyId = id;
      state.error = "";
      renderConsole();
      try {
        state.selected = await api(`/api/investigations/alerts/${id}/run`, {
          method: "POST",
          token: state.token,
          body: { use_llm: true },
        });
        await refresh();
      } catch (err) {
        state.error = err.message;
        state.busyId = null;
        renderConsole();
      }
    });
  });

  document.querySelectorAll("[data-select-inv]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.getAttribute("data-select-inv"));
      state.selected = state.investigations.find((i) => i.id === id) || null;
      renderConsole();
    });
  });

  document.getElementById("ingest-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api("/api/alerts", {
        method: "POST",
        token: state.token,
        body: {
          title: fd.get("title"),
          service: fd.get("service"),
          severity: fd.get("severity"),
          message: fd.get("message"),
          source: "console",
        },
      });
      await refresh();
    } catch (err) {
      state.error = err.message;
      renderConsole();
    }
  });
}

async function refresh() {
  const [stats, alerts, investigations, audit] = await Promise.all([
    api("/api/stats", { token: state.token }),
    api("/api/alerts", { token: state.token }),
    api("/api/investigations", { token: state.token }),
    api("/api/audit", { token: state.token }),
  ]);
  state.stats = stats;
  state.alerts = alerts;
  state.investigations = investigations;
  state.audit = audit;
  state.busyId = null;
  if (state.selected) {
    state.selected =
      investigations.find((i) => i.id === state.selected.id) || state.selected;
  } else if (investigations[0]) {
    state.selected = investigations[0];
  }
  renderConsole();
}

async function boot() {
  if (!state.token) {
    renderLogin();
    return;
  }
  try {
    state.user = await api("/api/auth/me", { token: state.token });
    await refresh();
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    state.token = "";
    renderLogin("Session expired — sign in again.");
  }
}

boot();
