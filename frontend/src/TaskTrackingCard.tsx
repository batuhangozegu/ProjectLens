import { Badge } from './components/Badge';
import { useState } from 'react';
import type { TaskAssessment, TaskResponse, TaskStatus } from './api/client';
import { priorityLabel, statusLabel, codeLabel, translateText } from './i18n';

const statuses: TaskStatus[] = ['TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED'];
type Detail = Record<string, unknown>;
function object(value: unknown): Detail { return value && typeof value === 'object' && !Array.isArray(value) ? value as Detail : {}; }
function label(value: unknown) { return value === null || value === undefined || value === '' ? 'Kullanılamıyor' : translateText(value); }

function AssessmentDetails({ assessment }: { assessment: TaskAssessment }) {
  const context = assessment.context.map(object);
  const criteria = assessment.criteria_results.map(object);
  return <div className="assessment-details">
    <p className="help-text">Tahmini tamamlanma, karşılanan otomatik ölçütlerin kesin sonuç veren ölçütlere oranıdır. Belirsiz ölçütler hesaba katılmaz. Güven düzeyi verinin yeterliliğini gösterir; görev durumunu kendiliğinden değiştirmez.</p>
    <dl className="assessment-meta">
      <div><dt>Kanıt durumu</dt><dd>{label(assessment.state)}</dd></div>
      <div><dt>Tahmini tamamlanma</dt><dd>{assessment.estimated_percent === null ? 'Tahmin yok' : `%${assessment.estimated_percent}`}</dd></div>
      <div><dt>Güven düzeyi</dt><dd>{label(assessment.confidence)}</dd></div>
      <div><dt>Görev durumu</dt><dd>{statusLabel(assessment.manual_status)}</dd></div>
      <div><dt>Uyumsuzluk</dt><dd>{assessment.divergence ? codeLabel(assessment.divergence) : 'Yok'}</dd></div>
    </dl>
    {assessment.divergence && <aside className="notice" aria-label="Görev durumu uyumsuzluğu"><strong>Uyumsuzluk: {codeLabel(assessment.divergence)}</strong><p>{translateText(assessment.divergence_reason)}</p></aside>}
    <section><h4>Değerlendirme gerekçeleri</h4>{assessment.reasons.length ? <ul>{assessment.reasons.map((reason, index) => <li key={index}>{translateText(reason)}</li>)}</ul> : <p className="muted">Gerekçe belirtilmedi.</p>}</section>
    <section><h4>Kabul ölçütleri</h4>{criteria.length ? <ul className="criteria-list">{criteria.map((criterion, index) => <li key={String(criterion.criterion_id ?? index)}><strong>{label(criterion.kind)} · {label(criterion.outcome)}</strong><span>{label(criterion.reason)}</span>{Array.isArray(criterion.evidence) && criterion.evidence.length > 0 && <small>Kanıt: {criterion.evidence.map(translateText).join(', ')}</small>}</li>)}</ul> : <p className="muted">Bu görevle ilişkili kabul ölçütü yok.</p>}</section>
    <section><h4>Bağlantılı dosyalar</h4>{context.length ? <ul>{context.map((file, index) => <li key={`${label(file.path)}-${index}`}><code>{label(file.path)}</code> — {file.exists ? 'bulundu' : 'bulunamadı'}{file.analyzed === true ? ', analiz edildi' : ''}{typeof file.analyzed_file_count === 'number' ? `, ${file.analyzed_file_count} dosya analiz edildi` : ''}</li>)}</ul> : <p className="muted">Bağlantılı dosya yok. Dosya bağlantıları bağlam sağlar; tamamlanma kanıtı sayılmaz.</p>}</section>
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
    catch (e) { setError(e instanceof Error ? e.message : 'Görev durumu güncellenemedi.'); }
    finally { setPending(false); }
  }
  return <article className="task-card" aria-labelledby={`task-${task.id}-title`}>
    <div className="task-heading"><div><h3 id={`task-${task.id}-title`}>{task.title}</h3><p>{task.description || 'Açıklama yok.'}</p></div><Badge tone={task.priority.toLowerCase()}>Öncelik: {priorityLabel(task.priority)}</Badge></div>
    <div className="task-controls"><p><strong>{task.category || 'Kategorisiz'}</strong>{task.source === 'import' ? ' · TODO.md dosyasından aktarıldı' : ' · elle eklenen görev'}</p><label htmlFor={`task-${task.id}-status`}>Görev durumu</label><select id={`task-${task.id}-status`} value={task.status} disabled={pending} onChange={(event) => void changeStatus(event.target.value as TaskStatus)}>{statuses.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select>{pending && <span role="status">Kaydediliyor…</span>}</div>
    {(error || assessmentError) && <p className="error task-error" role="alert">{error || assessmentError}</p>}
    <p className="assessment-summary">{assessment ? assessment.estimated_percent === null ? codeLabel(assessment.state) : `Kanıtlara göre %${assessment.estimated_percent} · ${codeLabel(assessment.confidence)} güven` : assessmentError ? 'Değerlendirme kullanılamıyor.' : 'Değerlendirme yükleniyor…'}</p><details className="assessment"><summary>Kod destekli değerlendirme ayrıntıları</summary>{assessment ? <AssessmentDetails assessment={assessment} /> : <p className="muted" role={assessmentError ? undefined : 'status'}>{assessmentError ? 'Değerlendirme kullanılamıyor.' : 'Değerlendirme yükleniyor…'}</p>}</details>
  </article>;
}
