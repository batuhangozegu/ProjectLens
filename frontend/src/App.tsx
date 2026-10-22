import { useEffect, useState, type FormEvent } from 'react';
import { api, type AnalysisResult, type JobResponse, type ProjectAccepted, type ProjectList, type ProjectSummary } from './api/client';
import { useRoute } from './router';
import { ProjectFilesPage } from './ProjectFilesPage';
import { ProjectInsightsPage } from './ProjectInsightsPage';

const unavailable = 'not available';
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
  const [trackedJobs, setTrackedJobs] = useState<number[]>(() => {
    try { return JSON.parse(localStorage.getItem('projectlens-jobs') || '[]') as number[]; } catch { return []; }
  });

  async function load() {
    try { const data = await api.get<ProjectList>('/projects'); setProjects(data.items); setError(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not load projects.'); }
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
            setNotice(job.status === 'succeeded' ? 'Analysis completed.' : job.error_message || 'Analysis failed.');
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
    if (!validGithubUrl(url.trim())) { setFormError('Enter a valid public GitHub repository URL (https://github.com/owner/repository).'); return; }
    setCreating(true);
    try {
      const accepted = await api.post<ProjectAccepted>('/projects', { repository_url: url.trim() });
      const ids = [...new Set([...trackedJobs, accepted.job_id])];
      localStorage.setItem('projectlens-jobs', JSON.stringify(ids)); setTrackedJobs(ids);
      setNotice('Project added. Analysis is in progress.'); setUrl(''); await load();
    } catch (e) { setFormError(e instanceof Error ? e.message : 'Could not create project.'); }
    finally { setCreating(false); }
  }

  return <main className="shell">
    <header className="site-header"><a className="brand" href="#/" aria-label="ProjectLens home"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header>
    <section className="page-intro"><p className="eyebrow">REPOSITORY INSIGHT</p><h1>Your projects</h1><p>Connect a public GitHub repository to explore its structure and health.</p></section>
    <section className="panel" aria-labelledby="create-title"><h2 id="create-title">Add a project</h2><form onSubmit={create} noValidate>
      <label htmlFor="repository-url">GitHub repository URL</label><div className="form-row"><input id="repository-url" type="url" autoComplete="url" placeholder="https://github.com/owner/repository" value={url} onChange={(e) => setUrl(e.target.value)} aria-describedby={formError ? 'form-error' : undefined} /><button disabled={creating}>{creating ? 'Adding…' : 'Add project'}</button></div>
      {formError && <p id="form-error" className="error" role="alert">{formError}</p>}
    </form></section>
    <section className="projects" aria-labelledby="projects-title"><div className="section-heading"><h2 id="projects-title">Projects</h2><button className="secondary" onClick={() => { setLoading(true); void load(); }}>Refresh</button></div>
      <p className="sr-only" aria-live="polite">{notice}</p>
      {loading ? <p role="status">Loading projects…</p> : error ? <div className="error-state" role="alert"><p>{error}</p><button className="secondary" onClick={() => { setLoading(true); void load(); }}>Try again</button></div> : projects.length === 0 ? <p className="empty">No projects yet. Add a GitHub repository above to get started.</p> : <ul className="project-list">{projects.map((p) => <li key={p.id}><a className="project-card" href={`#/projects/${p.id}`}><span><strong>{p.name}</strong><small>{p.repository_url || p.slug}</small></span><span className="project-meta">{p.latest_snapshot ? `${p.latest_snapshot.file_count} files · ${p.latest_snapshot.status}` : 'Analysis pending'}</span></a></li>)}</ul>}
    </section>
  </main>;
}

export function ProjectOverviewPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const p = await api.get<ProjectSummary>(`/projects/${projectId}`);
        if (!alive) return; setProject(p);
        if (p.latest_snapshot) {
          try { const data = await api.get<AnalysisResult>(`/projects/${projectId}/snapshots/latest`); if (alive) setResult(data); }
          catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Could not load analysis.'); }
        }
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Could not load project.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [projectId]);
  if (loading) return <main className="shell"><p role="status">Loading project…</p></main>;
  if (error || !project) return <main className="shell"><a href="#/">← All projects</a><p role="alert" className="error">{error || 'Project unavailable.'}</p></main>;
  const metrics = record(result?.metrics), physical = record(metrics.physical_loc), python = record(metrics.python_loc);
  const health = record(metrics.health), risk = record(metrics.risk), findings = record(metrics.findings);
  const riskCounts = record(risk.counts_by_level);
  const riskLevel = ['high', 'medium', 'low', 'minimal'].find((level) => typeof riskCounts[level] === 'number' && riskCounts[level] > 0);
  const languages = new Map<string, number>();
  for (const file of result?.files ?? []) if (file.language) languages.set(file.language, (languages.get(file.language) ?? 0) + 1);
  const languageText = languages.size ? [...languages].sort((a,b) => b[1]-a[1]).map(([name,count]) => `${name} (${count})`).join(', ') : unavailable;
  const healthReasons = Array.isArray(health.components) ? health.components.filter((c: any) => c?.reason).map((c: any) => String(c.reason)) : [];
  const topFindings = Array.isArray(findings.top_findings) ? findings.top_findings : Array.isArray(findings.items) ? findings.items : [];
  return <main className="shell">
    <header className="site-header"><a className="brand" href="#/"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header>
    <nav aria-label="Breadcrumb"><a href="#/">← All projects</a></nav>
    <section className="page-intro"><p className="eyebrow">PROJECT OVERVIEW</p><h1>{project.name}</h1><p>{project.repository_url || unavailable} · default branch: {show(project.default_branch)}</p></section>
    <p className="page-links"><a className="files-link" href={`#/projects/${projectId}/files`}>Explore files and dependencies →</a><a className="files-link" href={`#/projects/${projectId}/insights`}>Metrics, health, risks and activity →</a></p>
    {!result ? <div className="notice" role="status">{project.latest_snapshot ? 'Analysis result is not available.' : 'Analysis is queued or no snapshot has completed yet.'}</div> : <>
      {(result.partial || (result.diagnostics?.length ?? 0) > 0) && <aside className="notice" aria-label="Analysis diagnostics">{result.partial && <strong>Partial analysis</strong>} {result.diagnostics?.length ? `${result.diagnostics.length} diagnostic${result.diagnostics.length === 1 ? '' : 's'} reported. Some results may be incomplete.` : ''}</aside>}
      <section className="metric-grid" aria-label="Project metrics">
        <Metric label="Files" value={metrics.total_file_count} /><Metric label="Physical LOC" value={physical.total} detail={physical.unavailable_file_count !== undefined ? `${physical.unavailable_file_count} unavailable` : undefined} />
        <Metric label="Python files" value={metrics.python_file_count} /><Metric label="Python LOC" value={python.total} />
        <Metric label="Languages" value={languageText} /><Metric label="Frameworks" value={result.frameworks?.length ? result.frameworks.map((f) => f.name).join(', ') : result.frameworks ? 'None detected' : unavailable} />
        <Metric label="Health score" value={health.score} detail={health.level ? `Level: ${health.level}` : undefined} /><Metric label="Risk level" value={riskLevel} detail={riskCounts.high !== undefined ? `High: ${riskCounts.high}` : undefined} />
      </section>
      <section className="panel" aria-labelledby="health-reasons"><h2 id="health-reasons">Health reasons</h2>{healthReasons.length ? <ul>{healthReasons.map((reason: string) => <li key={reason}>{reason}</li>)}</ul> : <p>{health.reason || unavailable}</p>}</section>
      <section className="panel" aria-labelledby="findings-title"><h2 id="findings-title">Top findings</h2>{topFindings.length ? <ul>{topFindings.slice(0, 5).map((item: any, i: number) => <li key={item.path || item.id || i}>{typeof item === 'string' ? item : `${item.title || item.path || item.name || 'Finding'}${item.reason ? ` — ${item.reason}` : ''}`}</li>)}</ul> : <p>{Array.isArray(findings.top_findings) || Array.isArray(findings.items) ? 'No findings reported.' : unavailable}</p>}</section>
      {result.diagnostics?.length > 0 && <section className="panel" aria-labelledby="diagnostics-title"><h2 id="diagnostics-title">Diagnostics</h2><ul>{result.diagnostics.slice(0, 5).map((d, i) => <li key={`${d.stage}-${i}`}>{d.stage}{d.file ? ` · ${d.file}` : ''}: {d.message}</li>)}</ul></section>}
    </>}
  </main>;
}

function Metric({ label, value, detail }: { label: string; value: unknown; detail?: string }) { return <article className="metric"><h2>{label}</h2><p>{show(value)}</p>{detail && <small>{detail}</small>}</article>; }

export default function App() { const route = useRoute(); return route.projectId === null ? <ProjectListPage /> : route.files ? <ProjectFilesPage projectId={route.projectId} /> : route.insights ? <ProjectInsightsPage projectId={route.projectId} /> : <ProjectOverviewPage projectId={route.projectId} />; }
