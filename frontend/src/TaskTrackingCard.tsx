import { useState } from 'react';
import type { TaskAssessment, TaskResponse, TaskStatus } from './api/client';

const statuses: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED'];
type Detail = Record<string, unknown>;
function object(value: unknown): Detail { return value && typeof value === 'object' && !Array.isArray(value) ? value as Detail : {}; }
function label(value: unknown) { return value === null || value === undefined || value === '' ? 'Not available' : String(value); }

function AssessmentDetails({ assessment }: { assessment: TaskAssessment }) {
  const context = assessment.context.map(object);
  const criteria = assessment.criteria_results.map(object);
  return <div className="assessment-details">
    <dl className="assessment-meta">
      <div><dt>Evidence state</dt><dd>{label(assessment.state.replaceAll('_', ' '))}</dd></div>
      <div><dt>Estimated completion</dt><dd>{assessment.estimated_percent === null ? 'No estimate' : `${assessment.estimated_percent}%`}</dd></div>
      <div><dt>Confidence</dt><dd>{label(assessment.confidence)}</dd></div>
      <div><dt>Manual status</dt><dd>{assessment.manual_status.replaceAll('_', ' ')}</dd></div>
      <div><dt>Divergence</dt><dd>{assessment.divergence ? assessment.divergence.replaceAll('_', ' ') : 'None'}</dd></div>
    </dl>
    {assessment.divergence && <aside className="notice" aria-label="Status divergence"><strong>Divergence: {assessment.divergence.replaceAll('_', ' ')}</strong><p>{assessment.divergence_reason}</p></aside>}
    <section><h4>Assessment reasons</h4>{assessment.reasons.length ? <ul>{assessment.reasons.map((reason, index) => <li key={index}>{String(reason)}</li>)}</ul> : <p className="muted">No reasons provided.</p>}</section>
    <section><h4>Acceptance criteria</h4>{criteria.length ? <ul className="criteria-list">{criteria.map((criterion, index) => <li key={String(criterion.criterion_id ?? index)}><strong>{label(criterion.kind)} · {label(criterion.outcome)}</strong><span>{label(criterion.reason)}</span>{Array.isArray(criterion.evidence) && criterion.evidence.length > 0 && <small>Evidence: {criterion.evidence.map(String).join(', ')}</small>}</li>)}</ul> : <p className="muted">No acceptance criteria are linked to this task.</p>}</section>
    <section><h4>Linked files</h4>{context.length ? <ul>{context.map((file, index) => <li key={`${label(file.path)}-${index}`}><code>{label(file.path)}</code> — {file.exists ? 'found' : 'not found'}{file.analyzed === true ? ', analyzed' : ''}{typeof file.analyzed_file_count === 'number' ? `, ${file.analyzed_file_count} analyzed files` : ''}</li>)}</ul> : <p className="muted">No files are linked. File links provide context and do not count as completion evidence.</p>}</section>
  </div>;
}

export function TaskTrackingCard({ task, assessment, assessmentError, onStatusChange }: {
  task: TaskResponse;
  assessment?: TaskAssessment;
  assessmentError?: string;
  onStatusChange: (task: TaskResponse, status: TaskStatus) => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  async function changeStatus(status: TaskStatus) {
    setError(''); setPending(true);
    try { await onStatusChange(task, status); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not update task status.'); }
    finally { setPending(false); }
  }
  return <article className="task-card" aria-labelledby={`task-${task.id}-title`}>
    <div className="task-heading"><div><h3 id={`task-${task.id}-title`}>{task.title}</h3><p>{task.description || 'No description.'}</p></div><span className={`priority priority-${task.priority.toLowerCase()}`}>{task.priority}</span></div>
    <div className="task-controls"><p><strong>{task.category || 'Uncategorized'}</strong>{task.source === 'import' ? ' · imported from TODO.md' : ' · manual task'}</p><label htmlFor={`task-${task.id}-status`}>Manual status</label><select id={`task-${task.id}-status`} value={task.status} disabled={pending} onChange={(event) => void changeStatus(event.target.value as TaskStatus)}>{statuses.map((status) => <option key={status} value={status}>{status.replace('_', ' ')}</option>)}</select>{pending && <span role="status">Saving…</span>}</div>
    {(error || assessmentError) && <p className="error task-error" role="alert">{error || assessmentError}</p>}
    <details className="assessment" open><summary>Code-aware assessment</summary>{assessment ? <AssessmentDetails assessment={assessment} /> : <p className="muted" role={assessmentError ? undefined : 'status'}>{assessmentError ? 'Assessment unavailable.' : 'Loading assessment…'}</p>}</details>
  </article>;
}
