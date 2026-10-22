import { useEffect, useState } from 'react';
import { api, type AnalysisResult, type ProjectSummary } from './api/client';
import { InsightsMetrics } from './InsightsMetrics';
import { InsightsHealth } from './InsightsHealth';
import { InsightsRisks } from './InsightsRisks';
import { InsightsActivity } from './InsightsActivity';
import { ProjectPageChrome } from './PageChrome';

export function ProjectInsightsPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const current = await api.get<ProjectSummary>(`/projects/${projectId}`);
        if (!alive) return;
        setProject(current);
        if (current.latest_snapshot) setResult(await api.get<AnalysisResult>(`/projects/${projectId}/snapshots/latest`));
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Could not load project insights.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [projectId]);

  if (loading) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current="Insights" /><h1>Project insights</h1><p role="status">Loading project insights…</p></main>;
  if (error || !project) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current="Insights" /><h1>Project insights</h1><p role="alert" className="error">{error || 'Project unavailable.'}</p><button className="secondary" onClick={() => location.reload()}>Try again</button></main>;
  return <main id="main-content" tabIndex={-1} className="shell">
    <ProjectPageChrome projectId={projectId} current="Insights" />
    <section className="page-intro"><p className="eyebrow">PROJECT INSIGHTS</p><h1>{project.name}</h1><p>Repository metrics, explainable health and risk, and available Git activity.</p></section>
    {!result ? <div className="notice" role="status">{project.latest_snapshot ? 'Analysis result is not available.' : 'Analysis is queued or no snapshot has completed yet.'}</div> : <>
      {(result.partial || (result.diagnostics?.length ?? 0) > 0) && <aside className="notice" aria-label="Analysis diagnostics">{result.partial && <strong>Partial analysis. </strong>}{result.diagnostics?.length ? `${result.diagnostics.length} diagnostic${result.diagnostics.length === 1 ? '' : 's'} reported; some insights may be incomplete.` : 'Some insights may be incomplete.'}</aside>}
      <InsightsMetrics result={result} />
      <InsightsHealth result={result} />
      <InsightsRisks result={result} projectId={projectId} />
      <InsightsActivity result={result} projectId={projectId} />
    </>}
  </main>;
}
