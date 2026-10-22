import { useEffect, useState } from 'react';
import { api, type AnalysisResult, type ProjectSummary } from './api/client';
import { FileTree } from './FileTree';
import { DependencyGraph } from './DependencyGraph';
import { FileDetails } from './FileDetails';

export function ProjectFilesPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const current = await api.get<ProjectSummary>(`/projects/${projectId}`);
        if (!alive) return;
        setProject(current);
        if (current.latest_snapshot) setResult(await api.get<AnalysisResult>(`/projects/${projectId}/snapshots/latest`));
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Could not load project files.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [projectId]);
  if (loading) return <main className="shell"><p role="status">Loading files and dependencies…</p></main>;
  if (error || !project) return <main className="shell"><nav aria-label="Breadcrumb"><a href={`#/projects/${projectId}`}>← Project overview</a> · <a href="#/">All projects</a></nav><p role="alert" className="error">{error || 'Project unavailable.'}</p></main>;
  return <main className="shell">
    <header className="site-header"><a className="brand" href="#/"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header>
    <nav aria-label="Breadcrumb"><a href={`#/projects/${projectId}`}>← {project.name} overview</a></nav>
    <section className="page-intro"><p className="eyebrow">FILES AND DEPENDENCIES</p><h1>{project.name}</h1><p>Browse repository files and select a file to inspect its dependencies and analysis details.</p></section>
    {!result ? <div className="notice" role="status">{project.latest_snapshot ? 'Analysis result is not available.' : 'Analysis is queued or no snapshot has completed yet.'}</div> : <>
      {result.partial && <aside className="notice">This is a partial analysis. Some file details may be incomplete.</aside>}
      <div className="files-layout">
        <FileTree files={result.files ?? []} selectedPath={selectedPath} onSelect={setSelectedPath} />
        <div className="files-main"><DependencyGraph result={result} selectedPath={selectedPath} onSelect={setSelectedPath} /><FileDetails file={result.files.find((file) => file.path === selectedPath)} result={result} /></div>
      </div>
    </>}
  </main>;
}
