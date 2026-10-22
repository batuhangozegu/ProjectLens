export const tr = {
  unavailable: 'Kullanılamıyor',
  nav: { overview: 'Genel Bakış', files: 'Dosyalar', insights: 'Analizler', roadmap: 'Yol Haritası', ai: 'Yapay Zeka' },
  status: { TODO: 'Yapılacak', IN_PROGRESS: 'Devam ediyor', DONE: 'Tamamlandı', BLOCKED: 'Engelli' },
  priority: { LOW: 'Düşük', MEDIUM: 'Orta', HIGH: 'Yüksek', CRITICAL: 'Kritik' },
  risk: { minimal: 'En düşük', low: 'Düşük', medium: 'Orta', high: 'Yüksek', critical: 'Kritik' },
  health: { excellent: 'Çok iyi', good: 'İyi', fair: 'Orta', poor: 'Zayıf' },
  number: new Intl.NumberFormat('tr-TR'),
  confirmDelete: 'Bu projeyi silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.',
  confirm: 'Evet, projeyi sil', cancel: 'Vazgeç', delete: 'Sil', deleteProject: 'Projeyi sil',
} as const;

export function statusLabel(value: string): string { return tr.status[value as keyof typeof tr.status] ?? value; }
export function priorityLabel(value: string): string { return tr.priority[value as keyof typeof tr.priority] ?? value; }
export function riskLabel(value: string): string { return tr.risk[value as keyof typeof tr.risk] ?? value; }
export function healthLabel(value: string): string { return tr.health[value as keyof typeof tr.health] ?? value; }
export function explanationKindLabel(value: string): string {
  return ({ repository: 'Depo genel bakışı', architecture: 'Mimari', risk: 'Risk' } as Record<string, string>)[value] ?? value;
}
export function snapshotStatusLabel(value: string): string {
  return ({ succeeded: 'Tamamlandı', failed: 'Başarısız', queued: 'Sırada', running: 'Sürüyor', completed: 'Tamamlandı', partial: 'Kısmi' } as Record<string, string>)[value] ?? value;
}
export function fileClassLabel(value: string): string {
  return ({ python_source: 'Python kaynak kodu', python_test: 'Python testi', test: 'Test dosyası', config: 'Yapılandırma dosyası', documentation: 'Belgelendirme' } as Record<string, string>)[value] ?? value;
}
export function fileAnalysisLabel(value: string): string {
  return ({ analyzed: 'Analiz edildi', skipped: 'Atlandı', failed: 'Başarısız', unsupported: 'Desteklenmiyor' } as Record<string, string>)[value] ?? value;
}
