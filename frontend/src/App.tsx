import { useEffect, useState, type FormEvent } from 'react';
import { ApiError, api, type AnalysisResult, type JobResponse, type ProjectAccepted, type ProjectList, type ProjectSummary } from './api/client';
import { useRoute } from './router';
import { ProjectFilesPage } from './ProjectFilesPage';
import { ProjectInsightsPage } from './ProjectInsightsPage';
import { ProjectRoadmapPage } from './ProjectRoadmapPage';
import { ProjectAIInsightsPage } from './ProjectAIInsightsPage';
import { PageFrame, ProjectPageChrome, SiteHeader } from './PageChrome';
import { healthLabel, riskLabel, snapshotStatusLabel, tr } from './i18n';

const unavailable = tr.unavailable;
function record(value: unknown): Record<string, any> { return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, any> : {}; }
function show(value: unknown): string { return value === null || value === undefined || value === '' ? unavailable : String(value); }
function validGithubUrl(value: string) {
  try { const u = new URL(value); return u.protocol === 'https:' && u.hostname.toLowerCase() === 'github.com' && u.pathname.split('/').filter(Boolean).length >= 2 && !u.pathname.split('/').filter(Boolean).some((p) => p === '.' || p === '..'); }
  catch { return false; }
}

export function ProjectListPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [url, setUrl] = useState('');
  const [formError, setFormError] = useState('');
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [trackedJobs, setTrackedJobs] = useState<number[]>(() => {
    try { return JSON.parse(localStorage.getItem('projectlens-jobs') || '[]') as number[]; } catch { return []; }
  });

  async function load() {
    try { const data = await api.get<ProjectList>('/projects'); setProjects(data.items); setError(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Projeler yüklenemedi.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    let stopped = false;
    const poll = async () => {
      const finished: number[] = [];
      for (const jobId of trackedJobs) {
        if (stopped) return;
        try {
          const job = await api.get<JobResponse>(`/jobs/${jobId}`);
          if (job.status === 'succeeded' || job.status === 'failed') {
            finished.push(jobId);
            setNotice(job.status === 'succeeded' ? 'Analiz tamamlandı.' : job.error_message || 'Analiz başarısız oldu.');
            await load();
          }
        } catch { finished.push(jobId); }
      }
      if (finished.length) setTrackedJobs((current) => {
        const next = current.filter((id) => !finished.includes(id));
        localStorage.setItem('projectlens-jobs', JSON.stringify(next));
        return next;
      });
    };
    let polls = 0;
    const timer = window.setInterval(() => { polls += 1; if (polls <= 48) void poll(); }, 2500);
    return () => { stopped = true; clearInterval(timer); };
  }, [trackedJobs]);

  async function create(event: FormEvent) {
    event.preventDefault(); setFormError(''); setNotice('');
    if (!validGithubUrl(url.trim())) { setFormError('Geçerli bir herkese açık GitHub depo adresi girin (https://github.com/sahip/depo).'); return; }
    setCreating(true);
    try {
      const accepted = await api.post<ProjectAccepted>('/projects', { repository_url: url.trim() });
      const ids = [...new Set([...trackedJobs, accepted.job_id])];
      localStorage.setItem('projectlens-jobs', JSON.stringify(ids)); setTrackedJobs(ids);
      setNotice('Proje eklendi. Analiz sürüyor.'); setUrl(''); await load();
    } catch (e) { setFormError(e instanceof Error ? e.message : 'Proje oluşturulamadı.'); }
    finally { setCreating(false); }
  }

  async function deleteProject(id: number) {
    setDeleteError(''); setDeletingId(id);
    try { await api.delete(`/projects/${id}`); }
    catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) {
        setDeleteError(e instanceof Error ? e.message : 'Proje silinemedi.'); setDeletingId(null); return;
      }
    }
    setConfirmDeleteId(null); setDeletingId(null); setLoading(true); await load();
  }

  return <main id="main-content" tabIndex={-1} className="shell">
    <SiteHeader />
    <section className="page-intro"><p className="eyebrow">DEPO ANALİZİ</p><h1>Projeleriniz</h1><p>Herkese açık bir GitHub deposu ekleyerek yapısını ve sağlığını inceleyin.</p></section>
    <section className="panel" aria-labelledby="create-title"><h2 id="create-title">Proje ekle</h2><form onSubmit={create} noValidate>
      <label htmlFor="repository-url">GitHub depo adresi</label><div className="form-row"><input id="repository-url" type="url" autoComplete="url" placeholder="https://github.com/sahip/depo" value={url} onChange={(e) => setUrl(e.target.value)} aria-describedby={formError ? 'form-error' : undefined} /><button disabled={creating}>{creating ? 'Ekleniyor…' : 'Proje ekle'}</button></div>
      {formError && <p id="form-error" className="error" role="alert">{formError}</p>}
    </form></section>
    <section className="projects" aria-labelledby="projects-title"><div className="section-heading"><h2 id="projects-title">Projeler</h2><button className="secondary" onClick={() => { setLoading(true); void load(); }}>Yenile</button></div>
      <p className="sr-only" aria-live="polite">{notice}</p>
      {deleteError && <p className="error" role="alert">{deleteError}</p>}
      {loading ? <p role="status">Projeler yükleniyor…</p> : error ? <div className="error-state" role="alert"><p>{error}</p><button className="secondary" onClick={() => { setLoading(true); void load(); }}>Yeniden dene</button></div> : projects.length === 0 ? <p className="empty">Henüz proje yok. Başlamak için yukarıdan bir GitHub deposu ekleyin.</p> : <ul className="project-list">{projects.map((p) => <li key={p.id}><a className="project-card" href={`#/projects/${p.id}`}><span><strong>{p.name}</strong><small>{p.repository_url || p.slug}</small></span><span className="project-meta">{p.latest_snapshot ? `${tr.number.format(p.latest_snapshot.file_count)} dosya · ${snapshotStatusLabel(p.latest_snapshot.status)}` : 'Analiz bekliyor'}</span></a><div className="delete-controls">{confirmDeleteId === p.id ? <div role="group" aria-label={`${p.name} projesini silme onayı`}><p>{tr.confirmDelete}</p><button disabled={deletingId === p.id} onClick={() => void deleteProject(p.id)}>{deletingId === p.id ? 'Siliniyor…' : tr.confirm}</button><button className="secondary" onClick={() => { setConfirmDeleteId(null); setDeleteError(''); }}>{tr.cancel}</button></div> : <button className="secondary" aria-label={`${p.name} projesini sil`} onClick={() => { setDeleteError(''); setConfirmDeleteId(p.id); }}>{tr.delete}</button>}</div></li>)}</ul>}
    </section>
  </main>;
}

export function ProjectOverviewPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const p = await api.get<ProjectSummary>(`/projects/${projectId}`);
        if (!alive) return; setProject(p);
        if (p.latest_snapshot) {
          try { const data = await api.get<AnalysisResult>(`/projects/${projectId}/snapshots/latest`); if (alive) setResult(data); }
          catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Analiz yüklenemedi.'); }
        }
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Proje yüklenemedi.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [projectId]);
  async function deleteProject() {
    setDeleting(true); setDeleteError('');
    try { await api.delete(`/projects/${projectId}`); location.hash = '#/'; }
    catch (e) { if (e instanceof ApiError && e.status === 404) { location.hash = '#/'; return; } setDeleteError(e instanceof Error ? e.message : 'Proje silinemedi.'); }
    finally { setDeleting(false); }
  }
  if (loading) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.overview} /><h1>Proje genel bakışı</h1><p role="status">Proje yükleniyor…</p></main>;
  if (error || !project) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.overview} /><section className="page-intro"><h1>Proje genel bakışı</h1><p role="alert" className="error">{error || 'Proje kullanılamıyor.'}</p><button className="secondary" onClick={() => location.reload()}>Yeniden dene</button></section></main>;
  const metrics = record(result?.metrics), physical = record(metrics.physical_loc), python = record(metrics.python_loc);
  const health = record(metrics.health), risk = record(metrics.risk), findings = record(metrics.findings);
  const riskCounts = record(risk.counts_by_level);
  const riskLevel = ['high', 'medium', 'low', 'minimal'].find((level) => typeof riskCounts[level] === 'number' && riskCounts[level] > 0);
  const languages = new Map<string, number>();
  for (const file of result?.files ?? []) if (file.language) languages.set(file.language, (languages.get(file.language) ?? 0) + 1);
  const languageText = languages.size ? [...languages].sort((a,b) => b[1]-a[1]).map(([name,count]) => `${name} (${tr.number.format(count)})`).join(', ') : unavailable;
  const healthReasons = Array.isArray(health.components) ? health.components.filter((c: any) => c?.reason).map((c: any) => String(c.reason)) : [];
  const topFindings = Array.isArray(findings.top_findings) ? findings.top_findings : Array.isArray(findings.items) ? findings.items : [];
  return <main id="main-content" tabIndex={-1} className="shell">
    <ProjectPageChrome projectId={projectId} current={tr.nav.overview} />
    <nav aria-label="İçerik yolu"><a href="#/">← Tüm projeler</a></nav>
    <section className="page-intro"><p className="eyebrow">PROJE GENEL BAKIŞI</p><h1>{project.name}</h1><p>{project.repository_url || unavailable} · varsayılan dal: {show(project.default_branch)}</p><button className="secondary" onClick={() => { setConfirmDelete(true); setDeleteError(''); }}>{tr.deleteProject}</button>{confirmDelete && <div role="group" className="confirm-delete" aria-label="Proje silme onayı"><p>{tr.confirmDelete}</p>{deleteError && <p className="error" role="alert">{deleteError}</p>}<button disabled={deleting} onClick={() => void deleteProject()}>{deleting ? 'Siliniyor…' : tr.confirm}</button><button className="secondary" onClick={() => setConfirmDelete(false)}>{tr.cancel}</button></div>}</section>
    <p className="page-links"><a className="files-link" href={`#/projects/${projectId}/files`}>Dosyaları ve bağımlılıkları incele →</a><a className="files-link" href={`#/projects/${projectId}/insights`}>Ölçümler, sağlık, riskler ve etkinlik →</a><a className="files-link" href={`#/projects/${projectId}/roadmap`}>Yol haritası ve kod destekli takip →</a><a className="files-link" href={`#/projects/${projectId}/ai`}>İsteğe bağlı yapay zeka açıklamaları →</a></p>
    {!result ? <div className="notice" role="status">{project.latest_snapshot ? 'Analiz sonucu kullanılamıyor.' : 'Analiz sırada veya henüz bir anlık görüntü tamamlanmadı.'}</div> : <>
      {(result.partial || (result.diagnostics?.length ?? 0) > 0) && <aside className="notice" aria-label="Analiz tanıları">{result.partial && <strong>Kısmi analiz</strong>} {result.diagnostics?.length ? `${tr.number.format(result.diagnostics.length)} tanı bildirildi. Bazı sonuçlar eksik olabilir.` : ''}</aside>}
      <section className="metric-grid" aria-label="Proje ölçümleri">
        <Metric label="Dosyalar" value={metrics.total_file_count} /><Metric label="Fiziksel satır sayısı" value={physical.total} detail={physical.unavailable_file_count !== undefined ? `${tr.number.format(physical.unavailable_file_count)} dosyada kullanılamıyor` : undefined} />
        <Metric label="Python dosyaları" value={metrics.python_file_count} /><Metric label="Python satır sayısı" value={python.total} />
        <Metric label="Diller" value={languageText} /><Metric label="Çatılar" value={result.frameworks?.length ? result.frameworks.map((f) => f.name).join(', ') : result.frameworks ? 'Algılanmadı' : unavailable} />
        <Metric label="Sağlık puanı" value={health.score} detail={health.level ? `Düzey: ${healthLabel(String(health.level))}` : undefined} /><Metric label="Risk düzeyi" value={riskLevel ? riskLabel(riskLevel) : unavailable} detail={riskCounts.high !== undefined ? `Yüksek: ${tr.number.format(riskCounts.high)}` : undefined} />
      </section>
      <section className="panel" aria-labelledby="health-reasons"><h2 id="health-reasons">Sağlık gerekçeleri</h2>{healthReasons.length ? <ul>{healthReasons.map((reason: string) => <li key={reason}>{reason}</li>)}</ul> : <p>{health.reason || unavailable}</p>}</section>
      <section className="panel" aria-labelledby="findings-title"><h2 id="findings-title">Öne çıkan bulgular</h2>{topFindings.length ? <ul>{topFindings.slice(0, 5).map((item: any, i: number) => <li key={item.path || item.id || i}>{typeof item === 'string' ? item : `${item.title || item.path || item.name || 'Bulgu'}${item.reason ? ` — ${item.reason}` : ''}`}</li>)}</ul> : <p>{Array.isArray(findings.top_findings) || Array.isArray(findings.items) ? 'Bildirilen bulgu yok.' : unavailable}</p>}</section>
      {result.diagnostics?.length > 0 && <section className="panel" aria-labelledby="diagnostics-title"><h2 id="diagnostics-title">Tanı bilgileri</h2><ul>{result.diagnostics.slice(0, 5).map((d, i) => <li key={`${d.stage}-${i}`}>{d.stage}{d.file ? ` · ${d.file}` : ''}: {d.message}</li>)}</ul></section>}
    </>}
  </main>;
}

function Metric({ label, value, detail }: { label: string; value: unknown; detail?: string }) { const formatted = typeof value === 'number' ? tr.number.format(value) : show(value); return <article className="metric"><h2>{label}</h2><p>{formatted}</p>{detail && <small>{detail}</small>}</article>; }

export function NotFoundPage() { return <main id="main-content" className="shell" tabIndex={-1}><header className="site-header"><a className="brand" href="#/"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header><section className="page-intro"><p className="eyebrow">SAYFA BULUNAMADI</p><h1>Bu sayfa bulunamadı</h1><p>Adres yanlış olabilir veya sayfa taşınmış olabilir.</p><a href="#/">Projelere dön</a></section></main>; }

export default function App() { const route = useRoute(); const page = !route.known ? <NotFoundPage /> : route.projectId === null ? <ProjectListPage /> : route.files ? <ProjectFilesPage projectId={route.projectId} /> : route.insights ? <ProjectInsightsPage projectId={route.projectId} /> : route.roadmap ? <ProjectRoadmapPage projectId={route.projectId} /> : route.ai ? <ProjectAIInsightsPage projectId={route.projectId} /> : <ProjectOverviewPage projectId={route.projectId} />; return <PageFrame key={route.path}>{page}</PageFrame>; }
