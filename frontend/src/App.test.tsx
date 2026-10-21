import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';

const project = { id: 1, name: 'acme/demo', slug: 'acme-demo', repository_url: 'https://github.com/acme/demo', default_branch: 'main', created_at: '', updated_at: '', latest_snapshot: { id: 2, branch: 'main', commit_sha: 'abc', status: 'succeeded', partial: false, analyzer_schema_version: '1', file_count: 2, python_file_count: 1, python_loc: 24, edge_count: 1, cycle_group_count: 0, diagnostic_count: 0, created_at: '' } };
const result = { schema_version: '1', files: [{ path: 'main.py', language: 'python', file_class: 'python_source', physical_loc: 24, analysis_status: 'analyzed' }], dependency_edges: [], cycles: [], external_imports: [], unresolved_imports: [], frameworks: [{ name: 'FastAPI', ecosystem: 'python', evidence_file: 'pyproject.toml', evidence: 'fastapi', kind: 'framework' }], test_matches: [], metrics: { total_file_count: 2, python_file_count: 1, physical_loc: { total: 60, known_file_count: 2, unavailable_file_count: 0 }, python_loc: { total: 24 }, health: { score: 88, level: 'good', reason: 'Healthy', components: [{ reason: 'Few cycles' }] }, risk: { counts_by_level: { high: 1 }, top_risks: [{ path: 'main.py', level: 'high' }] }, findings: { top_findings: [{ title: 'Large module', reason: 'many lines' }] } }, diagnostics: [], partial: false };

function mockFetch(routes: Record<string, unknown>) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
    const value = routes[path];
    return new Response(value === undefined ? JSON.stringify({ error: { code: 'not_found', message: 'Missing route' } }) : JSON.stringify(value), { status: value === undefined ? 404 : 200, headers: { 'Content-Type': 'application/json' } });
  }));
}

beforeEach(() => { location.hash = '#/'; localStorage.clear(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('project screens', () => {
  it('shows list loading and empty states', async () => {
    let resolve!: (value: Response) => void;
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((r) => { resolve = r; })));
    render(<App />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading projects');
    resolve(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    expect(await screen.findByText(/No projects yet/)).toBeInTheDocument();
  });

  it('shows list errors', async () => {
    mockFetch({}); render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Missing route');
  });

  it('validates create URL and creates successfully', async () => {
    mockFetch({ '/projects': { items: [] } }); render(<App />);
    const input = screen.getByLabelText(/GitHub repository URL/);
    fireEvent.change(input, { target: { value: 'http://example.com/foo' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add project' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('valid public GitHub repository URL');
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
      if (path === '/projects' && init?.method === 'POST') return new Response(JSON.stringify({ project_id: 1, job_id: 8, status: 'queued', job_url: '/api/v1/jobs/8', project_url: '/api/v1/projects/1' }), { status: 202 });
      if (path === '/projects') return new Response(JSON.stringify({ items: [project] }), { status: 200 });
      return new Response(JSON.stringify({ items: [project] }), { status: 200 });
    });
    fireEvent.change(input, { target: { value: 'https://github.com/acme/demo' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add project' }));
    expect(await screen.findByText('Project added. Analysis is in progress.')).toBeInTheDocument();
  });

  it('renders overview metrics and reasons from full result', async () => {
    location.hash = '#/projects/1';
    mockFetch({ '/projects/1': project, '/projects/1/snapshots/latest': result }); render(<App />);
    expect(await screen.findByRole('heading', { name: 'acme/demo' })).toBeInTheDocument();
    expect(screen.getByText('88')).toBeInTheDocument();
    expect(screen.getByText('Few cycles')).toBeInTheDocument();
    expect(screen.getByText(/FastAPI/)).toBeInTheDocument();
    expect(screen.getByText(/Large module/)).toBeInTheDocument();
  });

  it('shows unavailable for optional fields missing in older result schema', async () => {
    location.hash = '#/projects/1';
    const older = { schema_version: '0', files: [], dependency_edges: [], cycles: [], external_imports: [], unresolved_imports: [], frameworks: [], test_matches: [], metrics: {}, diagnostics: [], partial: false };
    mockFetch({ '/projects/1': project, '/projects/1/snapshots/latest': older }); render(<App />);
    await screen.findByRole('heading', { name: 'acme/demo' });
    expect(screen.getAllByText('not available').length).toBeGreaterThan(2);
  });
});
