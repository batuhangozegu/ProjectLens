import { useEffect, useState } from 'react';
import { api, type AnalysisResult, type ProjectSummary } from './api/client';
import { FileTree } from './FileTree';
import { DependencyGraph } from './DependencyGraph';
import { FileDetails } from './FileDetails';
import { ProjectPageChrome } from './PageChrome';
import { tr } from './i18n';

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
      } catch (e) { if (alive) setError(e instanceof Error ? e.message : 'Proje dosyaları yüklenemedi.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [projectId]);
  if (loading) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.files} /><h1>Dosyalar ve bağımlılıklar</h1><p role="status">Dosyalar ve bağımlılıklar yükleniyor…</p></main>;
  if (error || !project) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.files} /><h1>Dosyalar ve bağımlılıklar</h1><p role="alert" className="error">{error || 'Proje kullanılamıyor.'}</p><button className="secondary" onClick={() => location.reload()}>Yeniden dene</button></main>;
  return <main id="main-content" tabIndex={-1} className="shell">
    <ProjectPageChrome projectId={projectId} current={tr.nav.files} />
    <section className="page-intro"><p className="eyebrow">DOSYALAR VE BAĞIMLILIKLAR</p><h1>{project.name}</h1><p>Depo dosyalarına göz atın; bağımlılıklarını ve analiz ayrıntılarını görmek için bir dosya seçin.</p></section>
    {!result ? <div className="notice" role="status">{project.latest_snapshot ? 'Analiz sonucu kullanılamıyor.' : 'Analiz sırada veya henüz bir anlık görüntü tamamlanmadı.'}</div> : <>
      {result.partial && <aside className="notice">Bu kısmi bir analizdir. Bazı dosya ayrıntıları eksik olabilir.</aside>}
      <div className="files-layout">
        <FileTree files={result.files ?? []} selectedPath={selectedPath} onSelect={setSelectedPath} />
        <div className="files-main"><DependencyGraph result={result} selectedPath={selectedPath} onSelect={setSelectedPath} /><FileDetails file={result.files.find((file) => file.path === selectedPath)} result={result} /></div>
      </div>
    </>}
  </main>;
}
