import type { AnalysisResult } from './api/client';
import { tr, translateText, languageLabel, codeLabel } from './i18n';

const unavailable = tr.unavailable;
const record = (value: unknown): Record<string, any> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, any> : {};
const display = (value: unknown) => value === null || value === undefined || value === '' ? unavailable : typeof value === 'number' ? new Intl.NumberFormat('tr-TR').format(value) : translateText(value);

export function InsightsMetrics({ result }: { result: AnalysisResult }) {
  const metrics = record(result.metrics);
  const physical = record(metrics.physical_loc);
  const languages = new Map<string, number>();
  for (const file of result.files ?? []) if (file.language) languages.set(file.language, (languages.get(file.language) ?? 0) + 1);
  const testMatches = record(metrics.test_matching);
  const tests = typeof testMatches.sources_total === 'number'
    ? `${tr.number.format(testMatches.sources_with_matching_test ?? 0)} / ${tr.number.format(testMatches.sources_total)} kaynak dosyayla eşleşti`
    : result.test_matches ? `${tr.number.format(result.test_matches.filter((item) => item.tests?.length).length)} kaynak dosyayla eşleşti` : unavailable;
  const rows = [
    ['Fiziksel satır sayısı', display(physical.total), `Boş satırlar ve yorumlar dahil LOC; karmaşıklık ölçüsü değildir.${physical.unavailable_file_count ? ` ${tr.number.format(physical.unavailable_file_count)} dosyanın satır sayısı kullanılamıyor.` : ''}`],
    ['Dosyalar', display(metrics.total_file_count ?? result.files?.length), 'Bu anlık görüntüde bulunan depo dosyaları'],
    ['Diller', languages.size ? [...languages].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([name, count]) => `${languageLabel(name)} (${tr.number.format(count)})`).join(', ') : result.files ? 'Algılanmadı' : unavailable, 'Dosya uzantılarından algılanır; dilin kullanım yoğunluğunu ölçmez.'],
    ['Çatılar', result.frameworks?.length ? result.frameworks.map((item) => `${item.name} (${languageLabel(item.ecosystem)} · ${codeLabel(item.kind)})`).join(', ') : result.frameworks ? 'Algılanmadı' : unavailable, 'Bildirim dosyalarından algılanır; kodda kullanım incelenmez.'],
    ['Test eşleşmeleri', tests, 'Ad/içe aktarım eşleşmesi; test kapsamı değildir'],
  ];
  return <section className="panel" aria-labelledby="insights-metrics-title">
    <h2 id="insights-metrics-title">Ölçümler</h2>
    <div className="table-scroll"><table><caption>Depo boyutu, teknolojiler ve test eşleşmeleri özeti</caption><thead><tr><th scope="col">Ölçüm</th><th scope="col">Değer</th><th scope="col">Ayrıntılar</th></tr></thead>
      <tbody>{rows.map(([name, value, detail]) => <tr key={name}><th scope="row">{name}</th><td>{value}</td><td>{detail}</td></tr>)}</tbody></table></div>
  </section>;
}

export { display, record };
