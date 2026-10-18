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

### 1.4 — Dependency graph

- [x] Yerel modül indeksini ve import çözümlemesini oluştur.
- [x] src düzeni, paketler, __init__.py ve relative importları ele al.
- [x] External, ambiguous ve çözülemeyen importları ayrı tut.
- [x] Dosya graph'ı, gelen/giden dependency sayıları ve cycle gruplarını üret.
- [x] İzole dosya, self-loop, cycle ve çözümleme testlerini yaz.
- [x] Doğrula ve commit at.

### 1.5 — Metrikler ve pipeline

- [x] Toplam dosya/Python dosyası sayısı, fiziksel LOC ve Python LOC hesapla.
- [x] En büyük dosyaları ve TODO/FIXME toplamlarını üret.
- [x] Scanner, parser, graph ve metrik aşamalarını birleştir.
- [x] Kısmi analiz tanılarını ve fatal hata davranışını uygula.
- [x] Kontrollü fixture repository üzerinden beklenen sonuçları test et.
- [x] Doğrula ve commit at.

### 1.6 — CLI çıktısı ve milestone kabulü

- [x] Okunabilir terminal özeti ve --output JSON export ekle.
- [x] Geçersiz path, yazılamayan output ve kısmi analiz için çıkış kodlarını belgele/test et.
- [x] Tekrarlanan analizlerde kararlı ölçüm/sıralama doğrula.
- [x] JSON çıktısının sonraki analizde girdi sayılmasını önleyecek davranışı belirle/test et.
- [x] CLI integration testlerini tamamla; pytest çalıştır.
- [x] README'ye gerçek çıktı örneği, sınırlamalar ve kullanım ekle.
- [x] Doğrula ve milestone commit'i at.

Kabul komutları:

```bash
python -m projectlens analyze /path/to/python/project
python -m projectlens analyze . --output analysis.json
projectlens analyze . --output analysis.json
```

Çıktı: dosya ağacı, Python dosyaları, LOC, importlar, dosya dependency graph'ı, cycle grupları, en büyük dosyalar ve TODO/FIXME sayıları. AI, DB, HTTP API ve frontend bu milestone'a dahil değil.

## 2 — Public GitHub repository ve persistence

Kararlar: PostgreSQL 18 yerelde kurulu; bağlantı bilgisi `DATABASE_URL` ile ortam değişkeninden gelir, gerçek `.env` commit edilmez. Persistence testleri SQLite ile çalışır; PostgreSQL ile doğrulama ayrı bir adımdır. Docker sonradan kuruldu ve Compose doğrulandı; GitHub Actions iş akışı henüz çalıştırılmadı. Analiz çekirdeği FastAPI/SQLAlchemy import etmez.

### 2.1 — Güvenli clone/checkout

- [x] Yalnızca public https GitHub URL'lerini kabul eden doğrulayıcı yaz (ssh, file, yerel yol, credential içeren URL, başka host reddedilir).
- [x] Git alt sürecini shell kullanmadan, timeout ve çıktı/disk limitiyle çalıştır; hook, submodule ve git config etkilerini kapat.
- [x] Branch ve commit kimliğiyle tekrarlanabilir checkout oluştur; checkout dizinini izole ve temizlenebilir tut.
- [x] Yerel git repository'leriyle (ağ gerektirmeyen) testler yaz; doğrula ve commit at.

### 2.2 — Project ve AnalysisSnapshot persistence

- [x] Project ve AnalysisSnapshot modellerini (commit/branch kimliğine bağlı) tanımla; ORM modelleri çekirdek modellerden ayrı kalır.
- [x] SQLAlchemy 2.x + Alembic migration kur; `DATABASE_URL` yapılandırması ekle.
- [x] Repository katmanı: snapshot'ı AnalysisResult JSON'u olarak sakla ve oku.
- [x] SQLite ile testler; doğrula ve commit at.

### 2.3 — FastAPI uçları

- [x] Project oluşturma (URL doğrulama + clone + analiz + snapshot) ve listeleme/okuma uçlarını ekle.
- [x] Uzun analiz işlerinin yaşam döngüsü ve concurrency sınırını belirle; gerekirse worker ekle.
- [x] Hata zarfı, girdi doğrulama ve API testleri; doğrula ve commit at.

### 2.4 — PostgreSQL doğrulaması, Docker Compose ve CI

- [x] Yerel PostgreSQL ile migration ve testleri doğrula.
- [x] Dockerfile ve Docker Compose ekle (build ve up Docker 29.8 ile doğrulandı — bkz. aşağıdaki not).
- [x] Backend CI iş akışını ekle.
- [x] Setup belgelerini ve README'yi güncelle; doğrula ve commit at.


Not: PostgreSQL 18 üzerinde migration, gerçek uçtan uca API akışı ve tüm testler (140) doğrulandı. `docker compose up --build` doğrulandı (migration, healthcheck, non-root, read-only FS, konteynerde gerçek analiz). GitHub Actions çalıştırılmadı; YAML sözdizimi ayrıştırıldı.

## 3 — Project tracking (backend)

Kararlar: Task durumları `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`. Manuel durum, analizden hesaplanan ilerleme tahmininden ayrı kalır (bu milestone yalnızca manuel durumu kapsar). Saf mantık (TODO.md ayrıştırma, ilerleme formülü) `projectlens/tracking/` altında, FastAPI/SQLAlchemy import etmeden yazılır; DB ve API katmanı `projectlens/app/` altında kalır.

### 3.1 — Task modeli, durum geçişleri ve CRUD API

- [x] Task ORM modeli ve migration (proje bağlı; başlık, açıklama, durum, priority, category, sıra, kaynak/source_key, zaman damgaları).
- [x] Geçerli durum geçişleri tablosu ve geçersiz geçişte net hata.
- [x] Repository ve `/api/v1/projects/{id}/tasks` CRUD uçları (liste filtreleri: durum, priority, category; sayfalama).
- [x] SQLite + PostgreSQL testleri; doğrula ve commit at.

### 3.2 — TODO.md checklist ayrıştırıcısı (saf mantık)

- [x] Markdown başlıklarını ve `- [x]` / `- [x]` maddelerini ayrıştır (CRLF, iç içe liste, kod blokları, başlık sonu notları).
- [x] Her madde için kararlı `source_key` üret (bölüm yolu + normalize başlık + tekrar sırası); aynı dosya ikinci kez ayrıştırıldığında aynı anahtarlar çıkmalı.
- [x] Gerçek `TODO.md` ve sentetik edge-case testleri; doğrula ve commit at.

### 3.3 — Roadmap ilerleme formülü (saf mantık)

- [x] Formülü tanımla ve belgele: yalnızca DONE tamamlanmış sayılır, IN_PROGRESS kısmi puan almaz, BLOCKED paydada kalır.
- [x] Boş roadmap davranışı: yüzde yerine açık "boş" durumu (0% değil).
- [x] Toplam, bölüm ve kategori bazında dağılım ve yüzde; test et, doğrula ve commit at.

### 3.4 — Import ve ilerleme uçları

- [x] TODO.md import ucu: tekrar import kararlı (anahtar eşleşmesi, çoğalma yok, manuel değişiklikleri ezme kuralı belgeli).
- [x] Proje roadmap ilerleme ucu (3.3 formülü).
- [x] API testleri ve belgeler; doğrula ve commit at.

## 4 — Code-aware tracking (backend)

Tasarım `docs/ARCHITECTURE.md` içindeki "Code-aware tracking tasarımı" bölümündedir. Özet: task'lar yola bağlı dosya/dizin bağlantıları (snapshot'tan bağımsız) ve kabul kriterleri taşır; kriterler yalnızca saklanan AnalysisResult JSON'undan değerlendirilir; ilerleme tahmini manuel durumdan ayrıdır, gerekçe ve belirsizlik içerir; bağlı dosyanın varlığı tek başına tamamlanma kanıtı sayılmaz. Değerlendirme saf mantıktır (`projectlens/tracking/`), DB/API `projectlens/app/` altındadır.

### 4.1 — Kanıt değerlendirme motoru (saf mantık)

- [x] Kriter türlerini ve snapshot JSON'undan değerlendirmeyi uygula (met / unmet / unknown).
- [x] Gerekçeli, belirsizliği gösteren ilerleme tahmin formülünü uygula; bağlantı varlığı ağırlıksızdır.
- [x] Manuel durumla sapma (divergence) göstergesi; eksik/yetersiz kanıtta null tahmin.
- [x] Kapsamlı testler; doğrula ve commit at.

### 4.2 — Bağlantı ve kriter persistence + CRUD API

- [x] TaskFileLink ve AcceptanceCriterion modelleri, migration 0004, repository.
- [x] `/projects/{id}/tasks/{task_id}/links` ve `/criteria` CRUD uçları (yol doğrulama, sınırlar).
- [x] SQLite + PostgreSQL testleri; doğrula ve commit at.

### 4.3 — Değerlendirme uçları

- [x] `GET /projects/{id}/tasks/{task_id}/assessment?snapshot=latest|<id>` (4.1 motoru + 4.2 verisi).
- [x] `GET /projects/{id}/roadmap/assessment` proje özeti (belirsizlik ve sapma sayıları dahil).
- [x] API testleri, belgeler; doğrula ve commit at.

## 5 — Analiz çekirdeğini genişletme

Her alt adım bağımsız commit'tir. Parser'lar kaynağı asla çalıştırmaz/import etmez; ağır parser bağımlılığı (tree-sitter vb.) eklenmeden önce gerekçe belgelenir.

### 5.1 — Dart/Flutter parser adaptörü

- [x] `.dart` için `LanguageParser` adaptörü: semboller, import/export/part direktifleri ve yalnızca yorumlardan TODO/FIXME.
- [x] Scanner sınıflandırması: Dart kaynak/test ve pubspec/analysis_options config; üretilmiş `*.g.dart` dosyaları dışlanmaz.
- [x] Pipeline'a Dart parser'ı bağla; fixture Dart repository'si ve dil testleri; bozuk/encoding hatalı dosya tanıları.
- [x] Doğrula, belgele ve commit at.

### 5.2 — Dart bağımlılık çözümleme

- [x] `package:<pubspec adı>/...` ve göreli import/export/part yollarını yerel dosyalara çöz; `dart:` ve dış paketler external, çözülemeyenler unresolved.
- [x] Python graph'ı ile aynı sonuç sözleşmesine (edge, cycle, sayaçlar) birleştir; karışık dilli repository testi.
- [x] Metrikler Dart dosyalarını da saymalı; doğrula, belgele ve commit at.

### 5.3 — Framework tespiti ve test eşleşmesi

- [x] Manifest tabanlı framework tespiti (pubspec/pyproject/requirements: Flutter, FastAPI, Django, Flask vb.), kanıt dosyasıyla birlikte.
- [x] Kaynak↔test dosyası ad/dizin eşleşmesi; sonuç açıkça "eşleşme"dir, coverage değildir ve belgede/çıktıda böyle etiketlenir.
- [x] Doğrula, belgele ve commit at.

### 5.4 — Health skorları

- [x] Formül, gerekçe listesi, formül sürümü ve eksik veri davranışı (hesaplanamayan bileşen skoru uydurmaz) ile tanımla ve uygula.
- [x] Doğrula, belgele ve commit at.

### 5.5 — Git history/churn ve risk

- [x] Güvenli (shell'siz, sınırlı) git log okuyucusu ile dosya bazlı churn; açıklanabilir risk seviyeleri.
- [x] Doğrula, belgele ve commit at.

### 5.6 — Büyük class/fonksiyon ve coupling bulguları

- [x] Büyük sembol ve yüksek fan-in/fan-out bulguları, eşikler ve gerekçeleriyle.
- [x] Doğrula, belgele ve commit at.

### 5.7 — Complexity ve duplication değerlendirmesi

- [ ] İhtiyaç ve maliyeti değerlendir; gerekiyorsa ayrı küçük adımlara böl, gerekmiyorsa kararı belgele.

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
