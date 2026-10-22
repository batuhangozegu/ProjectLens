import { useCallback, useEffect, useState } from 'react';
import { api, type ProjectSummary, type RoadmapProgress, type TaskAssessment, type TaskList, type TaskResponse, type TaskStatus } from './api/client';
import { RoadmapProgressSummary } from './RoadmapProgressSummary';
import { TaskTrackingCard } from './TaskTrackingCard';
import { ProjectPageChrome } from './PageChrome';
import { tr } from './i18n';

const statusOrder: TaskStatus[] = ['IN_PROGRESS', 'TODO', 'BLOCKED', 'DONE'];
const statusLabels: Record<TaskStatus, string> = tr.status;

async function loadTasks(projectId: number) {
  const items: TaskResponse[] = [];
  let offset = 0;
  let total = 0;
  do {
    const page = await api.get<TaskList>(`/projects/${projectId}/tasks?limit=100&offset=${offset}`);
    items.push(...page.items); total = page.total; offset += page.items.length;
    if (page.items.length === 0) break;
  } while (offset < total && offset < 10000);
  return { items, total };
}

export function ProjectRoadmapPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [progress, setProgress] = useState<RoadmapProgress | null>(null);
  const [assessments, setAssessments] = useState<Record<number, TaskAssessment>>({});
  const [assessmentErrors, setAssessmentErrors] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (aliveCheck: () => boolean = () => true) => {
    const [current, taskResult, progressResult] = await Promise.all([
      api.get<ProjectSummary>(`/projects/${projectId}`), loadTasks(projectId), api.get<RoadmapProgress>(`/projects/${projectId}/roadmap/progress`),
    ]);
    if (!aliveCheck()) return;
    setProject(current); setTasks(taskResult.items); setProgress(progressResult);
    const results = await Promise.all(taskResult.items.map(async (task) => {
      try { return [task.id, await api.get<TaskAssessment>(`/projects/${projectId}/tasks/${task.id}/assessment`)] as const; }
      catch (e) { return [task.id, e instanceof Error ? e.message : 'Değerlendirme yüklenemedi.'] as const; }
    }));
    if (!aliveCheck()) return;
    const nextAssessments: Record<number, TaskAssessment> = {}, nextErrors: Record<number, string> = {};
    for (const [id, result] of results) if (typeof result === 'string') nextErrors[id] = result; else nextAssessments[id] = result;
    setAssessments(nextAssessments); setAssessmentErrors(nextErrors);
  }, [projectId]);

  useEffect(() => {
    let alive = true;
    void load(() => alive).catch((e) => { if (alive) setError(e instanceof Error ? e.message : 'Yol haritası yüklenemedi.'); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [load]);

  async function changeStatus(task: TaskResponse, status: TaskStatus) {
    const updated = await api.patch<TaskResponse>(`/projects/${projectId}/tasks/${task.id}`, { status });
    setTasks((current) => current.map((item) => item.id === updated.id ? updated : item));
    try {
      const [nextProgress, assessment] = await Promise.all([
        api.get<RoadmapProgress>(`/projects/${projectId}/roadmap/progress`),
        api.get<TaskAssessment>(`/projects/${projectId}/tasks/${task.id}/assessment`),
      ]);
      setProgress(nextProgress); setAssessments((current) => ({ ...current, [task.id]: assessment }));
      setAssessmentErrors((current) => { const next = { ...current }; delete next[task.id]; return next; });
    } catch { /* The status is saved; the next page load refreshes derived data. */ }
  }

  if (loading) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.roadmap} /><h1>Yol Haritası</h1><p role="status">Yol haritası yükleniyor…</p></main>;
  if (error || !project || !progress) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.roadmap} /><h1>Yol Haritası</h1><p role="alert" className="error">{error || 'Yol haritası kullanılamıyor.'}</p><button className="secondary" onClick={() => location.reload()}>Yeniden dene</button></main>;
  const grouped = Object.fromEntries(statusOrder.map((status) => [status, tasks.filter((task) => task.status === status)])) as Record<TaskStatus, TaskResponse[]>;
  return <main id="main-content" tabIndex={-1} className="shell">
    <ProjectPageChrome projectId={projectId} current={tr.nav.roadmap} />
    <section className="page-intro"><p className="eyebrow">YOL HARİTASI VE KOD DESTEKLİ TAKİP</p><h1>{project.name}</h1><p>Görev durumu ve analiz kanıtları ayrı gösterilir. Kod kanıtları görev durumunu değiştirmez.</p></section>
    <RoadmapProgressSummary progress={progress} />
    {tasks.length === 0 ? <section className="empty roadmap-empty"><h2>Yol haritasında görev yok</h2><p>Depodaki TODO.md kontrol listesini yol haritası aktarım API'sine gönderin. Aktarım tekrarlanabilir ve elle yapılan görev düzenlemelerini korur; görevler görevler API'siyle de oluşturulabilir.</p><code>POST /api/v1/projects/{projectId}/roadmap/import</code><pre><code>{'{ "markdown": "- [ ] Örnek görev" }'}</code></pre></section> : <section aria-label="Yol haritası görevleri" className="roadmap-groups">
      {statusOrder.map((status) => <section key={status} aria-labelledby={`group-${status}`}><h2 id={`group-${status}`}>{statusLabels[status]} <span>({tr.number.format(grouped[status].length)})</span></h2>{grouped[status].length === 0 ? <p className="muted">Bu durumda görev yok.</p> : grouped[status].map((task) => <TaskTrackingCard key={task.id} task={task} assessment={assessments[task.id]} assessmentError={assessmentErrors[task.id]} onStatusChange={changeStatus} />)}</section>)}
    </section>}
  </main>;
}
