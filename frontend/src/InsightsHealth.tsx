import { Badge } from './components/Badge';
import { HelpText } from './components/HelpText';
import { display, record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';
import { healthLabel, codeLabel, translateText } from './i18n';

export function InsightsHealth({ result }: { result: AnalysisResult }) {
  const health = record(record(result.metrics).health);
  const components = Array.isArray(health.components) ? health.components : null;
  return <section className="panel" aria-labelledby="insights-health-title">
    <h2 id="insights-health-title">Sağlık</h2><HelpText>Sağlık, döngüler, çözülemeyen içe aktarımlar, test eşleşmeleri ve TODO/FIXME yoğunluğundan hesaplanan sezgisel bir puandır. Kod kalitesini, doğruluğunu veya test kapsamını garanti etmez.</HelpText>
    {health.score !== undefined && health.score !== null ? <p className="health-score"><strong>{display(health.score)} / 100</strong><span><Badge tone={health.level}>{health.level ? healthLabel(String(health.level)) : 'Puanlanmadı'}</Badge> · Güven: {codeLabel(health.confidence)}</span></p> : <p>{health.reason ? translateText(health.reason) : 'Bu anlık görüntüde sağlık puanı yok.'}</p>}
    {health.basis && <p>{translateText(health.basis)}</p>}
    {components ? components.length ? <div className="table-scroll"><table><caption>Sağlık bileşenleri ve açıklamaları</caption><thead><tr><th scope="col">Bileşen</th><th scope="col">Puan</th><th scope="col">Durum</th><th scope="col">Gerekçe</th></tr></thead><tbody>
      {components.map((item: any, index: number) => <tr key={item.id ?? index}><th scope="row">{item.id ? codeLabel(item.id) : display(item.label)}</th><td>{item.score === null || item.score === undefined ? 'Puanlanmadı' : `${display(item.score)} / 100`}</td><td>{item.available === false ? 'Kullanılamıyor' : 'Kullanılabilir'}</td><td>{display(item.reason)}</td></tr>)}
    </tbody></table></div> : <p>Sağlık bileşeni bildirilmedi.</p> : <p>Bu anlık görüntüde sağlık bileşeni yok.</p>}
  </section>;
}
