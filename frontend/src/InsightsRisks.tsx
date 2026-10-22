import { display, record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';

export function InsightsRisks({ result, projectId }: { result: AnalysisResult; projectId: number }) {
  const metrics = record(result.metrics);
  const risk = record(metrics.risk);
  const risks = Array.isArray(risk.top_risks) ? risk.top_risks : null;
  const findingsData = record(metrics.findings);
  const findings = Array.isArray(findingsData.top_findings) ? findingsData.top_findings : null;
  return <>
    <section className="panel" aria-labelledby="insights-risks-title">
      <h2 id="insights-risks-title">Risks</h2>
      {risks ? risks.length ? <ol className="ranked-list">{risks.map((item: any, index: number) => <li key={item.path ?? index}>
        <strong><span className="rank">#{index + 1}</span> {display(item.level)} risk · {item.points ?? '—'} points</strong>
        <p><a href={`#/projects/${projectId}/files`}>{display(item.path)}</a></p>
        {Array.isArray(item.factors) && item.factors.length ? <ul>{item.factors.map((factor: any, i: number) => <li key={factor.id ?? i}>{display(factor.reason)}</li>)}</ul> : <p>Risk factors are not available.</p>}
      </li>)}</ol> : <p>No non-minimal risks were reported.</p> : <p>Risk ranking is not available in this snapshot.</p>}
      {risk.basis && <p className="muted">{String(risk.basis)}</p>}
    </section>
    <section className="panel" aria-labelledby="insights-findings-title">
      <h2 id="insights-findings-title">Findings</h2>
      {findings ? findings.length ? <ol className="ranked-list">{findings.map((item: any, index: number) => <li key={item.id ?? index}>
        <strong><span className="rank">#{index + 1}</span> {display(item.kind)} · {display(item.severity)}</strong>
        <p><a href={`#/projects/${projectId}/files`}>{display(item.path)}</a>{item.symbol ? ` · ${item.symbol}` : ''}</p><p>{display(item.reason)}</p>
      </li>)}</ol> : <p>No findings were reported.</p> : <p>Findings are not available in this snapshot.</p>}
      {findingsData.truncated && <p>Showing the highest ranked findings; the list is truncated.</p>}
    </section>
  </>;
}
