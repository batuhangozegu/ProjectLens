import type { AnalysisResult } from './api/client';
import { record, display } from './InsightsMetrics';
import { codeLabel, healthLabel, languageLabel, riskLabel, translateText } from './i18n';
import { Badge } from './components/Badge';
import { Card } from './components/Card';
import { HelpText } from './components/HelpText';

export function QuickLinks({ projectId }: { projectId: number }) {
  return <nav className="quick-links" aria-label="Projeyi keşfedin">{[
    ['files', 'Dosyalar ve bağımlılıklar', 'Dosyaların birbirini nasıl kullandığını görün.'],
    ['insights', 'Ölçümler ve analizler', 'Sağlık puanının ve risklerin nedenlerini inceleyin.'],
    ['roadmap', 'Yol haritası', 'Görevlerin durumunu ve kod kanıtlarını takip edin.'],
    ['ai', 'Yapay zeka', 'Analiz verileri için isteğe bağlı açıklama alın.'],
  ].map(([path, title, description]) => <a href={`#/projects/${projectId}/${path}`} key={path}><strong>{title} <span aria-hidden="true">↗</span></strong><span>{description}</span></a>)}</nav>;
}

export function OverviewSummary({ result, projectId }: { result: AnalysisResult; projectId: number }) {
  const metrics = record(result.metrics), health = record(metrics.health), risk = record(metrics.risk), findings = record(metrics.findings);
  const counts = record(risk.counts_by_level);
  const risks: any[] = Array.isArray(risk.top_risks) ? risk.top_risks : [];
  const items: any[] = Array.isArray(findings.top_findings) ? findings.top_findings : Array.isArray(findings.items) ? findings.items : [];
  const level = ['critical', 'high', 'medium', 'low', 'minimal'].find(value => counts[value] > 0) ?? risks[0]?.level;
  const reasons = Array.isArray(health.components) ? health.components.filter((c: any) => c?.reason) : [];
  const concerns = [
    ...risks.filter(item => item.level !== 'minimal').map(item => ({ title: item.path, detail: `${riskLabel(item.level)} risk${item.factors?.[0]?.reason ? `: ${translateText(item.factors[0].reason)}` : ''}` })),
    ...items.map(item => ({ title: translateText(typeof item === 'string' ? item : item.kind ?? item.title ?? item.path ?? 'Bulgu'), detail: typeof item === 'string' ? '' : translateText(item.reason ?? item.path ?? '') })),
  ].slice(0, 3);
  const verdict = ({ good: 'Genel göstergeler olumlu.', excellent: 'Genel göstergeler çok iyi.', fair: 'Bazı alanları gözden geçirin.', attention: 'Öncelikli inceleme gerekiyor.', poor: 'İyileştirme için zaman ayırın.' } as Record<string, string>)[health.level] ?? 'Sağlık için yeterli veri yok.';
  const languages = [...new Set(result.files.map(file => languageLabel(file.language)))];
  return <>
    <section className="understand" aria-labelledby="understand-title"><p className="eyebrow">ÖNCE BÜTÜNÜ GÖRÜN</p><h2 id="understand-title">Bu projeyi anlamak için</h2><div className="summary-grid">
      <Card title="Sağlık puanı" className="score-card"><p className="score"><strong>{display(health.score)}</strong>{health.score != null && <span> / 100</span>}</p><Badge tone={health.level}>{health.level ? healthLabel(health.level) : 'Puanlanmadı'}</Badge><p className="verdict">{verdict}</p><HelpText>Statik analizden hesaplanan sezgisel bir gösterge. Kod kalitesini, doğruluğunu veya test kapsamını garanti etmez.</HelpText></Card>
      <Card title="Risk düzeyi"><Badge tone={level}>{level ? riskLabel(level) : 'Kullanılamıyor'} risk</Badge><p>{counts.high !== undefined ? `${display(counts.high)} dosya yüksek risk düzeyinde.` : 'Risk ayrıntıları analizlere göre değişir.'}</p><HelpText>Boyut, değişiklik sıklığı ve bağımlılıklar inceleme önceliğini belirler. Bu düzey hata tahmini değildir.</HelpText><a href={`#/projects/${projectId}/insights`}>Risk gerekçelerine bak →</a></Card>
      <Card title="Öncelikli 3 konu">{concerns.length ? <ol className="concern-list">{concerns.map((item, i) => <li key={i}><strong>{item.title}</strong>{item.detail && <p>{item.detail}</p>}</li>)}</ol> : <p>{Array.isArray(risk.top_risks) || Array.isArray(findings.top_findings) ? 'Bildirilen öncelikli konu yok. Bu, projenin hatasız olduğunu göstermez.' : 'Öncelikli konuları belirlemek için yeterli veri yok.'}</p>}</Card>
    </div></section>
    {(result.partial || result.diagnostics?.length > 0) && <aside className="notice" aria-label="Analiz tanıları"><strong>{result.partial ? 'Kısmi analiz' : 'Analiz notları'}</strong><p>{display(result.diagnostics?.length ?? 0)} tanı bildirildi. Bazı sonuçlar eksik olabilir.</p></aside>}
    <QuickLinks projectId={projectId} />
    <Card title="Deponun ölçeği"><div className="metric-grid">{[
      ['Dosyalar', metrics.total_file_count, 'Analiz sırasında bulunan dosyalar.'],
      ['Fiziksel satır sayısı', record(metrics.physical_loc).total, 'Boş satırlar ve yorumlar dahil LOC; karmaşıklık ölçüsü değildir.'],
      ['Python dosyaları', metrics.python_file_count, 'Python olarak tanınan dosyalar.'],
      ['Python satır sayısı', record(metrics.python_loc).total, 'Python dosyalarındaki fiziksel LOC.'],
      ['Diller', languages.length ? languages.join(', ') : null, 'Dosya uzantılarından algılanır.'],
      ['Çatılar', result.frameworks?.length ? result.frameworks.map(f => f.name).join(', ') : 'Algılanmadı', 'Bildirimlerden algılanır; kodda kullanım garantisi değildir.'],
    ].map(([title, value, help]) => <article className="metric" key={title}><h3>{title}</h3><p>{display(value)}</p><HelpText>{help}</HelpText></article>)}</div></Card>
    <Card title="Sağlık gerekçeleri">{reasons.length ? <ul>{reasons.map((item: any, i: number) => <li key={i}>{translateText(item.reason)}</li>)}</ul> : <p>{translateText(health.reason)}</p>}</Card>
    {result.diagnostics?.length > 0 && <Card title="Tanı bilgileri"><ul>{result.diagnostics.map((d, i) => <li key={i}><strong>{codeLabel(d.stage)} · {codeLabel(d.error_type)}</strong>{d.file && <p><code>{d.file}</code></p>}<p>{translateText(d.message)}</p></li>)}</ul></Card>}
  </>;
}
