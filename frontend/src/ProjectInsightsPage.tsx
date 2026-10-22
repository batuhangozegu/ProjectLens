import { useEffect, useState } from 'react';
import { api, type AnalysisResult, type ProjectSummary } from './api/client';
import { InsightsMetrics } from './InsightsMetrics';
import { InsightsHealth } from './InsightsHealth';
import { InsightsRisks } from './InsightsRisks';
import { InsightsActivity } from './InsightsActivity';
import { ProjectPageChrome } from './PageChrome';
import { tr } from './i18n';

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
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Proje analizleri yüklenemedi.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [projectId]);

  if (loading) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.insights} project={project} /><h1>Proje analizleri</h1><p role="status">Proje analizleri yükleniyor…</p></main>;
  if (error || !project) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.insights} project={project} /><h1>Proje analizleri</h1><p role="alert" className="error">{error || 'Proje kullanılamıyor.'}</p><button className="secondary" onClick={() => location.reload()}>Yeniden dene</button></main>;
  return <main id="main-content" tabIndex={-1} className="shell">
    <ProjectPageChrome projectId={projectId} current={tr.nav.insights} project={project} />
    <section className="page-intro"><p className="eyebrow">PROJE ANALİZLERİ</p><h1>{project.name}</h1><p>Depo ölçümleri, açıklanabilir sağlık ve risk bilgileri ile Git etkinliği.</p></section>
    {!result ? <div className="notice" role="status">{project.latest_snapshot ? 'Analiz sonucu kullanılamıyor.' : 'Analiz sırada veya henüz bir anlık görüntü tamamlanmadı.'}</div> : <>
      {(result.partial || (result.diagnostics?.length ?? 0) > 0) && <aside className="notice" aria-label="Analiz tanıları">{result.partial && <strong>Kısmi analiz. </strong>}{result.diagnostics?.length ? `${tr.number.format(result.diagnostics.length)} tanı bildirildi; bazı analizler eksik olabilir.` : 'Bazı analizler eksik olabilir.'}</aside>}
      <InsightsMetrics result={result} />
      <InsightsHealth result={result} />
      <InsightsRisks result={result} projectId={projectId} />
      <InsightsActivity result={result} projectId={projectId} />
    </>}
  </main>;
}
