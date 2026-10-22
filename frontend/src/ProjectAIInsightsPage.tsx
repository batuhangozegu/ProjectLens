import { useEffect, useState, type FormEvent } from 'react';
import { ApiError, api, type ProjectSummary } from './api/client';
import { AIExplanationResult, type AIExplanation } from './AIExplanationResult';

const kinds = [
  { value: 'repository', label: 'Repository overview' },
  { value: 'architecture', label: 'Architecture' },
  { value: 'risk', label: 'Risk' },
] as const;

function explainError(error: unknown): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : 'Could not request an AI explanation.';
  if (error.code === 'ai_disabled') return 'AI explanations are disabled by the server. No explanation was generated.';
  if (error.code === 'ai_unavailable' || error.code === 'ai_provider_error') return 'The AI provider is unavailable or not configured. Try again later, or contact the server administrator.';
  if (error.code === 'ai_timeout') return 'The AI provider took too long to respond. You can try again.';
  if (error.code === 'invalid_context') return 'The selected analysis context could not be prepared. Try a newer or more complete analysis.';
  if (error.code === 'ai_invalid_response') return 'The AI provider returned an unusable response. You can try again later.';
  if (error.code === 'snapshot_not_found') return 'There is no completed analysis snapshot to explain yet. Run an analysis first.';
  if (error.code === 'project_not_found') return 'This project could not be found.';
  if (error.status === 413) return 'This request exceeded the server size limit. Try again with a newer or smaller analysis.';
  if (error.status === 429) return 'The server is receiving too many requests. Wait a moment before trying again.';
  if (error.status === 422) return 'The request was not accepted. Check the selected explanation type and try again.';
  return error.message || 'The AI explanation request failed.';
}

export function ProjectAIInsightsPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [kind, setKind] = useState<(typeof kinds)[number]['value']>('repository');
  const [result, setResult] = useState<AIExplanation | null>(null);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    api.get<ProjectSummary>(`/projects/${projectId}`).then((current) => { if (alive) setProject(current); })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : 'Could not load project.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [projectId]);

  async function requestExplanation(event: FormEvent) {
    event.preventDefault();
    setError(''); setResult(null); setRequesting(true);
    try {
      const response = await api.post<AIExplanation>(`/projects/${projectId}/ai/explanations`, { kind, snapshot: 'latest' });
      setResult(response);
    } catch (e) { setError(explainError(e)); }
    finally { setRequesting(false); }
  }

  if (loading) return <main className="shell"><p role="status">Loading AI insights…</p></main>;
  if (error && !project) return <main className="shell"><nav aria-label="Breadcrumb"><a href={`#/projects/${projectId}`}>← Project overview</a> · <a href="#/">All projects</a></nav><p role="alert" className="error">{error}</p></main>;
  if (!project) return <main className="shell"><p role="alert" className="error">Project unavailable.</p></main>;

  return <main className="shell">
    <header className="site-header"><a className="brand" href="#/"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header>
    <nav aria-label="Breadcrumb"><a href={`#/projects/${projectId}`}>← {project.name} overview</a></nav>
    <section className="page-intro"><p className="eyebrow">OPTIONAL AI INSIGHTS</p><h1>{project.name}</h1><p>Request an AI explanation of the latest saved analysis. Nothing is sent until you submit a request.</p></section>
    <section className="notice ai-data-note" aria-labelledby="ai-data-title">
      <h2 id="ai-data-title">What is sent</h2>
      <p>AI is optional and may be disabled. If enabled, ProjectLens sends a small, selected context from the saved analysis to its configured external AI provider. This can include repository file paths, file categories, dependency relationships, summary metrics, health and risk findings, and framework evidence.</p>
      <p>The context is limited to 16 KB by default. It does not include source code or file contents, the repository URL, credentials, a checkout, or the full analysis snapshot. The provider is currently not configured in this application, so requests may report that AI is unavailable.</p>
      <p>Repository-derived data and the AI response are untrusted. Verify any advice against the cited analysis sources.</p>
    </section>
    {!project.latest_snapshot && <div className="notice" role="status">No completed analysis is available yet. Run an analysis before requesting an explanation.</div>}
    <form className="panel ai-request" onSubmit={requestExplanation}>
      <label htmlFor="ai-kind">Explanation type</label>
      <select id="ai-kind" value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}>
        {kinds.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
      </select>
      <p className="muted">Uses the latest saved snapshot. The provider request has a 512-token output cap and 20-second timeout by default.</p>
      <button disabled={requesting || !project.latest_snapshot}>{requesting ? 'Requesting explanation…' : 'Request AI explanation'}</button>
      {requesting && <p role="status">Waiting for the AI provider…</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
    {result && <AIExplanationResult result={result} />}
  </main>;
}
