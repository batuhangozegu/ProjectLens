import type { RoadmapProgress } from './api/client';
import { statusLabel, tr } from './i18n';

const statuses = ['TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED'];

function Breakdown({ title, items }: { title: string; items: Record<string, Record<string, unknown>> }) {
  const entries = Object.entries(items);
  return <section className="roadmap-breakdown" aria-label={`${title} dökümü`}>
    <h3>{title}</h3>
    {entries.length === 0 ? <p className="muted">{title === 'Bölümler' ? 'Bölüm verisi yok.' : 'Kategori verisi yok.'}</p> : <ul>
      {entries.map(([label, item]) => {
        const total = Number(item.total ?? 0);
        const completed = Number(item.completed ?? 0);
        const percent = item.percent_complete;
        return <li key={label}><span>{label}</span><span>{tr.number.format(completed)} / {tr.number.format(total)} tamamlandı{typeof percent === 'number' ? ` · %${tr.number.format(percent)}` : ''}</span></li>;
      })}
    </ul>}
  </section>;
}

export function RoadmapProgressSummary({ progress }: { progress: RoadmapProgress }) {
  return <section className="panel roadmap-summary" aria-labelledby="roadmap-progress-title">
    <div className="section-heading"><h2 id="roadmap-progress-title">Yol haritası ilerlemesi</h2><span>{progress.state === 'empty' ? 'Boş yol haritası' : `%${tr.number.format(progress.percent_complete ?? 0)} tamamlandı`}</span></div>
    {progress.state === 'empty' ? <p>Henüz görev aktarılmadı veya oluşturulmadı.</p> : <>
      <progress aria-label="Elle işaretlenen yol haritası tamamlanma oranı" max={100} value={progress.percent_complete ?? 0} />
      <p className="muted">{tr.number.format(progress.completed)} / {tr.number.format(progress.total)} görev tamamlandı · {tr.number.format(progress.remaining)} görev kaldı. Bu ilerleme hesabında yalnızca tamamlanan görevler sayılır.</p>
      <dl className="roadmap-counts">{statuses.map((status) => <div key={status}><dt>{statusLabel(status)}</dt><dd>{tr.number.format(progress.counts[status] ?? 0)}</dd></div>)}</dl>
      {progress.has_blocked && <p className="notice" role="status">Bu yol haritasında engellenen görevler var.</p>}
      <div className="roadmap-breakdowns"><Breakdown title="Bölümler" items={progress.breakdown_by_section} /><Breakdown title="Kategoriler" items={progress.breakdown_by_category} /></div>
    </>}
    <p className="muted roadmap-formula">Tamamlanma yüzdesi, tamamlanan görevlerin tüm görevlere oranıdır. Devam eden görevler kısmi puan almaz, engellenen görevler paydada kalır. Boş bir yol haritasının yüzdesi yoktur.</p>
  </section>;
}
