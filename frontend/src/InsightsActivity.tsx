import { record } from './InsightsMetrics';
import type { AnalysisResult } from './api/client';

export function InsightsActivity({ result, projectId }: { result: AnalysisResult; projectId: number }) {
  const history = record(record(result.metrics).git_history);
  const available = history.available === true;
  const churn = Array.isArray(history.top_churn) ? history.top_churn : null;
  return <section className="panel" aria-labelledby="insights-activity-title">
    <h2 id="insights-activity-title">Etkinlik</h2>
    {!available ? <p>Bu anlık görüntüde Git etkinliği yok{history.reason ? ` (${String(history.reason).replaceAll('_', ' ')}).` : '. Geçmiş toplama etkinleştirilmemiş olabilir.'}</p> : <>
      <p>Son {history.window_days ?? 'bilinmeyen'} günde {history.commits_in_window ?? 0} commit · değişen dosya: {history.files_with_churn ?? 0} · HEAD tarihi: {history.head_commit_date ?? 'Kullanılamıyor'}</p>
      {history.note && <p>{String(history.note)}</p>}
      {churn ? churn.length ? <div className="table-scroll"><table><caption>Kayıtlı geçmiş aralığında en fazla commit alan dosyalar</caption><thead><tr><th scope="col">Dosya</th><th scope="col">Commit</th><th scope="col">Katkıda bulunanlar</th><th scope="col">Son değişiklik</th></tr></thead><tbody>
        {churn.map((item: any, index: number) => <tr key={item.path ?? index}><th scope="row"><a href={`#/projects/${projectId}/files`}>{item.path}</a></th><td>{item.commits}</td><td>{item.authors}</td><td>{item.last_commit_date}</td></tr>)}
      </tbody></table></div> : <p>Bu geçmiş aralığında dosya değişikliği kaydı yok.</p> : <p>Dosya değişikliği ayrıntıları kullanılamıyor.</p>}
      {history.basis && <p className="muted">{String(history.basis)}</p>}
    </>}
  </section>;
}
