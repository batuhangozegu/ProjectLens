import type { AnalysisResult } from './api/client';

const unavailable = 'Not available';
const record = (value: unknown): Record<string, any> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, any> : {};
const display = (value: unknown) => value === null || value === undefined || value === '' ? unavailable : String(value);

export function InsightsMetrics({ result }: { result: AnalysisResult }) {
  const metrics = record(result.metrics);
  const physical = record(metrics.physical_loc);
  const languages = new Map<string, number>();
  for (const file of result.files ?? []) if (file.language) languages.set(file.language, (languages.get(file.language) ?? 0) + 1);
  const testMatches = record(metrics.test_matching);
  const tests = typeof testMatches.sources_total === 'number'
    ? `${testMatches.sources_with_matching_test ?? 0} of ${testMatches.sources_total} source files matched`
    : result.test_matches ? `${result.test_matches.filter((item) => item.tests?.length).length} source files matched` : unavailable;
  const rows = [
    ['Physical LOC', display(physical.total), physical.unavailable_file_count ? `${physical.unavailable_file_count} file counts unavailable` : 'All available file counts included'],
    ['Files', display(metrics.total_file_count ?? result.files?.length), 'Repository files found in this snapshot'],
    ['Languages', languages.size ? [...languages].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([name, count]) => `${name} (${count})`).join(', ') : result.files ? 'None detected' : unavailable, 'Counted from file records'],
    ['Frameworks', result.frameworks?.length ? result.frameworks.map((item) => `${item.name} (${item.ecosystem})`).join(', ') : result.frameworks ? 'None detected' : unavailable, 'Detected from manifest declarations'],
    ['Test matches', tests, 'Name/import heuristic; this is not test coverage'],
  ];
  return <section className="panel" aria-labelledby="insights-metrics-title">
    <h2 id="insights-metrics-title">Metrics</h2>
    <div className="table-scroll"><table><caption>Repository size, technology and test matching summary</caption><thead><tr><th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Details</th></tr></thead>
      <tbody>{rows.map(([name, value, detail]) => <tr key={name}><th scope="row">{name}</th><td>{value}</td><td>{detail}</td></tr>)}</tbody></table></div>
  </section>;
}

export { display, record };
