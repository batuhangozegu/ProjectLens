import { display, record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';
import { riskLabel } from './i18n';

export function InsightsRisks({ result, projectId }: { result: AnalysisResult; projectId: number }) {
  const metrics = record(result.metrics);
  const risk = record(metrics.risk);
  const risks = Array.isArray(risk.top_risks) ? risk.top_risks : null;
  const findingsData = record(metrics.findings);
  const findings = Array.isArray(findingsData.top_findings) ? findingsData.top_findings : null;
  return <>
    <section className="panel" aria-labelledby="insights-risks-title">
      <h2 id="insights-risks-title">Riskler</h2>
      {risks ? risks.length ? <ol className="ranked-list">{risks.map((item: any, index: number) => <li key={item.path ?? index}>
        <strong><span className="rank">#{index + 1}</span> {riskLabel(String(item.level))} risk · {item.points ?? '—'} puan</strong>
        <p><a href={`#/projects/${projectId}/files`}>{display(item.path)}</a></p>
        {Array.isArray(item.factors) && item.factors.length ? <ul>{item.factors.map((factor: any, i: number) => <li key={factor.id ?? i}>{display(factor.reason)}</li>)}</ul> : <p>Risk etkenleri kullanılamıyor.</p>}
      </li>)}</ol> : <p>En düşük düzeyin üzerindeki risk bildirilmedi.</p> : <p>Bu anlık görüntüde risk sıralaması yok.</p>}
      {risk.basis && <p className="muted">{String(risk.basis)}</p>}
    </section>
    <section className="panel" aria-labelledby="insights-findings-title">
      <h2 id="insights-findings-title">Bulgular</h2>
      {findings ? findings.length ? <ol className="ranked-list">{findings.map((item: any, index: number) => <li key={item.id ?? index}>
        <strong><span className="rank">#{index + 1}</span> {display(item.kind)} · {display(item.severity)}</strong>
        <p><a href={`#/projects/${projectId}/files`}>{display(item.path)}</a>{item.symbol ? ` · ${item.symbol}` : ''}</p><p>{display(item.reason)}</p>
      </li>)}</ol> : <p>Bulgu bildirilmedi.</p> : <p>Bu anlık görüntüde bulgu yok.</p>}
      {findingsData.truncated && <p>En yüksek sıradaki bulgular gösteriliyor; liste kısaltıldı.</p>}
    </section>
  </>;
}
