import type { RoadmapProgress } from './api/client';

const statuses = ['TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED'];

function Breakdown({ title, items }: { title: string; items: Record<string, Record<string, unknown>> }) {
  const entries = Object.entries(items);
  return <section className="roadmap-breakdown" aria-label={`${title} breakdown`}>
    <h3>{title}</h3>
    {entries.length === 0 ? <p className="muted">No {title.toLowerCase()} data.</p> : <ul>
      {entries.map(([label, item]) => {
        const total = Number(item.total ?? 0);
        const completed = Number(item.completed ?? 0);
        const percent = item.percent_complete;
        return <li key={label}><span>{label}</span><span>{completed} of {total} done{typeof percent === 'number' ? ` · ${percent}%` : ''}</span></li>;
      })}
    </ul>}
  </section>;
}

export function RoadmapProgressSummary({ progress }: { progress: RoadmapProgress }) {
  return <section className="panel roadmap-summary" aria-labelledby="roadmap-progress-title">
    <div className="section-heading"><h2 id="roadmap-progress-title">Roadmap progress</h2><span>{progress.state === 'empty' ? 'Empty roadmap' : `${progress.percent_complete ?? 0}% complete`}</span></div>
    {progress.state === 'empty' ? <p>No tasks have been imported or created yet.</p> : <>
      <progress aria-label="Manual roadmap completion" max={100} value={progress.percent_complete ?? 0} />
      <p className="muted">{progress.completed} of {progress.total} tasks done · {progress.remaining} remaining. Only DONE tasks count toward this manual progress total.</p>
      <dl className="roadmap-counts">{statuses.map((status) => <div key={status}><dt>{status.replace('_', ' ')}</dt><dd>{progress.counts[status] ?? 0}</dd></div>)}</dl>
      {progress.has_blocked && <p className="notice" role="status">This roadmap has blocked tasks.</p>}
      <div className="roadmap-breakdowns"><Breakdown title="Sections" items={progress.breakdown_by_section} /><Breakdown title="Categories" items={progress.breakdown_by_category} /></div>
    </>}
    <p className="muted roadmap-formula">{progress.formula}</p>
  </section>;
}
