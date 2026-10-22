import type { AnalysisResult, FileRecord } from './api/client';
import { fileAnalysisLabel, fileClassLabel, riskLabel, tr, translateText, codeLabel, languageLabel } from './i18n';

function object(value: unknown): Record<string, unknown> { return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function matchingRows(value: unknown, path: string) {
  if (!Array.isArray(value)) return [];
  return value.filter((item) => { const row = object(item); return row.path === path || row.file === path || row.source === path; });
}

export function FileDetails({ file, result }: { file: FileRecord | undefined; result: AnalysisResult }) {
  if (!file) return <aside className="file-details" aria-label="Dosya ayrıntıları"><h2>Dosya ayrıntıları</h2><p>İncelemek için ağaçtan veya bağımlılık grafiğinden bir dosya seçin.</p></aside>;
  const incoming = result.dependency_edges.filter((edge) => edge.target === file.path).map((edge) => edge.source).sort();
  const outgoing = result.dependency_edges.filter((edge) => edge.source === file.path).map((edge) => edge.target).sort();
  const cycleGroups = (result.cycles ?? []).filter((cycle) => cycle.includes(file.path));
  const tests = result.test_matches?.find((item) => item.source === file.path)?.tests ?? [];
  const metrics = object(result.metrics), risk = object(metrics.risk), findings = object(metrics.findings);
  const riskRows = [...matchingRows(risk.top_risks, file.path), ...matchingRows(risk.files, file.path)];
  const findingRows = [...matchingRows(findings.top_findings, file.path), ...matchingRows(findings.items, file.path)];
  return <aside className="file-details" aria-label="Dosya ayrıntıları">
    <h2>Dosya ayrıntıları</h2><p className="help-text">Gelen bağlantılar bu dosyayı kullananları, giden bağlantılar bu dosyanın kullandıklarını sayar. Test eşleşmesi test kapsamını ölçmez.</p><h3 className="detail-path">{file.path}</h3>
    <dl><dt>Dil</dt><dd>{languageLabel(file.language)}</dd><dt>Sınıf</dt><dd>{fileClassLabel(file.file_class)}</dd><dt>Kod satırları</dt><dd>{file.physical_loc === null ? 'Kullanılamıyor' : tr.number.format(file.physical_loc)}</dd><dt>Analiz durumu</dt><dd>{fileAnalysisLabel(file.analysis_status)}</dd><dt>Gelen bağımlılıklar</dt><dd>{tr.number.format(incoming.length)}</dd><dt>Giden bağımlılıklar</dt><dd>{tr.number.format(outgoing.length)}</dd></dl>
    {incoming.length > 0 && <section><h3>Kullananlar</h3><ul>{incoming.map((path) => <li key={path}>{path}</li>)}</ul></section>}
    {outgoing.length > 0 && <section><h3>Bağımlı olduğu dosyalar</h3><ul>{outgoing.map((path) => <li key={path}>{path}</li>)}</ul></section>}
    <section><h3>Döngüler</h3>{cycleGroups.length ? cycleGroups.map((cycle, i) => <ul key={i}>{cycle.map((path) => <li key={path}>{path}</li>)}</ul>) : <p>Bildirilen bir döngüde yer almıyor.</p>}</section>
    <section><h3>Eşleşen testler</h3>{tests.length ? <ul>{tests.map((test) => <li key={`${test.path}-${codeLabel(test.rule)}`}>{test.path} <small>({codeLabel(test.rule)})</small></li>)}</ul> : <p>Eşleşen test bildirilmedi.</p>}</section>
    <section><h3>Riskler ve bulgular</h3>{riskRows.length || findingRows.length ? <ul>{riskRows.map((row, i) => <li key={`risk-${i}`}>Risk: {riskLabel(String(row.level ?? 'Bildirildi'))}{row.points !== undefined ? ` (${String(row.points)} puan)` : ''}{Array.isArray(row.factors) && row.factors.length > 0 && <ul>{row.factors.map((factor: unknown, index: number) => <li key={index}>{translateText(object(factor).reason ?? object(factor).id ?? 'Risk etkeni')}</li>)}</ul>}</li>)}{findingRows.map((row, i) => <li key={`finding-${i}`}>{translateText(row.kind ?? row.title ?? row.symbol ?? 'Bulgu')}{row.severity ? ` · ${codeLabel(row.severity)}` : ''}{row.reason ? `: ${translateText(row.reason)}` : ''}</li>)}</ul> : <p>Dosyaya özgü risk veya bulgu ayrıntısı bildirilmedi.</p>}</section>
  </aside>;
}
