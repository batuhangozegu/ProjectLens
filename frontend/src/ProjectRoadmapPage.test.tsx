import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';

const project = { id: 4, name: 'acme/demo', slug: 'acme-demo', repository_url: 'https://github.com/acme/demo', default_branch: 'main', created_at: '', updated_at: '', latest_snapshot: null };
const progress = { formula_version: '1', total: 1, counts: { TODO: 0, IN_PROGRESS: 1, DONE: 0, BLOCKED: 0 }, completed: 0, percent_complete: 0, state: 'in_progress', has_blocked: false, remaining: 1, breakdown_by_category: { API: { total: 1, completed: 0, percent_complete: 0, counts: { TODO: 0, IN_PROGRESS: 1, DONE: 0, BLOCKED: 0 } } }, breakdown_by_section: { 'Step 7': { total: 1, completed: 0, percent_complete: 0, counts: { TODO: 0, IN_PROGRESS: 1, DONE: 0, BLOCKED: 0 } } }, formula: 'Only DONE tasks count as complete.', manual_status_only: true };
const task = { id: 9, project_id: 4, title: 'Add roadmap UI', description: 'Show evidence', status: 'IN_PROGRESS' as const, priority: 'HIGH' as const, category: 'API', position: 1, source: 'import' as const, source_key: '7/add-roadmap', created_at: '', updated_at: '', completed_at: null };
const assessment = { project_id: 4, task_id: 9, formula_version: '1', state: 'estimated', manual_status: 'IN_PROGRESS', estimated_percent: 50, confidence: 'medium', reasons: ['One criterion met and one unmet.'], criteria_results: [{ criterion_id: 2, kind: 'file_exists', outcome: 'met', reason: 'File is present.', evidence: ['src/roadmap.tsx'] }], unknown_criteria: [], attestations: { attested: 0, total: 0 }, context: [{ path: 'src/roadmap.tsx', exists: true, analyzed: true }], divergence: null, divergence_reason: null, snapshot: { id: 3, commit: 'abc' } };

function installFetch({ empty = false, failMutation = false }: { empty?: boolean; failMutation?: boolean } = {}) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost');
    const path = url.pathname.replace('/api/v1', '');
    if (path === '/projects/4') return Response.json(project);
    if (path === '/projects/4/tasks') return Response.json({ items: empty ? [] : [task], total: empty ? 0 : 1, limit: 100, offset: 0 });
    if (path === '/projects/4/roadmap/progress') return Response.json(empty ? { ...progress, total: 0, counts: { TODO: 0, IN_PROGRESS: 0, DONE: 0, BLOCKED: 0 }, completed: 0, percent_complete: null, state: 'empty', remaining: 0, breakdown_by_category: {}, breakdown_by_section: {} } : progress);
    if (path.endsWith('/assessment')) return Response.json(assessment);
    if (path === '/projects/4/tasks/9' && init?.method === 'PATCH') return failMutation ? Response.json({ error: { code: 'invalid_status_transition', message: 'Task status cannot transition.' } }, { status: 409 }) : Response.json({ ...task, status: JSON.parse(String(init.body)).status });
    return Response.json({ error: { code: 'not_found', message: 'Missing route' } }, { status: 404 });
  }));
}

beforeEach(() => { location.hash = '#/projects/4/roadmap'; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('project roadmap page', () => {
  it('shows status groups, progress breakdowns and code-aware assessment', async () => {
    installFetch(); render(<App />);
    expect(await screen.findByRole('heading', { name: 'acme/demo' })).toBeInTheDocument();
    expect(screen.getByText('%0 tamamlandı')).toBeInTheDocument();
    expect(screen.getByText('Step 7')).toBeInTheDocument();
    expect(screen.getAllByText('API')).toHaveLength(2);
    expect(screen.getByRole('heading', { name: 'Devam ediyor (1)' })).toBeInTheDocument();
    expect(await screen.findByText('One criterion met and one unmet.')).toBeInTheDocument();
    expect(screen.getByText('%50')).toBeInTheDocument();
    expect(screen.getByText('src/roadmap.tsx')).toBeInTheDocument();
  });

  it('explains how to populate an empty roadmap', async () => {
    installFetch({ empty: true }); render(<App />);
    expect(await screen.findByRole('heading', { name: 'Yol haritas\u0131nda g\u00f6rev yok' })).toBeInTheDocument();
    expect(screen.getByText(/Depodaki TODO.md kontrol listesini/)).toBeInTheDocument();
    expect(screen.getByText('POST /api/v1/projects/4/roadmap/import')).toBeInTheDocument();
  });

  it('shows failed manual status updates inline', async () => {
    installFetch({ failMutation: true }); render(<App />);
    const select = await screen.findByLabelText('Görev durumu');
    fireEvent.change(select, { target: { value: 'DONE' } });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Task status cannot transition.'));
  });
});
