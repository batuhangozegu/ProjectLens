import { record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';

export function InsightsActivity({ result, projectId }: { result: AnalysisResult; projectId: number }) {
  const history = record(record(result.metrics).git_history);
  const available = history.available === true;
  const churn = Array.isArray(history.top_churn) ? history.top_churn : null;
  return <section className="panel" aria-labelledby="insights-activity-title">
    <h2 id="insights-activity-title">Activity</h2>
    {!available ? <p>Git activity is not available for this snapshot{history.reason ? ` (${String(history.reason).replaceAll('_', ' ')}).` : '. History collection may not have been enabled.'}</p> : <>
      <p>{history.commits_in_window ?? 0} commits in the last {history.window_days ?? 'unknown'} days · {history.files_with_churn ?? 0} files changed · HEAD date: {history.head_commit_date ?? 'Not available'}</p>
      {history.note && <p>{String(history.note)}</p>}
      {churn ? churn.length ? <div className="table-scroll"><table><caption>Files with the most commits during the recorded history window</caption><thead><tr><th scope="col">File</th><th scope="col">Commits</th><th scope="col">Authors</th><th scope="col">Last change</th></tr></thead><tbody>
        {churn.map((item: any, index: number) => <tr key={item.path ?? index}><th scope="row"><a href={`#/projects/${projectId}/files`}>{item.path}</a></th><td>{item.commits}</td><td>{item.authors}</td><td>{item.last_commit_date}</td></tr>)}
      </tbody></table></div> : <p>No file churn was recorded in this history window.</p> : <p>File churn details are not available.</p>}
      {history.basis && <p className="muted">{String(history.basis)}</p>}
    </>}
  </section>;
}
