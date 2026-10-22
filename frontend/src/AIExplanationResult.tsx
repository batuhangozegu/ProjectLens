import { explanationKindLabel, tr } from './i18n';

export interface AIExplanation {
  kind: string;
  text: string;
  sources_used?: unknown[];
  context_budget?: { max_bytes?: number; used_bytes?: number; truncated?: boolean };
  usage?: { input_tokens?: number; output_tokens?: number; model?: string };
  disclaimer?: string;
}

function sourceLabel(source: unknown): string {
  if (typeof source === 'string') return source;
  if (!source || typeof source !== 'object') return String(source);
  const item = source as Record<string, unknown>;
  return [item.path, item.key, item.kind].filter((value) => typeof value === 'string').join(' · ') || JSON.stringify(source);
}

export function AIExplanationResult({ result }: { result: AIExplanation }) {
  return <section className="panel ai-result" aria-labelledby="ai-result-title">
    <p className="eyebrow">YAPAY ZEKA ÜRETİMİ · ÖNERİ NİTELİĞİNDE</p>
    <h2 id="ai-result-title">{explanationKindLabel(result.kind)} açıklaması</h2>
    <p className="ai-untrusted">Yapay zeka çıktısı hatalı veya eksik olabilir. Önerileri doğrulanmamış kabul edin ve belirtilen analiz kaynaklarıyla karşılaştırın.</p>
    <div className="ai-answer">{result.text.split(/\n{2,}/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
    {result.sources_used?.length ? <section aria-labelledby="ai-sources-title"><h3 id="ai-sources-title">Kullanılan analiz kaynakları</h3><ul>{result.sources_used.map((source, index) => <li key={`${sourceLabel(source)}-${index}`}><code>{sourceLabel(source)}</code></li>)}</ul></section> : <p className="muted">Yanıtta kaynak belirtilmedi.</p>}
    {result.disclaimer && <p className="muted">{result.disclaimer}</p>}
    {result.context_budget && <p className="muted">Gönderilen bağlam: {result.context_budget.used_bytes === undefined ? 'bilinmiyor' : tr.number.format(result.context_budget.used_bytes)} / {result.context_budget.max_bytes === undefined ? 'bilinmiyor' : tr.number.format(result.context_budget.max_bytes)} bayt{result.context_budget.truncated ? ' (boyut sınırına uyması için bazı bölümler çıkarıldı)' : ''}.</p>}
  </section>;
}
