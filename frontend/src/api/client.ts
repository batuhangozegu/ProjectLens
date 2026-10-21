const API_BASE = (import.meta.env.VITE_API_BASE ?? '/api/v1').replace(/\/$/, '');

export interface ApiErrorEnvelope { error: { code: string; message: string } }
export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    ...init,
    headers: { ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
  });
  if (response.status === 204) return undefined as T;
  const body: unknown = await response.json().catch(() => undefined);
  if (!response.ok) {
    const envelope = body as ApiErrorEnvelope | undefined;
    throw new ApiError(response.status, envelope?.error?.code ?? 'http_error', envelope?.error?.message ?? `Request failed (${response.status}).`);
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
};

export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'DONE' | 'BLOCKED';
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export interface SnapshotSummary { id: number; branch: string; commit_sha: string; status: string; partial: boolean; analyzer_schema_version: string; file_count: number; python_file_count: number; python_loc: number; edge_count: number; cycle_group_count: number; diagnostic_count: number; created_at: string }
export interface ProjectSummary { id: number; name: string; slug: string; repository_url: string | null; default_branch: string; created_at: string; updated_at: string; latest_snapshot: SnapshotSummary | null }
export interface ProjectList { items: ProjectSummary[] }
export interface ProjectAccepted { project_id: number; job_id: number; status: 'queued' | 'running' | 'succeeded' | 'failed'; job_url: string; project_url: string }
export interface JobResponse { id: number; project_id: number; status: 'queued' | 'running' | 'succeeded' | 'failed'; error_code: string | null; error_message: string | null; snapshot_id: number | null; created_at: string; started_at: string | null; finished_at: string | null }
export interface FileRecord { path: string; language: string | null; file_class: string; physical_loc: number | null; analysis_status: string }
export interface DependencyEdge { source: string; target: string; import_line: number; evidence_lines: number[] }
export interface AnalysisDiagnostic { stage: string; file: string | null; error_type: string; message: string }
export interface AnalysisResult { projectlens_format?: string; schema_version: string; files: FileRecord[]; dependency_edges: DependencyEdge[]; cycles: string[][]; external_imports: Record<string, unknown>[]; unresolved_imports: Record<string, unknown>[]; frameworks: { name: string; ecosystem: string; evidence_file: string; evidence: string; kind: string }[]; test_matches: { source: string; tests: { path: string; rule: string }[] }[]; metrics: Record<string, unknown>; diagnostics: AnalysisDiagnostic[]; partial: boolean }
export interface TaskResponse { id: number; project_id: number; title: string; description: string | null; status: TaskStatus; priority: TaskPriority; category: string | null; position: number; source: 'manual' | 'import'; source_key: string | null; created_at: string; updated_at: string; completed_at: string | null }
export interface TaskList { items: TaskResponse[]; total: number; limit: number; offset: number }
export interface RoadmapProgress { formula_version: string; total: number; counts: Record<string, number>; completed: number; percent_complete: number | null; state: string; has_blocked: boolean; remaining: number; breakdown_by_category: Record<string, Record<string, unknown>>; breakdown_by_section: Record<string, Record<string, unknown>>; formula: string; manual_status_only: boolean }
export interface TaskAssessment { project_id: number; task_id: number; formula_version: string; state: string; manual_status: string; estimated_percent: number | null; confidence: string; reasons: unknown[]; criteria_results: unknown[]; unknown_criteria: unknown[]; attestations: Record<string, unknown>; context: unknown[]; divergence: string | null; divergence_reason: string | null; snapshot: Record<string, unknown> | null }
