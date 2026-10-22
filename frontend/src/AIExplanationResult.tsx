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
    <p className="eyebrow">AI-GENERATED · ADVISORY</p>
    <h2 id="ai-result-title">{result.kind[0]?.toUpperCase()}{result.kind.slice(1)} explanation</h2>
    <p className="ai-untrusted">AI output can be inaccurate or incomplete. Treat it as untrusted advice and verify claims against the cited analysis sources.</p>
    <div className="ai-answer">{result.text.split(/\n{2,}/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
    {result.sources_used?.length ? <section aria-labelledby="ai-sources-title"><h3 id="ai-sources-title">Analysis sources provided</h3><ul>{result.sources_used.map((source, index) => <li key={`${sourceLabel(source)}-${index}`}><code>{sourceLabel(source)}</code></li>)}</ul></section> : <p className="muted">The response did not include source references.</p>}
    {result.disclaimer && <p className="muted">{result.disclaimer}</p>}
    {result.context_budget && <p className="muted">Context sent: {result.context_budget.used_bytes ?? 'unknown'} of {result.context_budget.max_bytes ?? 'unknown'} bytes{result.context_budget.truncated ? ' (some sections were omitted to meet the size limit)' : ''}.</p>}
  </section>;
}
