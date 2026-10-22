import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import App from './App';

const project = { id: 4, name: 'acme/demo', slug: 'acme-demo', repository_url: 'https://github.com/acme/demo', default_branch: 'main', created_at: '', updated_at: '', latest_snapshot: { id: 5, branch: 'main', commit_sha: 'abc', status: 'succeeded', partial: false, analyzer_schema_version: '1', file_count: 3, python_file_count: 3, python_loc: 25, edge_count: 2, cycle_group_count: 1, diagnostic_count: 0, created_at: '' } };
const result = {
  schema_version: '1',
  files: [
    { path: 'src/a.py', language: 'python', file_class: 'python_source', physical_loc: 10, analysis_status: 'analyzed' },
    { path: 'src/b.py', language: 'python', file_class: 'python_source', physical_loc: 8, analysis_status: 'analyzed' },
    { path: 'tests/test_a.py', language: 'python', file_class: 'python_test', physical_loc: 7, analysis_status: 'analyzed' },
  ],
  dependency_edges: [{ source: 'src/a.py', target: 'src/b.py', import_line: 1, evidence_lines: [1] }, { source: 'src/b.py', target: 'src/a.py', import_line: 1, evidence_lines: [1] }],
  cycles: [['src/a.py', 'src/b.py']], external_imports: [], unresolved_imports: [], frameworks: [],
  test_matches: [{ source: 'src/a.py', tests: [{ path: 'tests/test_a.py', rule: 'name match' }] }],
  metrics: { risk: { top_risks: [{ path: 'src/a.py', level: 'high' }] }, findings: { top_findings: [{ path: 'src/a.py', title: 'Large file', reason: 'High LOC' }] } }, diagnostics: [], partial: false,
};

function mockFetch(routes: Record<string, unknown>) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname.replace('/api/v1', '');
    const value = routes[path];
    return new Response(value === undefined ? JSON.stringify({ error: { code: 'not_found', message: 'Missing route' } }) : JSON.stringify(value), { status: value === undefined ? 404 : 200, headers: { 'Content-Type': 'application/json' } });
  }));
}

beforeEach(() => { location.hash = '#/projects/4/files'; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('project files page', () => {
  it('renders a collapsible tree, graph, and selected file details', async () => {
    mockFetch({ '/projects/4': project, '/projects/4/snapshots/latest': result });
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'acme/demo' })).toBeInTheDocument();
    const tree = screen.getByRole('navigation', { name: 'Repository files' });
    fireEvent.click(within(tree).getByRole('button', { name: /src\// }));
    expect(within(tree).queryByRole('button', { name: /^a\.py/ })).not.toBeInTheDocument();
    fireEvent.click(within(tree).getByRole('button', { name: /src\// }));
    fireEvent.click(within(tree).getByRole('button', { name: /^a\.py/ }));
    const details = screen.getByRole('complementary', { name: 'File details' });
    expect(within(details).getAllByText('src/a.py').length).toBeGreaterThan(0);
    expect(within(details).getByText('tests/test_a.py')).toBeInTheDocument();
    expect(within(details).getByText(/Risk: high/)).toBeInTheDocument();
    expect(within(details).getByText(/Large file: High LOC/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Dependency graph' })).toBeInTheDocument();
  });

  it('shows the empty analysis and unavailable snapshot states', async () => {
    mockFetch({ '/projects/4': project, '/projects/4/snapshots/latest': { ...result, files: [], dependency_edges: [] } });
    render(<App />);
    expect(await screen.findByText('No files in this analysis.')).toBeInTheDocument();
    expect(screen.getByText('No files to display in the dependency graph.')).toBeInTheDocument();
  });

  it('shows API errors with an alert', async () => {
    mockFetch({}); render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Missing route');
  });
});
