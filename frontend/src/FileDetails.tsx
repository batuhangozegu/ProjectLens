import type { AnalysisResult, FileRecord } from './api/client';

function object(value: unknown): Record<string, unknown> { return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function matchingRows(value: unknown, path: string) {
  if (!Array.isArray(value)) return [];
  return value.filter((item) => { const row = object(item); return row.path === path || row.file === path || row.source === path; });
}

export function FileDetails({ file, result }: { file: FileRecord | undefined; result: AnalysisResult }) {
  if (!file) return <aside className="file-details" aria-label="File details"><h2>File details</h2><p>Select a file from the tree or dependency graph to inspect it.</p></aside>;
  const incoming = result.dependency_edges.filter((edge) => edge.target === file.path).map((edge) => edge.source).sort();
  const outgoing = result.dependency_edges.filter((edge) => edge.source === file.path).map((edge) => edge.target).sort();
  const cycleGroups = (result.cycles ?? []).filter((cycle) => cycle.includes(file.path));
  const tests = result.test_matches?.find((item) => item.source === file.path)?.tests ?? [];
  const metrics = object(result.metrics), risk = object(metrics.risk), findings = object(metrics.findings);
  const riskRows = [...matchingRows(risk.top_risks, file.path), ...matchingRows(risk.files, file.path)];
  const findingRows = [...matchingRows(findings.top_findings, file.path), ...matchingRows(findings.items, file.path)];
  return <aside className="file-details" aria-label="File details">
    <h2>File details</h2><h3 className="detail-path">{file.path}</h3>
    <dl><dt>Language</dt><dd>{file.language || 'Unknown'}</dd><dt>Class</dt><dd>{file.file_class}</dd><dt>Lines of code</dt><dd>{file.physical_loc ?? 'Unavailable'}</dd><dt>Analysis status</dt><dd>{file.analysis_status}</dd><dt>Incoming dependencies</dt><dd>{incoming.length ? incoming.length : 'None'}</dd><dt>Outgoing dependencies</dt><dd>{outgoing.length ? outgoing.length : 'None'}</dd></dl>
    {incoming.length > 0 && <section><h3>Used by</h3><ul>{incoming.map((path) => <li key={path}>{path}</li>)}</ul></section>}
    {outgoing.length > 0 && <section><h3>Depends on</h3><ul>{outgoing.map((path) => <li key={path}>{path}</li>)}</ul></section>}
    <section><h3>Cycles</h3>{cycleGroups.length ? cycleGroups.map((cycle, i) => <ul key={i}>{cycle.map((path) => <li key={path}>{path}</li>)}</ul>) : <p>Not part of a reported cycle.</p>}</section>
    <section><h3>Matching tests</h3>{tests.length ? <ul>{tests.map((test) => <li key={`${test.path}-${test.rule}`}>{test.path} <small>({test.rule})</small></li>)}</ul> : <p>No matching tests reported.</p>}</section>
    <section><h3>Risk and findings</h3>{riskRows.length || findingRows.length ? <ul>{riskRows.map((row, i) => <li key={`risk-${i}`}>Risk: {String(row.level ?? 'Reported')}{row.points !== undefined ? ` (${String(row.points)} points)` : ''}{Array.isArray(row.factors) && row.factors.length > 0 && <ul>{row.factors.map((factor: unknown, index: number) => <li key={index}>{String(object(factor).reason ?? object(factor).id ?? 'Risk factor')}</li>)}</ul>}</li>)}{findingRows.map((row, i) => <li key={`finding-${i}`}>{String(row.title ?? row.symbol ?? row.kind ?? 'Finding')}{row.severity ? ` · ${String(row.severity)}` : ''}{row.reason ? `: ${String(row.reason)}` : ''}</li>)}</ul> : <p>No file specific risk or finding details reported.</p>}</section>
  </aside>;
}
