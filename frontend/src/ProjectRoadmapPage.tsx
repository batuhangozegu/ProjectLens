import { useCallback, useEffect, useState } from 'react';
import { api, type ProjectSummary, type RoadmapProgress, type TaskAssessment, type TaskList, type TaskResponse, type TaskStatus } from './api/client';
import { RoadmapProgressSummary } from './RoadmapProgressSummary';
import { TaskTrackingCard } from './TaskTrackingCard';

const statusOrder: TaskStatus[] = ['IN_PROGRESS', 'TODO', 'BLOCKED', 'DONE'];
const statusLabels: Record<TaskStatus, string> = { TODO: 'To do', IN_PROGRESS: 'In progress', DONE: 'Done', BLOCKED: 'Blocked' };

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
      catch (e) { return [task.id, e instanceof Error ? e.message : 'Could not load assessment.'] as const; }
    }));
    if (!aliveCheck()) return;
    const nextAssessments: Record<number, TaskAssessment> = {}, nextErrors: Record<number, string> = {};
    for (const [id, result] of results) if (typeof result === 'string') nextErrors[id] = result; else nextAssessments[id] = result;
    setAssessments(nextAssessments); setAssessmentErrors(nextErrors);
  }, [projectId]);

  useEffect(() => {
    let alive = true;
    void load(() => alive).catch((e) => { if (alive) setError(e instanceof Error ? e.message : 'Could not load roadmap.'); }).finally(() => { if (alive) setLoading(false); });
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

  if (loading) return <main className="shell"><p role="status">Loading roadmap…</p></main>;
  if (error || !project || !progress) return <main className="shell"><nav aria-label="Breadcrumb"><a href={`#/projects/${projectId}`}>← Project overview</a> · <a href="#/">All projects</a></nav><p role="alert" className="error">{error || 'Roadmap unavailable.'}</p></main>;
  const grouped = Object.fromEntries(statusOrder.map((status) => [status, tasks.filter((task) => task.status === status)])) as Record<TaskStatus, TaskResponse[]>;
  return <main className="shell">
    <header className="site-header"><a className="brand" href="#/"><span className="mark" aria-hidden="true">PL</span>ProjectLens</a></header>
    <nav aria-label="Breadcrumb"><a href={`#/projects/${projectId}`}>← {project.name} overview</a></nav>
    <section className="page-intro"><p className="eyebrow">ROADMAP AND CODE-AWARE TRACKING</p><h1>{project.name}</h1><p>Manual task status and analysis-based evidence are shown separately. Code evidence never changes the manual status.</p></section>
    <RoadmapProgressSummary progress={progress} />
    {tasks.length === 0 ? <section className="empty roadmap-empty"><h2>No roadmap tasks</h2><p>Send the contents of the repository’s TODO.md checklist to the roadmap import API. Importing is repeatable and preserves manual task edits; tasks can also be created through the tasks API.</p><code>POST /api/v1/projects/{projectId}/roadmap/import</code><pre><code>{'{ "markdown": "- [ ] Example task" }'}</code></pre></section> : <section aria-label="Roadmap tasks" className="roadmap-groups">
      {statusOrder.map((status) => <section key={status} aria-labelledby={`group-${status}`}><h2 id={`group-${status}`}>{statusLabels[status]} <span>({grouped[status].length})</span></h2>{grouped[status].length === 0 ? <p className="muted">No tasks in this status.</p> : grouped[status].map((task) => <TaskTrackingCard key={task.id} task={task} assessment={assessments[task.id]} assessmentError={assessmentErrors[task.id]} onStatusChange={changeStatus} />)}</section>)}
    </section>}
  </main>;
}
