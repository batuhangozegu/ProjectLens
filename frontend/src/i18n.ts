export const tr = {
  unavailable: 'Kullanılamıyor',
  nav: { overview: 'Genel Bakış', files: 'Dosyalar', insights: 'Analizler', roadmap: 'Yol Haritası', ai: 'Yapay Zeka' },
  status: { TODO: 'Yapılacak', IN_PROGRESS: 'Devam ediyor', DONE: 'Tamamlandı', BLOCKED: 'Engelli' },
  priority: { LOW: 'Düşük', MEDIUM: 'Orta', HIGH: 'Yüksek', CRITICAL: 'Kritik' },
  risk: { minimal: 'En düşük', low: 'Düşük', medium: 'Orta', high: 'Yüksek', critical: 'Kritik' },
  health: { excellent: 'Çok iyi', good: 'İyi', fair: 'Orta', attention: 'İlgi gerekiyor', poor: 'Zayıf' },
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
  return codeLabel(value);
}
export function fileClassLabel(value: string): string {
  return codeLabel(value);
}
export function fileAnalysisLabel(value: string): string {
  return codeLabel(value);
}

// Stable values from analysis/*, tracking/* and app/api/*. Unknown values stay
// intact so future analyzer versions and repository-authored text remain useful.
const codes: Record<string, string> = {
  succeeded: 'Tamamlandı', completed: 'Tamamlandı', complete: 'Tamamlandı', failed: 'Başarısız', queued: 'Sırada', running: 'Sürüyor', partial: 'Kısmi', unavailable: 'Kullanılamıyor',
  python_source: 'Python kaynak kodu', dart_source: 'Dart kaynak kodu', python_test: 'Python testi', test: 'Test dosyası', config: 'Yapılandırma dosyası', documentation: 'Belgelendirme', other: 'Diğer',
  scanned: 'Tarandı', analyzed: 'Analiz edildi', analyzed_with_diagnostics: 'Tanılarla analiz edildi', parse_failed: 'Ayrıştırılamadı', unreadable: 'Okunamadı', skipped_size_limit: 'Boyut sınırı nedeniyle atlandı', skipped: 'Atlandı', unsupported: 'Desteklenmiyor',
  cycles: 'Bağımlılık döngüleri', unresolved_imports: 'Çözülemeyen içe aktarımlar', test_presence: 'Test dosyası eşleşmesi', todo_density: 'TODO/FIXME yoğunluğu',
  high: 'Yüksek', medium: 'Orta', low: 'Düşük', none: 'Yok', unknown: 'Bilinmiyor',
  insufficient_evidence: 'Yetersiz kanıt', estimated: 'Tahmin edildi', no_snapshot: 'Analiz yok', met: 'Karşılandı', unmet: 'Karşılanmadı',
  done_but_unmet: 'Tamamlandı işaretli, ölçütler eksik', evidence_complete_but_not_done: 'Kanıtlar tamam, görev açık',
  file_exists: 'Dosya varlığı', path_has_files: 'Klasörde dosya varlığı', import_edge_exists: 'İçe aktarım bağlantısı', not_in_cycle: 'Döngüde yer almama', max_todo_markers: 'TODO/FIXME üst sınırı', no_analysis_failures: 'Analiz hatası olmaması', manual_attestation: 'Elle doğrulama',
  large_function: 'Uzun fonksiyon', large_class: 'Büyük sınıf', many_members: 'Çok sayıda metot', high_fan_out: 'Çok sayıda bağımlılık', high_fan_in: 'Çok sayıda kullanan dosya', mutual_dependency: 'Karşılıklı bağımlılık', warning: 'Uyarı', notice: 'Bilgi',
  churn: 'Değişiklik sıklığı', size: 'Dosya boyutu', cycle: 'Bağımlılık döngüsü', untested: 'Test eşleşmesi yok', fan_in: 'Gelen bağımlılıklar',
  framework: 'Çatı', manifest: 'Bildirim dosyası', library: 'Kütüphane', tool: 'Araç', dependency: 'Bağımlılık', dev_dependency: 'Geliştirme bağımlılığı',
  'test framework': 'Test çatısı', 'state management': 'Durum yönetimi',
  file: 'Dosya', metric: 'Ölçüm', files: 'Dosyalar', dependency_edges: 'Bağımlılık bağlantıları', 'metrics.health': 'Sağlık ölçümleri', 'metrics.risk': 'Risk ölçümleri', 'metrics.findings': 'Bulgular',
  name: 'Ad eşleşmesi', 'name match': 'Ad eşleşmesi', import: 'İçe aktarım eşleşmesi',
  scan: 'Tarama', read: 'Okuma', parse: 'Ayrıştırma', frameworks: 'Çatı algılama', git_history: 'Git geçmişi',
  git_unavailable: 'Git kullanılamıyor', output_limit: 'Çıktı sınırı aşıldı', not_a_git_repository: 'Git deposu değil', shallow_history: 'Sığ Git geçmişi', no_commits: 'Commit yok', disabled: 'Devre dışı', not_requested: 'İstenmedi',
  '(uncategorized)': 'Kategorisiz', '(no section)': 'Bölümsüz', empty: 'Boş', in_progress: 'Devam ediyor', not_started: 'Başlamadı', truncated: 'Liste kısaltıldı',
  SyntaxError: 'Sözdizimi hatası', EncodingError: 'Kodlama hatası', NullByteError: 'Geçersiz boş bayt', TokenizeError: 'Sözcük çözümleme hatası', ParserError: 'Ayrıştırıcı hatası', UnreadableFile: 'Dosya okunamadı', UnreadableDirectory: 'Klasör okunamadı', FileTooLarge: 'Dosya çok büyük', Excluded: 'Hariç tutuldu', SymlinkSkipped: 'Sembolik bağlantı atlandı', ScanEntryError: 'Tarama hatası', UnreadablePubspec: 'pubspec.yaml okunamadı', UnreadableManifest: 'Bildirim dosyası okunamadı', InvalidPubspecName: 'Geçersiz paket adı', AmbiguousPackageName: 'Belirsiz paket adı', DartUriEscapesRepository: 'Dart adresi depo dışına çıkıyor', GitHistoryUnavailable: 'Git geçmişi kullanılamıyor',
};
export function codeLabel(value: unknown): string {
  if (value === null || value === undefined || value === '') return tr.unavailable;
  const key = String(value);
  return codes[key] ?? key;
}
export function languageLabel(value: string | null): string {
  return value ? ({ python: 'Python', dart: 'Dart', javascript: 'JavaScript', typescript: 'TypeScript', csharp: 'C#', cpp: 'C++', shell: 'Kabuk', markdown: 'Markdown', yaml: 'YAML', json: 'JSON', xml: 'XML', toml: 'TOML' } as Record<string, string>)[value] ?? value : 'Bilinmiyor';
}
export function dateLabel(value?: string | null): string {
  if (!value || Number.isNaN(Date.parse(value))) return 'Tarih bilinmiyor';
  return new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

const phrases: Record<string, string> = {
  'Completed percentage is DONE tasks divided by all tasks; IN_PROGRESS earns no partial credit, and BLOCKED tasks remain in the denominator. Empty roadmaps have no percentage.': 'Tamamlanma yüzdesi, tamamlanan görevlerin tüm görevlere oranıdır. Devam eden görevler kısmi puan almaz, engellenen görevler paydada kalır. Boş bir yol haritasının yüzdesi yoktur.',
  'Generated by AI from bounded ProjectLens analysis context; verify cited sources.': 'Sınırlı ProjectLens analiz bağlamından yapay zeka ile üretildi; belirtilen kaynakları doğrulayın.',
  'Verify cited sources.': 'Belirtilen kaynakları doğrulayın.',
  'Dependency cycles': codes.cycles,
  'Unresolved imports': codes.unresolved_imports,
  'Test file presence by name/import heuristic, not coverage': 'Ad/içe aktarım eşleşmesine göre test varlığı; test kapsamı değildir',
  'TODO/FIXME density': codes.todo_density,
  'heuristic indicator from static analysis; not a measure of correctness or coverage': 'Statik analizden hesaplanan sezgisel gösterge; doğruluk veya test kapsamı ölçüsü değildir.',
  'explainable heuristic; not a prediction of defects': 'Açıklanabilir sezgisel gösterge; hata tahmini değildir.',
  'static size/coupling thresholds; heuristic, not a defect prediction': 'Boyut ve bağımlılık eşiklerine dayalı sezgisel gösterge; hata tahmini değildir.',
  'name/import heuristics; not coverage': 'Ad/içe aktarım eşleşmesi; test kapsamı değildir.',
  'manifest declarations; code usage not inspected': 'Bildirim dosyalarına dayanır; kodda kullanım incelenmedi.',
  'commit counts from git log within the window; not a measure of defect probability': 'Seçili zaman aralığındaki Git commit sayıları; hata olasılığını ölçmez.',
  'commit limit reached; file counts cover the first 20000 in-window commits': 'Commit sınırına ulaşıldı; dosya sayıları zaman aralığındaki ilk 20.000 commit ile sınırlı.',
  'No eligible Python/Dart graph files are available (0 denominator).': 'Grafikte uygun Python/Dart dosyası yok; payda sıfır.',
  'No local or unresolved import references are available (0 denominator).': 'Yerel veya çözülemeyen içe aktarım yok; payda sıfır.',
  'No source files are available for test file presence by name/import heuristic, not coverage (0 denominator).': 'Test eşleştirmesi için kaynak dosyası yok; payda sıfır. Bu ölçüm test kapsamı değildir.',
  '0 matching test files (name/import heuristic, not coverage)': 'Eşleşen test dosyası yok (ad/içe aktarım eşleşmesi; test kapsamı değildir).',
  'manual attestation is user-reported, not automatic evidence': 'Elle doğrulama kullanıcı beyanıdır; otomatik kanıt değildir.',
  'file is absent from a partial snapshot': 'Dosya kısmi analizde bulunamadı.',
  'file is absent from the snapshot': 'Dosya analizde bulunamadı.',
  'file is present and analyzed': 'Dosya bulundu ve analiz edildi.',
  'local import edge is present': 'Yerel içe aktarım bağlantısı bulundu.',
  'source or target file is absent or not fully analyzed': 'Kaynak veya hedef dosya yok ya da tam analiz edilmedi.',
  'edge is absent from a partial snapshot': 'Bağlantı kısmi analizde bulunamadı.',
  'local import edge is absent': 'Yerel içe aktarım bağlantısı bulunamadı.',
  'file belongs to a dependency cycle': 'Dosya bir bağımlılık döngüsünde yer alıyor.',
  'file is not fully analyzed in a partial snapshot': 'Dosya kısmi analizde tam incelenmedi.',
  'file is not in a reported dependency cycle': 'Dosya bildirilen bir bağımlılık döngüsünde yer almıyor.',
  'no files are covered by this path': 'Bu yolda kapsanan dosya yok.',
  'one or more covered files have analysis failures': 'Kapsanan dosyalardan en az birinin analizi başarısız.',
  'no covered files have a known analysis failure': 'Kapsanan dosyalarda bilinen analiz hatası yok.',
  'no analysis snapshot is available': 'Analiz sonucu yok.',
  'No analysis snapshot is available; progress cannot be estimated.': 'Analiz sonucu yok; ilerleme tahmin edilemiyor.',
  'No automatic criteria produced met or unmet evidence, so no percentage is estimated.': 'Otomatik ölçütler kesin sonuç vermedi; yüzde tahmin edilmiyor.',
  'Linked files provide context only; their existence is not completion evidence.': 'Bağlantılı dosyalar bağlam sağlar; varlıkları tamamlanma kanıtı değildir.',
  'Manual attestations are reported separately and do not affect the estimate.': 'Elle doğrulamalar ayrı gösterilir ve tahmini etkilemez.',
  'Manual status is DONE while automatic evidence estimates less than 100% completion.': 'Görev tamamlandı işaretli, ancak otomatik kanıtların tamamlanma tahmini %100 altında.',
  'Automatic evidence estimates 100% with medium or high confidence while manual status is not DONE.': 'Otomatik kanıtlar orta veya yüksek güvenle %100 gösteriyor; görev henüz tamamlandı işaretli değil.',
  'Only DONE tasks count as complete.': 'Yalnızca tamamlandı işaretli görevler tamamlanmış sayılır.',
  'analysis output path excluded': 'Analiz çıktı yolu hariç tutuldu.',
  'symlink was not followed or read': 'Sembolik bağlantı izlenmedi veya okunmadı.',
  'directory excluded by scanner rules': 'Klasör tarama kuralları gereği hariç tutuldu.',
  'file excluded by scanner rules': 'Dosya tarama kuralları gereği hariç tutuldu.',
  'virtual environment detected by pyvenv.cfg': 'pyvenv.cfg ile sanal ortam algılandı.',
  'ProjectLens result JSON excluded': 'ProjectLens sonuç JSON dosyası hariç tutuldu.',
  'pubspec.yaml has no valid top-level name': 'pubspec.yaml içinde geçerli üst düzey paket adı yok.',
  'Permission denied': 'Erişim reddedildi', 'Access is denied': 'Erişim reddedildi', 'No such file or directory': 'Dosya veya klasör bulunamadı',
  'invalid syntax': 'Geçersiz sözdizimi', 'parser resource limit exceeded': 'Ayrıştırıcı kaynak sınırı aşıldı', 'decoder resource limit exceeded': 'Kod çözücü kaynak sınırı aşıldı',
  'unexpected indent': 'Beklenmeyen girinti', 'unexpected EOF while parsing': 'Ayrıştırma sırasında dosya beklenmedik biçimde sona erdi', 'unindent does not match any outer indentation level': 'Girinti önceki girinti düzeyleriyle eşleşmiyor', 'source code string cannot contain null bytes': 'Kaynak kodu boş bayt içeremez', 'source code string cannot contain null characters': 'Kaynak kodu boş karakter içeremez', 'EOF in multi-line statement': 'Çok satırlı ifade tamamlanmadan dosya sona erdi', 'EOF in multi-line string': 'Çok satırlı metin tamamlanmadan dosya sona erdi',
  'The request could not be completed.': 'İstek tamamlanamadı.',
  'Checklist item appears before any heading': 'Kontrol listesi öğesi başlıklardan önce yer alıyor', 'Checklist item has an empty title and was skipped': 'Başlığı boş olan kontrol listesi öğesi atlandı', 'Unterminated code fence; remaining lines were treated as code': 'Kod bloğu kapatılmamış; kalan satırlar kod olarak ele alındı',
  'path must be a non-empty string': 'Yol boş olmayan bir metin olmalı', 'absolute paths are not allowed': 'Mutlak yollara izin verilmez', "'..' path segments are not allowed": "'..' yol bölümlerine izin verilmez", 'control characters are not allowed': 'Kontrol karakterlerine izin verilmez', "prefix must end with '/'": "Önek '/' ile bitmeli", 'expected a file path, not a directory prefix': 'Dosya yolu bekleniyor; klasör öneki girilmiş',
  'snapshot must be a mapping': 'Analiz sonucu bir alan eşlemesi olmalı', 'criterion must be a CriterionInput': 'Ölçüt geçerli bir ölçüt girdisi olmalı', 'kind must be a string and params must be a mapping': 'Tür metin, parametreler alan eşlemesi olmalı', 'manual_attestation takes no params': 'Elle doğrulama parametre almaz', 'min_count must be an integer from 1 to 100000': 'En az dosya sayısı 1 ile 100.000 arasında tam sayı olmalı', 'max must be a non-negative integer': 'Üst sınır negatif olmayan tam sayı olmalı',
};

type Template = [RegExp, (...parts: string[]) => string];
const templates: Template[] = [
  [/^(\d+) of (\d+) graph files are in cycles \(([^)]+)\); 25% saturates the penalty\.$/, (n,t,r) => `${t} grafik dosyasının ${n} tanesi döngüde (oran: ${r}); ceza %25 oranında üst sınıra ulaşır.`],
  [/^(\d+) of (\d+) local or unresolved import references are unresolved \(([^)]+)\); external imports are excluded\.$/, (n,t,r) => `${t} yerel veya çözülemeyen içe aktarımın ${n} tanesi çözülemedi (oran: ${r}); harici içe aktarımlar hariçtir.`],
  [/^(\d+) of (\d+) source files have a matching test file by name\/import heuristic, not coverage \(([^)]+)\)\.$/, (n,t,r) => `${t} kaynak dosyasının ${n} tanesi ad/içe aktarım yoluyla testle eşleşti (oran: ${r}); bu, test kapsamı değildir.`],
  [/^(\d+) TODO\/FIXME markers across (\d+) physical LOC \(([^)]+) per KLOC\); 20 per KLOC saturates the penalty\.$/, (n,l,d) => `${l} fiziksel LOC içinde ${n} TODO/FIXME işareti (1.000 LOC başına ${d}); ceza 1.000 LOC başına 20 işarette üst sınıra ulaşır.`],
  [/^Marker data is incomplete \((\d+) files unavailable\), with (\d+) known markers across (\d+) LOC; TODO\/FIXME density cannot be scored\.$/, (n,m,l) => `${n} dosyada işaret verisi eksik. ${l} LOC içinde ${m} bilinen işaret var; TODO/FIXME yoğunluğu puanlanamıyor.`],
  [/^Known physical LOC is (\d+) and marker count is (\d+); zero LOC prevents a density score\.$/, (l,n) => `Bilinen fiziksel LOC: ${l}, işaret sayısı: ${n}; sıfır LOC nedeniyle yoğunluk puanlanamıyor.`],
  [/^Weighted mean of (\d+) available components; weights renormalized to ([\d.]+)\.$/, (n,w) => `${n} kullanılabilir bileşenin ağırlıklı ortalaması; ağırlık toplamı ${w} olarak yeniden düzenlendi.`],
  [/^Only (\d+) of 4 components are available; at least 2 are required for an overall score\.$/, n => `4 bileşenden yalnızca ${n} tanesi kullanılabilir; genel puan için en az 2 bileşen gerekir.`],
  [/^(\d+) commits in the history window$/, n => `Geçmiş aralığında ${n} commit`],
  [/^(\d+) physical LOC$/, n => `${n} fiziksel LOC`],
  [/^file is in (\d+) dependency cycle group\(s\)$/, n => `Dosya ${n} bağımlılık döngüsü grubunda yer alıyor`],
  [/^(\d+) incoming local dependency edges$/, n => `${n} gelen yerel bağımlılık bağlantısı`],
  [/^Function spans (\d+) lines; threshold is (\d+) lines\.$/, (n,t) => `Fonksiyon ${n} satır uzunluğunda; eşik ${t} satır.`],
  [/^Class-like declaration spans (\d+) lines; threshold is (\d+) lines\.$/, (n,t) => `Sınıf benzeri bildirim ${n} satır uzunluğunda; eşik ${t} satır.`],
  [/^Class-like declaration has (\d+) direct methods; threshold is (\d+) methods\.$/, (n,t) => `Sınıf benzeri bildirimde ${n} doğrudan metot var; eşik ${t} metot.`],
  [/^File has (\d+) distinct local dependencies; threshold is (\d+)\.$/, (n,t) => `Dosyanın ${n} farklı yerel bağımlılığı var; eşik ${t}.`],
  [/^File has (\d+) distinct local dependents; threshold is (\d+); it is a central dependency where changes have wide impact, not necessarily a defect\.$/, (n,t) => `Dosyayı ${n} farklı yerel dosya kullanıyor; eşik ${t}. Merkezi bir bağımlılık olduğu için değişikliklerin etkisi geniştir; bu mutlaka bir hata değildir.`],
  [/^file exists but is not fully analyzed \((.+)\)$/, s => `Dosya var, ancak tam analiz edilmedi (${codeLabel(s)}).`],
  [/^file analysis status is not recognized \((.+)\)$/, s => `Dosyanın analiz durumu tanınmıyor (${codeLabel(s)}).`],
  [/^found (\d+) fully analyzed matching files \(minimum (\d+)\)$/, (n,m) => `${n} tam analiz edilmiş eşleşen dosya bulundu (en az ${m}).`],
  [/^found (\d+) fully analyzed matching files; minimum is (\d+)( and snapshot is partial)?$/, (n,m,p) => `${n} tam analiz edilmiş eşleşen dosya bulundu; en az ${m} gerekli${p ? ' ve analiz kısmi' : ''}.`],
  [/^known marker total (\d+) exceeds maximum (\d+)(; more markers may exist)?$/, (n,m,p) => `Bilinen ${n} işaret, ${m} üst sınırını aşıyor${p ? '; daha fazla işaret olabilir' : ''}.`],
  [/^known marker total (\d+) is within maximum (\d+), but coverage is incomplete$/, (n,m) => `Bilinen ${n} işaret, ${m} üst sınırını aşmıyor; ancak inceleme eksik.`],
  [/^marker total (\d+) is at most (\d+)$/, (n,m) => `İşaret sayısı ${n}; ${m} üst sınırını aşmıyor.`],
  [/^Estimate uses (\d+) met and (\d+) unmet automatic criteria; (\d+) unknown criteria are excluded from the percentage\.$/, (m,u,n) => `Tahmin, karşılanan ${m} ve karşılanmayan ${u} otomatik ölçüte dayanıyor; belirsiz ${n} ölçüt yüzdeye katılmadı.`],
  [/^Confidence is (\w+)( because the snapshot is partial)?\.$/, (c,p) => `Güven düzeyi: ${codeLabel(c)}${p ? '; analiz kısmi olduğu için düşürüldü' : ''}.`],
  [/^All (\d+) automatic criteria are unknown\.$/, n => `${n} otomatik ölçütün tamamı belirsiz.`],
  [/^(.+): TODO\/FIXME data incomplete$/, p => `${p}: TODO/FIXME verisi eksik`], [/^known total: (\d+)$/, n => `Bilinen toplam: ${n}`],
  [/^invalid_criterion: (.+)$/, s => `Geçersiz ölçüt: ${translateText(s)}`],
  [/^unknown criterion kind (.+)$/, s => `Bilinmeyen ölçüt türü: ${s}`],
  [/^unexpected params (.+); missing params (.+)$/, (e,m) => `Beklenmeyen parametreler: ${e}; eksik parametreler: ${m}`],
  [/^(language|file_class) must be a string$/, s => `${s === 'language' ? 'Dil' : 'Dosya sınıfı'} metin olmalı`],
  [/^(\d+) bytes exceeds limit of (\d+)$/, (n,m) => `${n} bayt, ${m} bayt sınırını aşıyor`],
  [/^unterminated block comment \(line (\d+)\)$/, n => `Kapatılmamış blok yorumu (satır ${n})`], [/^unterminated string \(line (\d+)\)$/, n => `Kapatılmamış metin (satır ${n})`],
  [/^(.+) \(line (\d+)\)$/, (s,n) => `${translateText(s)} (satır ${n})`],
  [/^package name (.+) is declared by multiple pubspec.yaml files$/, s => `${s} paket adı birden fazla pubspec.yaml dosyasında bildirilmiş`],
  [/^(package|relative) URI (.+) escapes the repository root$/, (k,u) => `${k === 'package' ? 'Paket' : 'Göreli'} adresi ${u} depo kökünün dışına çıkıyor`],
  [/^(\w+Error): (.+)$/, (k,s) => `${codeLabel(k)}: ${translateText(s)}`],
  [/^Duplicate checklist title disambiguated as occurrence (\d+)$/, n => `Yinelenen kontrol listesi başlığı ${n}. oluşum olarak ayrıldı`],
  [/^expected an indented block(?: after (.+))?$/, s => `Girintili blok bekleniyor${s ? `: ${s}` : ''}`],
  [/^unterminated string literal(?: \(detected at line (\d+)\))?$/, n => `Kapatılmamış metin${n ? ` (satır ${n})` : ''}`],
  [/^(.+) was never closed$/, s => `${s} kapatılmamış`],
  [/^Failed to fetch$|^fetch failed$|^NetworkError when attempting to fetch resource\.$/, () => 'Sunucuya bağlanılamadı. Bağlantınızı kontrol edip yeniden deneyin.'],
];
export function translateText(value: unknown): string {
  if (value === null || value === undefined || value === '') return tr.unavailable;
  const text = String(value);
  if (phrases[text]) return phrases[text];
  if (codes[text]) return codes[text];
  for (const [pattern, translate] of templates) {
    const match = text.match(pattern);
    if (match) return translate(...match.slice(1));
  }
  return text;
}

const errors: Record<string, string> = {
  project_not_found: 'Proje bulunamadı.', project_missing: 'Proje artık kullanılamıyor.', project_analysis_active: 'Analiz sıradayken veya sürerken proje silinemez. Analizin bitmesini bekleyin.',
  snapshot_not_found: 'Bu proje için tamamlanmış analiz bulunamadı.', job_not_found: 'Analiz işi bulunamadı.', task_not_found: 'Bu projede görev bulunamadı.', link_not_found: 'Görev dosya bağlantısı bulunamadı.', criterion_not_found: 'Kabul ölçütü bulunamadı.', task_item_not_found: 'Görev öğesi bulunamadı.',
  validation_error: 'İstek doğrulanamadı. Girdiğiniz bilgileri kontrol edin.', internal_error: 'Sunucuda bir hata oluştu. Yeniden deneyin.', queue_full: 'Analiz kuyruğu dolu. Biraz sonra yeniden deneyin.', invalid_repository_url: 'Geçerli, herkese açık bir HTTPS GitHub depo adresi girin.',
  invalid_kind: 'Açıklama türü geçersiz. Depo, mimari veya risk seçin.',
  invalid_status_transition: 'Görev bu duruma geçirilemiyor. Mevcut durumunu kontrol edin.', duplicate_link: 'Bu yol göreve zaten bağlı.', link_limit_reached: 'Görevin dosya bağlantısı sınırına ulaşıldı.', criteria_limit_reached: 'Görevin kabul ölçütü sınırına ulaşıldı.',
  request_too_large: 'İstek sunucunun boyut sınırını aşıyor.', assessment_task_limit: 'Değerlendirilebilecek görev sayısı sınırı aşıldı.', roadmap_import_conflict: 'Eşzamanlı yol haritası aktarımı çakıştı. Yeniden deneyin.', invalid_checklist: 'Markdown kontrol listesi okunamadı.',
  worker_unavailable: 'Analiz zamanlanamadı. Yeniden deneyin.', analysis_failed: 'Analiz tamamlanamadı.', checkout_timeout: 'Depoyu indirme süresi aşıldı.', checkout_failed: 'Depo indirilemedi veya indirme sınırı aşıldı.', invalid_ref: 'İstenen dal veya commit indirilemedi.',
  ai_disabled: 'Yapay zeka açıklamaları devre dışı.', ai_unavailable: 'Yapay zeka hizmeti kullanılamıyor.', ai_provider_error: 'Yapay zeka hizmetinde hata oluştu.', ai_timeout: 'Yapay zeka hizmetinden zamanında yanıt alınamadı.', invalid_context: 'Analiz bağlamı hazırlanamadı.', ai_invalid_response: 'Yapay zeka hizmetinin yanıtı kullanılamıyor.', ai_auth_failed: 'Yapay zeka hizmetinin kimlik doğrulaması başarısız oldu.',
};
export function apiErrorMessage(code: string | null | undefined, message: string): string { return errors[code ?? ''] ?? message; }
