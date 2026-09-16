import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';

const ALERT = {
  id: 1,
  source_id: 'sensor-a',
  event_timestamp: '2026-01-01T00:00:00Z',
  rule_signature: 'ET SCAN suspicious',
  rule_category: null,
  rule_severity: 2,
  payload: { alert: { signature: 'ET SCAN suspicious' } },
};

const CATEGORY = { id: 9, name: 'Recon', description: '' };

function jsonResponse(body: unknown, ok = true) {
  return Promise.resolve({ ok, status: ok ? 200 : 401, json: () => Promise.resolve(body) } as Response);
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('login', () => {
  it('shows the review queue after a successful sign-in', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url === '/api/auth/login') return jsonResponse({ token: 't', username: 'ana', role: 'analyst' });
      if (url.startsWith('/api/alerts')) return jsonResponse([ALERT]);
      if (url === '/api/categories') return jsonResponse([CATEGORY]);
      return jsonResponse([]);
    }));

    render(<App />);

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'ana' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enter queue' }));

    await waitFor(() => expect(screen.getByText('ET SCAN suspicious')).toBeInTheDocument());
    expect(screen.getByText('1 uncategorized alerts')).toBeInTheDocument();
  });

  it('shows an error on invalid credentials', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({ detail: 'invalid credentials' }, false)));

    render(<App />);

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'ana' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enter queue' }));

    await waitFor(() => expect(screen.getByText('Invalid username or password.')).toBeInTheDocument());
  });
});

describe('categorization', () => {
  it('removes an alert from the queue once it is categorized', async () => {
    localStorage.setItem('alert-manager-session', JSON.stringify({ token: 't', username: 'ana', role: 'analyst' }));
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url.startsWith('/api/alerts') && (!options || options.method === undefined)) return jsonResponse([ALERT]);
      if (url === '/api/categories') return jsonResponse([CATEGORY]);
      if (url === '/api/alerts/1/categorize') return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(undefined) } as Response);
      return jsonResponse([]);
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByText('ET SCAN suspicious')).toBeInTheDocument());
    fireEvent.click(screen.getByText('ET SCAN suspicious'));

    fireEvent.change(screen.getByRole('combobox'), { target: { value: String(CATEGORY.id) } });
    fireEvent.click(screen.getByRole('button', { name: 'Categorize' }));

    await waitFor(() => expect(screen.queryByText('ET SCAN suspicious')).not.toBeInTheDocument());
    expect(screen.getByText('0 uncategorized alerts')).toBeInTheDocument();
  });
});
