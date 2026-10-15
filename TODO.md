# ProjectLens TODO

Bu dosya geliştirme sırasının kaynağıdır. İşler küçük adımlarla yapılır; her tamamlanan adımın doğrulaması ve commit'i olur. Frontend en son yapılır. İşaretler yalnızca gerçekten tamamlanan işlerde güncellenir.

## 0 — Mimari ve repository hazırlığı

- [x] Mevcut klasörü ve Git durumunu kontrol et.
- [x] Proje/paket/CLI adını ProjectLens / projectlens olarak belirle.
- [x] Mimariyi, domain modellerini ve pipeline sınırlarını belgele.
- [x] Kaynak ve test dizinleri için başlangıç yapısını oluştur.
- [x] README ve aşamalı TODO listesini hazırla.

Kabul: Uygulama kodu olmadan, uygulanacak yapı ve ilk milestone sınırları okunabilir durumda.

## 1 — Local Python analysis engine

### 1.1 — Çalıştırılabilir paket ve sonuç sözleşmesi

- [x] Python alt sürümünü ve minimum bağımlılıkları belirle; pyproject.toml oluştur.
- [x] projectlens paketini, modül girişini ve CLI argümanlarını oluştur.
- [x] Dataclass modelleri, JSON şema sürümü ve parser Protocol tanımla.
- [x] Kurulum, --help ve sonuç serileştirme kontrollerini yap.
- [x] README'ye gerçek kurulum komutlarını ekle; doğrula ve commit at.

### 1.2 — Repository scanner

- [x] Kök yol doğrulaması, kararlı dosya ağacı ve dil/sınıf tespiti ekle.
- [x] Varsayılan hariç tutmalar, symlink politikası ve dosya boyutu sınırını uygula.
- [x] .gitignore desteğinin ilk sürüm kapsamını belirle ve belgele.
- [x] Boş klasör, erişim hatası, Windows path ve hariç tutma testleri yaz.
- [x] Doğrula ve commit at.

### 1.3 — Python parser

- [x] AST ile fonksiyon/class sembolleri ve import kayıtları çıkar.
- [x] Encoding ve syntax hatalarını dosya bazlı tanılara dönüştür.
- [x] Yorum token'larından TODO/FIXME say; string içeriklerini hariç tut.
- [x] Relative import, alias, multiline import ve hatalı dosya testleri yaz.
- [x] Doğrula ve commit at.

### 1.4 — Dependency graph (sıradaki adım)

- [ ] Yerel modül indeksini ve import çözümlemesini oluştur.
- [ ] src düzeni, paketler, __init__.py ve relative importları ele al.
- [ ] External, ambiguous ve çözülemeyen importları ayrı tut.
- [ ] Dosya graph'ı, gelen/giden dependency sayıları ve cycle gruplarını üret.
- [ ] İzole dosya, self-loop, cycle ve çözümleme testlerini yaz.
- [ ] Doğrula ve commit at.

### 1.5 — Metrikler ve pipeline

- [ ] Toplam dosya/Python dosyası sayısı, fiziksel LOC ve Python LOC hesapla.
- [ ] En büyük dosyaları ve TODO/FIXME toplamlarını üret.
- [ ] Scanner, parser, graph ve metrik aşamalarını birleştir.
- [ ] Kısmi analiz tanılarını ve fatal hata davranışını uygula.
- [ ] Kontrollü fixture repository üzerinden beklenen sonuçları test et.
- [ ] Doğrula ve commit at.

### 1.6 — CLI çıktısı ve milestone kabulü

- [ ] Okunabilir terminal özeti ve --output JSON export ekle.
- [ ] Geçersiz path, yazılamayan output ve kısmi analiz için çıkış kodlarını belgele/test et.
- [ ] Tekrarlanan analizlerde kararlı ölçüm/sıralama doğrula.
- [ ] JSON çıktısının sonraki analizde girdi sayılmasını önleyecek davranışı belirle/test et.
- [ ] CLI integration testlerini tamamla; pytest çalıştır.
- [ ] README'ye gerçek çıktı örneği, sınırlamalar ve kullanım ekle.
- [ ] Doğrula ve milestone commit'i at.

Kabul komutları (henüz uygulanmadı):

```bash
python -m projectlens analyze /path/to/python/project
python -m projectlens analyze . --output analysis.json
projectlens analyze . --output analysis.json
```

Çıktı: dosya ağacı, Python dosyaları, LOC, importlar, dosya dependency graph'ı, cycle grupları, en büyük dosyalar ve TODO/FIXME sayıları. AI, DB, HTTP API ve frontend bu milestone'a dahil değil.

## 2 — Public GitHub repository ve persistence

- [ ] Clone/fetch için güvenli URL, timeout, disk limiti ve izolasyon kurallarını belirle.
- [ ] Branch ve commit kimliğiyle tekrarlanabilir checkout oluştur.
- [ ] Project ve AnalysisSnapshot modellerini ekle.
- [ ] SQLAlchemy/PostgreSQL persistence ve migration kur.
- [ ] FastAPI ile project oluşturma ve analiz sonuçlarını okuma uçlarını ekle.
- [ ] Uzun analiz işlerinin yaşam döngüsü/concurrency sınırlarını belirle; gerekirse worker ekle.
- [ ] Docker Compose ve backend CI kontrollerini ekle.
- [ ] Integration testleri ve setup belgelerini tamamla; adım adım commit at.

## 3 — Project tracking (backend)

- [ ] Manuel task CRUD, priority/category ve durum geçişleri ekle.
- [ ] TODO.md checklist import formatını ve tekrar import davranışını tanımla/test et.
- [ ] Roadmap ilerlemesini açık bir formülle hesapla; boş roadmap davranışını belirle.
- [ ] API, test ve belgeleri tamamla; adım adım commit at.

## 4 — Code-aware tracking (backend)

- [ ] Task'ları snapshot içindeki dosya/modüllerle ilişkilendir.
- [ ] Task kabul kriterleri ve kullanıcı tarafından tanımlanan kontrol kanıtlarını modelle.
- [ ] Manuel durumdan ayrı, gerekçeli ilerleme tahmini üret.
- [ ] Eksik/yetersiz kanıtta belirsizliği göster; dosya varlığını tamamlanma sayma.
- [ ] API, test ve belgeleri tamamla; adım adım commit at.

## 5 — Analiz çekirdeğini genişletme

- [ ] Dart/Flutter parser adaptörü, fixture'lar ve dil testlerini ekle.
- [ ] Framework tespiti ve test dosyası eşleşmesi ekle; coverage ile farkını belirt.
- [ ] Health skorlarını formül, gerekçe, sürüm ve eksik veri davranışıyla tanımla.
- [ ] Git history/churn ve açıklanabilir risk seviyelerini ekle.
- [ ] Büyük class/fonksiyon ve coupling bulgularını ekle.
- [ ] Complexity ve duplication analizini ihtiyaç olduğunda ayrı adımlarla değerlendir.
- [ ] Her özellik için doğrula, belgele ve commit at.

## 6 — İsteğe bağlı AI katmanı

- [ ] Structured context seçimi, boyut sınırları ve kaynak referanslarını tasarla.
- [ ] Repository/architecture/risk açıklamalarını ekle.
- [ ] Onboarding ve task önerilerini kullanıcı onayıyla uygulanacak öneriler olarak sun.
- [ ] Repository içeriğini güvenilmeyen veri olarak ele al; context'e tüm repository'yi gönderme.
- [ ] Sağlayıcı maliyeti, veri aktarımı ve hata davranışını belgele/test et.

## 7 — Frontend (en son)

- [ ] React + TypeScript + Vite uygulamasını kur.
- [ ] Uygun açık kaynak graph kütüphanesini değerlendir ve seç.
- [ ] Project listesi ve overview ekranını ekle.
- [ ] File tree, dependency graph ve node detaylarını ekle.
- [ ] Metrics, health, risks ve activity ekranlarını ekle.
- [ ] Roadmap ve code-aware tracking görünümünü ekle.
- [ ] AI insights görünümünü ilgili backend hazırsa ekle.
- [ ] Loading/error/empty durumları, erişilebilirlik ve frontend testlerini tamamla.
- [ ] Screenshot ve kullanıcı kurulum belgelerini ekle; adım adım commit at.

## Public release hazırlığı

- [ ] Lisansı seç ve LICENSE ekle.
- [ ] CONTRIBUTING.md, CODE_OF_CONDUCT.md ve güvenlik bildirim yönergesi ekle.
- [ ] README setup, Docker, architecture, roadmap ve katkı bağlantılarını güncelle.

## Daha sonraki backlog

- [ ] GitHub OAuth ve private repository desteği.
- [ ] GitHub Issues / Projects entegrasyonu.
- [ ] PR analizi ve regression risk raporu.
- [ ] Change impact analizi.
- [ ] Symbol/function/class search ve semantic search.
- [ ] Architecture rule validation ve technical debt tracking.
- [ ] Code ownership ve contributor analytics.
- [ ] Public proje sayfası, paylaşılabilir rapor ve README badge.
- [ ] PDF export ve otomatik documentation/diagram üretimi.
- [ ] CI üzerinde çalışan ProjectLens GitHub Action.
