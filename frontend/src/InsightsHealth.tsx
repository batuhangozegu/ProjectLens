import { display, record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';

export function InsightsHealth({ result }: { result: AnalysisResult }) {
  const health = record(record(result.metrics).health);
  const components = Array.isArray(health.components) ? health.components : null;
  return <section className="panel" aria-labelledby="insights-health-title">
    <h2 id="insights-health-title">Health</h2>
    {health.score !== undefined ? <p className="health-score"><strong>{display(health.score)} / 100</strong><span>Level: {display(health.level)} · Confidence: {display(health.confidence)}</span></p> : <p>{health.reason || 'Health score is not available in this snapshot.'}</p>}
    {health.basis && <p>{String(health.basis)}</p>}
    {components ? components.length ? <div className="table-scroll"><table><caption>Health components and their explanations</caption><thead><tr><th scope="col">Component</th><th scope="col">Score</th><th scope="col">Status</th><th scope="col">Reason</th></tr></thead><tbody>
      {components.map((item: any, index: number) => <tr key={item.id ?? index}><th scope="row">{display(item.label ?? item.id)}</th><td>{item.score === null || item.score === undefined ? 'Not scored' : `${item.score} / 100`}</td><td>{item.available === false ? 'Unavailable' : 'Available'}</td><td>{display(item.reason)}</td></tr>)}
    </tbody></table></div> : <p>No health components were reported.</p> : <p>Health components are not available in this snapshot.</p>}
  </section>;
}
