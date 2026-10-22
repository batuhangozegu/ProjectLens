import { display, record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';
import { healthLabel } from './i18n';

export function InsightsHealth({ result }: { result: AnalysisResult }) {
  const health = record(record(result.metrics).health);
  const components = Array.isArray(health.components) ? health.components : null;
  return <section className="panel" aria-labelledby="insights-health-title">
    <h2 id="insights-health-title">Sağlık</h2>
    {health.score !== undefined ? <p className="health-score"><strong>{display(health.score)} / 100</strong><span>Düzey: {healthLabel(String(health.level))} · Güven: {display(health.confidence)}</span></p> : <p>{health.reason || 'Bu anlık görüntüde sağlık puanı yok.'}</p>}
    {health.basis && <p>{String(health.basis)}</p>}
    {components ? components.length ? <div className="table-scroll"><table><caption>Sağlık bileşenleri ve açıklamaları</caption><thead><tr><th scope="col">Bileşen</th><th scope="col">Puan</th><th scope="col">Durum</th><th scope="col">Gerekçe</th></tr></thead><tbody>
      {components.map((item: any, index: number) => <tr key={item.id ?? index}><th scope="row">{display(item.label ?? item.id)}</th><td>{item.score === null || item.score === undefined ? 'Puanlanmadı' : `${display(item.score)} / 100`}</td><td>{item.available === false ? 'Kullanılamıyor' : 'Kullanılabilir'}</td><td>{display(item.reason)}</td></tr>)}
    </tbody></table></div> : <p>Sağlık bileşeni bildirilmedi.</p> : <p>Bu anlık görüntüde sağlık bileşeni yok.</p>}
  </section>;
}
