import { useEffect, useState, type FormEvent } from 'react';
import { ApiError, api, type ProjectSummary } from './api/client';
import { AIExplanationResult, type AIExplanation } from './AIExplanationResult';
import { ProjectPageChrome } from './PageChrome';
import { tr } from './i18n';

const kinds = [
  { value: 'repository', label: 'Depo genel bakışı' },
  { value: 'architecture', label: 'Mimari' },
  { value: 'risk', label: 'Risk' },
] as const;

function explainError(error: unknown): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : 'Yapay zeka açıklaması istenemedi.';
  if (error.code === 'ai_disabled') return 'Sunucu yapay zeka açıklamalarını devre dışı bırakmış. Açıklama oluşturulmadı.';
  if (error.code === 'ai_unavailable' || error.code === 'ai_provider_error') return 'Yapay zeka hizmeti kullanılamıyor veya yapılandırılmamış. Daha sonra yeniden deneyin ya da sunucu yöneticisiyle görüşün.';
  if (error.code === 'ai_timeout') return 'Yapay zeka hizmetinden yanıt alınamadı. Yeniden deneyebilirsiniz.';
  if (error.code === 'invalid_context') return 'Seçilen analiz bağlamı hazırlanamadı. Daha yeni veya kapsamlı bir analiz deneyin.';
  if (error.code === 'ai_invalid_response') return 'Yapay zeka hizmeti kullanılamayan bir yanıt verdi. Daha sonra yeniden deneyin.';
  if (error.code === 'snapshot_not_found') return 'Açıklanabilecek tamamlanmış analiz yok. Önce analiz çalıştırın.';
  if (error.code === 'project_not_found') return 'Proje bulunamadı.';
  if (error.status === 413) return 'İstek sunucu boyut sınırını aştı. Daha yeni veya küçük bir analiz deneyin.';
  if (error.status === 429) return 'Sunucuya çok fazla istek gönderiliyor. Yeniden denemeden önce bekleyin.';
  if (error.status === 422) return 'İstek kabul edilmedi. Açıklama türünü kontrol edip yeniden deneyin.';
  return error.message || 'Yapay zeka açıklama isteği başarısız oldu.';
}

export function ProjectAIInsightsPage({ projectId }: { projectId: number }) {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [kind, setKind] = useState<(typeof kinds)[number]['value']>('repository');
  const [result, setResult] = useState<AIExplanation | null>(null);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    api.get<ProjectSummary>(`/projects/${projectId}`).then((current) => { if (alive) setProject(current); })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : 'Proje yüklenemedi.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [projectId]);

  async function requestExplanation(event: FormEvent) {
    event.preventDefault();
    setError(''); setResult(null); setRequesting(true);
    try {
      const response = await api.post<AIExplanation>(`/projects/${projectId}/ai/explanations`, { kind, snapshot: 'latest' });
      setResult(response);
    } catch (e) { setError(explainError(e)); }
    finally { setRequesting(false); }
  }

  if (loading) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.ai} /><h1>Yapay zeka analizleri</h1><p role="status">Yapay zeka analizleri yükleniyor…</p></main>;
  if (error && !project) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.ai} /><h1>Yapay zeka analizleri</h1><p role="alert" className="error">{error}</p><button className="secondary" onClick={() => location.reload()}>Yeniden dene</button></main>;
  if (!project) return <main id="main-content" tabIndex={-1} className="shell"><ProjectPageChrome projectId={projectId} current={tr.nav.ai} /><h1>Yapay zeka analizleri</h1><p role="alert" className="error">Proje kullanılamıyor.</p><button className="secondary" onClick={() => location.reload()}>Yeniden dene</button></main>;

  return <main id="main-content" tabIndex={-1} className="shell">
    <ProjectPageChrome projectId={projectId} current={tr.nav.ai} />
    <section className="page-intro"><p className="eyebrow">İSTEĞE BAĞLI YAPAY ZEKA ANALİZLERİ</p><h1>{project.name}</h1><p>Kaydedilen son analiz için yapay zeka açıklaması isteyin. İsteği göndermeden veri paylaşılmaz.</p></section>
    <section className="notice ai-data-note" aria-labelledby="ai-data-title">
      <h2 id="ai-data-title">Paylaşılan veriler</h2>
      <p>Yapay zeka isteğe bağlıdır ve devre dışı bırakılmış olabilir. Etkinse ProjectLens, kaydedilen analizden seçilmiş küçük bir bağlamı yapılandırılmış harici yapay zeka hizmetine gönderir. Bu bağlam depo dosya yollarını, dosya türlerini, bağımlılık ilişkilerini, özet ölçümleri, sağlık ve risk bulgularını ve çatı kanıtlarını içerebilir.</p>
      <p>Bağlam varsayılan olarak 16 KB ile sınırlıdır. Kaynak kodu veya dosya içerikleri, depo adresi, kimlik bilgileri, depo kopyası ya da analizin tamamı gönderilmez. Bu uygulamada yapay zeka hizmeti henüz yapılandırılmamış; bu nedenle hizmetin kullanılamadığı bildirilebilir.</p>
      <p>Depodan alınan veriler ve yapay zeka yanıtı doğrulanmamış içeriktir. Önerileri belirtilen analiz kaynaklarıyla karşılaştırın.</p>
    </section>
    {!project.latest_snapshot && <div className="notice" role="status">Henüz tamamlanmış analiz yok. Açıklama istemeden önce analiz çalıştırın.</div>}
    <form className="panel ai-request" onSubmit={requestExplanation}>
      <label htmlFor="ai-kind">Açıklama türü</label>
      <select id="ai-kind" value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}>
        {kinds.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
      </select>
      <p className="muted">Kaydedilen en son analiz kullanılır. Hizmet isteğinde varsayılan olarak 512 belirteç yanıt sınırı ve 20 saniye zaman aşımı uygulanır.</p>
      <button disabled={requesting || !project.latest_snapshot}>{requesting ? 'Açıklama isteniyor…' : 'Yapay zeka açıklaması iste'}</button>
      {requesting && <p role="status">Yapay zeka hizmetinden yanıt bekleniyor…</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
    {result && <AIExplanationResult result={result} />}
  </main>;
}
