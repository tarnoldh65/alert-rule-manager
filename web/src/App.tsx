import { useEffect, useState, type FormEvent } from 'react';

type Alert = {
  id: number;
  source_id: string;
  event_timestamp: string;
  rule_signature: string;
  rule_category: string | null;
  rule_severity: number | null;
  payload: Record<string, unknown>;
};

type Category = { id: number; name: string; description: string };

type User = { id: number; username: string; role: string; is_active: boolean };

type Autocategory = {
  id: number;
  name: string;
  category_id: number;
  field_path: string;
  match_value: string;
  is_enabled: boolean;
};

type Session = { token: string; username: string; role: string };

const SESSION_KEY = 'alert-manager-session';

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

async function api<T>(session: Session, path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${session.token}` },
  });
  if (!response.ok) throw new Error(`request to ${path} failed`);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

function LoginForm({ onLogin }: { onLogin: (session: Session) => void }) {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [error, setError] = useState('');

  async function login(event: FormEvent) {
    event.preventDefault();
    setError('');
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!response.ok) {
      setError('Invalid username or password.');
      return;
    }
    onLogin((await response.json()) as Session);
  }

  return (
    <main>
      <header>
        <span className="eyebrow">ALERT RULE MANAGER</span>
        <h1>Sign in</h1>
        <p>Use a local account to enter the review queue.</p>
      </header>
      <form className="login" onSubmit={login}>
        <label>
          Username
          <input value={credentials.username} onChange={(event) => setCredentials({ ...credentials, username: event.target.value })} />
        </label>
        <label>
          Password
          <input type="password" value={credentials.password} onChange={(event) => setCredentials({ ...credentials, password: event.target.value })} />
        </label>
        <button type="submit">Enter queue</button>
        {error && <p className="error">{error}</p>}
      </form>
    </main>
  );
}

function QueueView({ session }: { session: Session }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [categoryId, setCategoryId] = useState('');

  useEffect(() => {
    api<Alert[]>(session, '/api/alerts?limit=50').then(setAlerts).catch(() => {});
    api<Category[]>(session, '/api/categories').then(setCategories).catch(() => {});
  }, [session]);

  async function categorize() {
    if (!selected || !categoryId) return;
    await api(session, `/api/alerts/${selected.id}/categorize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category_id: Number(categoryId) }),
    });
    setAlerts((current) => current.filter((alert) => alert.id !== selected.id));
    setSelected(null);
    setCategoryId('');
  }

  return (
    <>
      <header>
        <span className="eyebrow">ALERT RULE MANAGER</span>
        <h1>Review queue</h1>
        <p>{alerts.length} uncategorized alerts</p>
      </header>
      <section className="workspace">
        <div className="queue">
          {alerts.map((alert) => (
            <button className="alert-row" key={alert.id} onClick={() => setSelected(alert)}>
              <span>
                <strong>{alert.rule_signature}</strong>
                <small>{alert.source_id} · {new Date(alert.event_timestamp).toLocaleString()}</small>
              </span>
              <span className="severity">S{alert.rule_severity ?? '-'}</span>
            </button>
          ))}
        </div>
        <article className="detail">
          {selected ? (
            <>
              <span className="eyebrow">ALERT {selected.id}</span>
              <h2>{selected.rule_signature}</h2>
              <p>{selected.rule_category ?? 'Uncategorized'} · severity {selected.rule_severity ?? 'unknown'}</p>
              <div className="categorize-row">
                <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                  <option value="">Choose a category…</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
                <button type="button" disabled={!categoryId} onClick={categorize}>Categorize</button>
              </div>
              <pre>{JSON.stringify(selected.payload, null, 2)}</pre>
            </>
          ) : (
            <p className="empty">Select an alert to inspect its details.</p>
          )}
        </article>
      </section>
    </>
  );
}

function ReportsView({ session }: { session: Session }) {
  const [multiCategorized, setMultiCategorized] = useState<Record<string, unknown>[]>([]);
  const [byCategory, setByCategory] = useState<Record<string, unknown>[]>([]);
  const [autocategorized, setAutocategorized] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    api(session, '/api/reports/multi-categorized-rules').then(setMultiCategorized).catch(() => {});
    api(session, '/api/reports/rules-by-category').then(setByCategory).catch(() => {});
    api(session, '/api/reports/autocategorized-rules').then(setAutocategorized).catch(() => {});
  }, [session]);

  return (
    <>
      <header>
        <span className="eyebrow">ALERT RULE MANAGER</span>
        <h1>Reports</h1>
      </header>
      <ReportTable title="Rules with more than one categorization" rows={multiCategorized} />
      <ReportTable title="Rules by categorization" rows={byCategory} />
      <ReportTable title="Auto-categorized rules" rows={autocategorized} />
    </>
  );
}

function ReportTable({ title, rows }: { title: string; rows: Record<string, unknown>[] }) {
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return (
    <section className="report">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <p className="empty">No data yet.</p>
      ) : (
        <table>
          <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>{columns.map((column) => <td key={column}>{String(row[column])}</td>)}</tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function ConfigView({ session }: { session: Session }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [autocategories, setAutocategories] = useState<Autocategory[]>([]);
  const [categoryForm, setCategoryForm] = useState({ name: '', description: '' });
  const [userForm, setUserForm] = useState({ username: '', password: '', role: 'analyst' });
  const [autocatForm, setAutocatForm] = useState({ name: '', category_id: '', field_path: '', match_value: '' });

  function refresh() {
    api<Category[]>(session, '/api/categories').then(setCategories).catch(() => {});
    api<User[]>(session, '/api/users').then(setUsers).catch(() => {});
    api<Autocategory[]>(session, '/api/autocategories').then(setAutocategories).catch(() => {});
  }

  useEffect(refresh, [session]);

  async function addCategory(event: FormEvent) {
    event.preventDefault();
    await api(session, '/api/categories', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(categoryForm),
    });
    setCategoryForm({ name: '', description: '' });
    refresh();
  }

  async function addUser(event: FormEvent) {
    event.preventDefault();
    await api(session, '/api/users', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(userForm),
    });
    setUserForm({ username: '', password: '', role: 'analyst' });
    refresh();
  }

  async function toggleUser(user: User) {
    await api(session, `/api/users/${user.id}/active`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_active: !user.is_active }),
    });
    refresh();
  }

  async function addAutocategory(event: FormEvent) {
    event.preventDefault();
    await api(session, '/api/autocategories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...autocatForm, category_id: Number(autocatForm.category_id) }),
    });
    setAutocatForm({ name: '', category_id: '', field_path: '', match_value: '' });
    refresh();
  }

  async function toggleAutocategory(autocategory: Autocategory) {
    await api(session, `/api/autocategories/${autocategory.id}/enabled`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_enabled: !autocategory.is_enabled }),
    });
    refresh();
  }

  return (
    <>
      <header>
        <span className="eyebrow">ALERT RULE MANAGER</span>
        <h1>Configuration</h1>
      </header>

      <section className="report">
        <h2>Categories</h2>
        <table>
          <thead><tr><th>Name</th><th>Description</th></tr></thead>
          <tbody>{categories.map((category) => <tr key={category.id}><td>{category.name}</td><td>{category.description}</td></tr>)}</tbody>
        </table>
        <form className="inline-form" onSubmit={addCategory}>
          <input placeholder="Name" value={categoryForm.name} onChange={(event) => setCategoryForm({ ...categoryForm, name: event.target.value })} />
          <input placeholder="Description" value={categoryForm.description} onChange={(event) => setCategoryForm({ ...categoryForm, description: event.target.value })} />
          <button type="submit">Add category</button>
        </form>
      </section>

      <section className="report">
        <h2>Users</h2>
        <table>
          <thead><tr><th>Username</th><th>Role</th><th>Active</th><th></th></tr></thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td><td>{user.role}</td><td>{user.is_active ? 'yes' : 'no'}</td>
                <td><button type="button" onClick={() => toggleUser(user)}>{user.is_active ? 'Deactivate' : 'Activate'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <form className="inline-form" onSubmit={addUser}>
          <input placeholder="Username" value={userForm.username} onChange={(event) => setUserForm({ ...userForm, username: event.target.value })} />
          <input placeholder="Password" type="password" value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} />
          <select value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value })}>
            <option value="analyst">analyst</option>
            <option value="admin">admin</option>
            <option value="auditor">auditor</option>
          </select>
          <button type="submit">Add user</button>
        </form>
      </section>

      <section className="report">
        <h2>Auto-categorization rules</h2>
        <table>
          <thead><tr><th>Name</th><th>Field path</th><th>Match value</th><th>Enabled</th><th></th></tr></thead>
          <tbody>
            {autocategories.map((autocategory) => (
              <tr key={autocategory.id}>
                <td>{autocategory.name}</td><td>{autocategory.field_path}</td><td>{autocategory.match_value}</td>
                <td>{autocategory.is_enabled ? 'yes' : 'no'}</td>
                <td><button type="button" onClick={() => toggleAutocategory(autocategory)}>{autocategory.is_enabled ? 'Disable' : 'Enable'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <form className="inline-form" onSubmit={addAutocategory}>
          <input placeholder="Name" value={autocatForm.name} onChange={(event) => setAutocatForm({ ...autocatForm, name: event.target.value })} />
          <select value={autocatForm.category_id} onChange={(event) => setAutocatForm({ ...autocatForm, category_id: event.target.value })}>
            <option value="">Category…</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <input placeholder="Field path (e.g. alert.signature)" value={autocatForm.field_path} onChange={(event) => setAutocatForm({ ...autocatForm, field_path: event.target.value })} />
          <input placeholder="Match value" value={autocatForm.match_value} onChange={(event) => setAutocatForm({ ...autocatForm, match_value: event.target.value })} />
          <button type="submit">Add rule</button>
        </form>
      </section>
    </>
  );
}

export function App() {
  const [session, setSession] = useState<Session | null>(loadSession);
  const [tab, setTab] = useState<'queue' | 'reports' | 'config'>('queue');

  function onLogin(next: Session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(next));
    setSession(next);
  }

  function logout() {
    localStorage.removeItem(SESSION_KEY);
    setSession(null);
  }

  if (!session) return <LoginForm onLogin={onLogin} />;

  return (
    <main>
      <nav className="tabs">
        <button className={tab === 'queue' ? 'active' : ''} onClick={() => setTab('queue')}>Queue</button>
        <button className={tab === 'reports' ? 'active' : ''} onClick={() => setTab('reports')}>Reports</button>
        {session.role === 'admin' && <button className={tab === 'config' ? 'active' : ''} onClick={() => setTab('config')}>Config</button>}
        <button className="logout" onClick={logout}>Sign out ({session.username})</button>
      </nav>
      {tab === 'queue' && <QueueView session={session} />}
      {tab === 'reports' && <ReportsView session={session} />}
      {tab === 'config' && session.role === 'admin' && <ConfigView session={session} />}
    </main>
  );
}
