import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within, waitFor } from '@testing-library/react';
import App from './App';

const project = { id: 4, name: 'acme/demo', slug: 'acme-demo', repository_url: 'https://github.com/acme/demo', default_branch: 'main', created_at: '', updated_at: '', latest_snapshot: { id: 5, branch: 'main', commit_sha: 'abc', status: 'succeeded', partial: false, analyzer_schema_version: '1', file_count: 2, python_file_count: 1, python_loc: 18, edge_count: 1, cycle_group_count: 0, diagnostic_count: 0, created_at: '' } };
const result = {
  schema_version: '1', partial: false,
  files: [{ path: 'src/app.py', language: 'python', file_class: 'python_source', physical_loc: 18, analysis_status: 'analyzed' }],
  dependency_edges: [], cycles: [], external_imports: [], unresolved_imports: [], diagnostics: [],
  frameworks: [{ name: 'FastAPI', ecosystem: 'python', evidence_file: 'pyproject.toml', evidence: 'fastapi', kind: 'framework' }],
  test_matches: [{ source: 'src/app.py', tests: [{ path: 'tests/test_app.py', rule: 'name match' }] }],
  metrics: {
    total_file_count: 2, physical_loc: { total: 18, unavailable_file_count: 0 },
    test_matching: { sources_total: 1, sources_with_matching_test: 1 },
    health: { score: 90, level: 'good', confidence: 'high', components: [{ id: 'cycles', label: 'Dependency cycles', score: 100, available: true, reason: '0 of 1 graph files are in cycles (0.000); 25% saturates the penalty.' }] },
    risk: { basis: 'Heuristic risk', top_risks: [{ path: 'src/app.py', level: 'high', points: 5, factors: [{ id: 'untested', reason: '0 matching test files (name/import heuristic, not coverage)' }] }] },
    findings: { top_findings: [{ id: 'large_function:src/app.py:run', kind: 'large_function', severity: 'warning', path: 'src/app.py', symbol: 'run', reason: 'Function spans 160 lines; threshold is 80 lines.' }] },
  },
};

function mockFetch(routes: Record<string, unknown>) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
    const value = routes[path];
    return new Response(value === undefined ? JSON.stringify({ error: { code: 'not_found', message: 'Missing route' } }) : JSON.stringify(value), { status: value === undefined ? 404 : 200, headers: { 'Content-Type': 'application/json' } });
  }));
}

beforeEach(() => { location.hash = '#/projects/4/insights'; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('project insights page', () => {
  it('renders metrics, health reasons, ranked risks and findings accessibly', async () => {
    mockFetch({ '/projects/4': project, '/projects/4/snapshots/latest': result });
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'acme/demo' })).toBeInTheDocument();
    const metrics = screen.getByRole('region', { name: 'Ölçümler' });
    expect(within(metrics).getByText('Fiziksel satır sayısı')).toBeInTheDocument();
    expect(within(metrics).getByText('FastAPI (Python · Çatı)')).toBeInTheDocument();
    expect(within(metrics).getByText(/test kapsamı değildir/)).toBeInTheDocument();
    expect(screen.getByText('90 / 100')).toBeInTheDocument();
    expect(screen.getByText('1 grafik dosyasının 0 tanesi döngüde (oran: 0.000); ceza %25 oranında üst sınıra ulaşır.')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'src/app.py' })[0]).toHaveAttribute('href', '#/projects/4/files');
    expect(screen.getByText('Eşleşen test dosyası yok (ad/içe aktarım eşleşmesi; test kapsamı değildir).')).toBeInTheDocument();
    expect(screen.getByText('Fonksiyon 160 satır uzunluğunda; eşik 80 satır.')).toBeInTheDocument();
  });

  it('explains unavailable history and missing optional metric sections', async () => {
    mockFetch({ '/projects/4': project, '/projects/4/snapshots/latest': { ...result, metrics: {} } });
    render(<App />);
    expect(await screen.findByText(/Bu anlık görüntüde Git etkinliği yok/)).toBeInTheDocument();
    expect(screen.getByText('Bu anlık görüntüde sağlık puanı yok.')).toBeInTheDocument();
    expect(screen.getByText('Bu anlık görüntüde risk sıralaması yok.')).toBeInTheDocument();
    expect(screen.getByText('Bu anlık görüntüde bulgu yok.')).toBeInTheDocument();
  });

  it('shows loading, no-snapshot and API error states', async () => {
    let resolve!: (value: Response) => void;
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((r) => { resolve = r; })));
    render(<App />);
    expect(screen.getByRole('status')).toHaveTextContent('Proje analizleri yükleniyor');
    resolve(new Response(JSON.stringify({ ...project, latest_snapshot: null }), { status: 200 }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Analiz sırada veya henüz bir anlık görüntü tamamlanmadı.'));
    cleanup();
    mockFetch({}); render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Missing route');
  });
});
