import { StrictMode, useEffect, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Alert = {
  id: number;
  source_id: string;
  event_timestamp: string;
  rule_signature: string;
  rule_category: string | null;
  rule_severity: number | null;
  payload: Record<string, unknown>;
};

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('alert-manager-token'));
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loginError, setLoginError] = useState('');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState<Alert | null>(null);

  useEffect(() => {
    if (!token) return;
    fetch('/api/alerts?limit=50', { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Session expired')))
      .then(setAlerts)
      .catch(() => { localStorage.removeItem('alert-manager-token'); setToken(null); });
  }, [token]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setLoginError('');
    const response = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(credentials),
    });
    if (!response.ok) { setLoginError('Invalid username or password.'); return; }
    const result = await response.json();
    localStorage.setItem('alert-manager-token', result.token);
    setToken(result.token);
  }

  if (!token) return <main><header><span className="eyebrow">ALERT RULE MANAGER</span><h1>Sign in</h1><p>Use a local analyst account to enter the review queue.</p></header><form className="login" onSubmit={login}><label>Username<input value={credentials.username} onChange={(event) => setCredentials({ ...credentials, username: event.target.value })} /></label><label>Password<input type="password" value={credentials.password} onChange={(event) => setCredentials({ ...credentials, password: event.target.value })} /></label><button type="submit">Enter queue</button>{loginError && <p className="error">{loginError}</p>}</form></main>;

  return (
    <main>
      <header><span className="eyebrow">ALERT RULE MANAGER</span><h1>Review queue</h1><p>{alerts.length} uncategorized alerts</p></header>
      <section className="workspace">
        <div className="queue">{alerts.map((alert) => (
          <button className="alert-row" key={alert.id} onClick={() => setSelected(alert)}>
            <span><strong>{alert.rule_signature}</strong><small>{alert.source_id} · {new Date(alert.event_timestamp).toLocaleString()}</small></span>
            <span className="severity">S{alert.rule_severity ?? '-'}</span>
          </button>
        ))}</div>
        <article className="detail">{selected ? <><span className="eyebrow">ALERT {selected.id}</span><h2>{selected.rule_signature}</h2><p>{selected.rule_category ?? 'Uncategorized'} · severity {selected.rule_severity ?? 'unknown'}</p><pre>{JSON.stringify(selected.payload, null, 2)}</pre></> : <p className="empty">Select an alert to inspect its details.</p>}</article>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
