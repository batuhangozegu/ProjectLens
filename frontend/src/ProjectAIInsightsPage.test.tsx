import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';

const project = { id: 4, name: 'acme/demo', slug: 'acme-demo', repository_url: 'https://github.com/acme/demo', default_branch: 'main', created_at: '', updated_at: '', latest_snapshot: { id: 5, branch: 'main', commit_sha: 'abc', status: 'succeeded', partial: false, analyzer_schema_version: '1', file_count: 2, python_file_count: 1, python_loc: 18, edge_count: 1, cycle_group_count: 0, diagnostic_count: 0, created_at: '' } };

function installFetch(explanation?: unknown, status = 200, code = '') {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
    if (path === '/projects/4') return Response.json(project);
    if (path === '/projects/4/ai/explanations' && init?.method === 'POST') return Response.json(status >= 400 ? { error: { code, message: code } } : explanation, { status });
    return Response.json({ error: { code: 'not_found', message: 'Missing route' } }, { status: 404 });
  }));
}

beforeEach(() => { location.hash = '#/projects/4/ai'; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('project AI insights page', () => {
  it('does not request AI until explicit submission and renders advisory results with sources', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/projects/4') return Response.json(project);
      if (path === '/projects/4/ai/explanations' && init?.method === 'POST') return Response.json({ kind: 'architecture', text: 'The app has a small dependency graph.', sources_used: [{ kind: 'file', path: 'src/app.py' }], context_budget: { max_bytes: 16384, used_bytes: 210 }, disclaimer: 'Verify cited sources.' });
      return Response.json({ error: { code: 'not_found', message: 'Missing route' } }, { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'acme/demo' })).toBeInTheDocument();
    expect(screen.getByText(/seçilmiş küçük bir bağlamı/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/ai/explanations'))).toBe(false);

    fireEvent.change(screen.getByLabelText('Açıklama türü'), { target: { value: 'architecture' } });
    fireEvent.click(screen.getByRole('button', { name: 'Yapay zeka açıklaması iste' }));
    expect(await screen.findByText('The app has a small dependency graph.')).toBeInTheDocument();
    expect(screen.getByText('YAPAY ZEKA \u00dcRET\u0130M\u0130 \u00b7 \u00d6NER\u0130 N\u0130TEL\u0130\u011e\u0130NDE')).toBeInTheDocument();
    expect(screen.getByText(/do\u011frulanmam\u0131\u015f kabul edin/)).toBeInTheDocument();
    expect(screen.getByText('src/app.py · Dosya')).toBeInTheDocument();
    expect(screen.getByText('Belirtilen kaynakları doğrulayın.')).toBeInTheDocument();
    const request = fetchMock.mock.calls.find(([input]) => String(input).includes('/ai/explanations'));
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ kind: 'architecture', snapshot: 'latest' });
  });

  it('explains disabled and unconfigured provider responses in plain language', async () => {
    installFetch(undefined, 503, 'ai_disabled'); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Yapay zeka açıklaması iste' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Sunucu yapay zeka açıklamalarını devre dışı bırakmış');
  });

  it('explains provider unavailability, context size and rate limits', async () => {
    installFetch(undefined, 503, 'ai_unavailable'); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Yapay zeka açıklaması iste' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('kullanılamıyor veya yapılandırılmamış');
    cleanup();
    installFetch(undefined, 413, 'context_too_large'); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Yapay zeka açıklaması iste' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('boyut sınırını aştı');
    cleanup();
    installFetch(undefined, 429, 'rate_limited'); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Yapay zeka açıklaması iste' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('çok fazla istek');
  });

  it('disables requests when there is no completed snapshot', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ ...project, latest_snapshot: null })));
    render(<App />);
    expect(await screen.findByRole('button', { name: 'Yapay zeka açıklaması iste' })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('Henüz tamamlanmış analiz yok');
  });
});
