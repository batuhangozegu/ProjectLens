# ProjectLens — mimari ve dosya yapısı

## Kapsam ve yaklaşım

Önce çalışan, test edilmiş bir local Python analiz motoru kurulacak. Bu ilk hazırlık adımında uygulama kodu yazılmayacak. Backend, takip sistemi ve AI katmanı çekirdeğin üzerine ayrı adımlarla eklenecek. Frontend en son yapılacak.

Başlangıç mimarisi modüler bir Python paketi olacak. Mikroservis, plugin registry, event bus veya worker altyapısı gerekmiyor. CLI ve ileride API, aynı analiz pipeline'ını çağıracak. Analiz çekirdeği FastAPI, SQLAlchemy veya herhangi bir AI sağlayıcısını import etmeyecek.

Proje adı **ProjectLens**, Python paketi ve komut adı **projectlens** olacak.

## Dosya yapısı

Şu anda yalnızca README, TODO, mimari belgesi, ignore kuralları ve boş kaynak/test dizinleri oluşturulur. Aşağıdaki Python dosyaları ve alt modüller, ilgili TODO adımında eklenecek tasarımdır; henüz uygulanmış değildir.

```text
ProjectLens/
├── README.md
├── TODO.md
├── .gitignore
├── docs/
│   └── ARCHITECTURE.md
└── backend/
    ├── pyproject.toml                 # Paketleme, pytest ve CLI ayarları
    ├── src/
    │   └── projectlens/
    │       ├── __init__.py
    │       ├── __main__.py            # python -m projectlens
    │       ├── cli.py                 # Argümanlar, özet, JSON export
    │       └── analysis/
    │           ├── models.py         # Çekirdeğin veri modelleri
    │           ├── pipeline.py       # Aşamaların orkestrasyonu
    │           ├── scanner.py        # Dosya keşfi, sınıflandırma, hariç tutma
    │           ├── languages/
    │           │   ├── base.py       # LanguageParser Protocol
    │           │   └── python.py     # Python AST adaptörü
    │           ├── dependency.py     # Import çözümleme, graph ve cycle analizi
    │           └── metrics.py        # LOC, büyük dosyalar, yorum işaretleri
    └── tests/
        ├── unit/
        ├── integration/
        └── fixtures/                 # Küçük, kontrollü örnek repository'ler
```

Başlangıçta tek dosyayla anlatılabilen bir modül için ayrıca klasör açılmayacak. İhtiyaç büyüdükçe dependency ve metrics modülleri bölünebilir.

İleride ihtiyaç oluştukça `projectlens/git/`, `projectlens/tracking/`, `projectlens/app/` ve en son kökte `frontend/` eklenecek. API katmanında route/schema, service ve persistence sorumlulukları ayrılacak; boş katmanlar şimdiden üretilmeyecek.

## Temel domain modelleri

İlk milestone'da veri taşıyan modeller için standart kütüphane `dataclass` yeterli. Dosya yolları sonuçlarda repository köküne göre ve `/` ayıracıyla saklanacak.

| Model | Temel alanlar ve amaç |
| --- | --- |
| AnalysisOptions | Kök yol, hariç tutma kuralları ve dosya boyutu sınırı |
| FileRecord | Göreli yol, dil, dosya sınıfı, fiziksel LOC ve analiz durumu |
| SymbolRecord | Dosya, isim, tür, başlangıç/bitiş satırı; fonksiyon ve class boyutları için temel |
| ImportRecord | Kaynak dosya, modül, import edilen isimler, relative import seviyesi, satır |
| ParsedFile | Semboller, importlar, yorum işaretleri ve parse tanıları |
| DependencyEdge | Kaynak/hedef yerel dosya ve ilişkiyi kanıtlayan import konumu |
| AnalysisDiagnostic | Aşama, dosya, hata türü ve açıklama |
| AnalysisResult | Şema sürümü, dosyalar, graph, cycle grupları, metrikler ve tanılar |

Sonraki milestone'larda eklenecek modeller: `Project`, commit/branch kimliğine bağlı `AnalysisSnapshot`, `Task`, `TaskFileLink`, `TaskEvidence`, `ScoreBreakdown` ve `RiskFinding`. ORM modelleri bu çekirdek modellerinden ayrı tutulacak.

Task durumları `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED` olacak. Backlog bir görünüm/filtre olarak ele alınabilir; şimdilik ek bir durum gerekmiyor. Manuel task durumu, analizden hesaplanan ilerleme tahmininden ayrı kalacak. Dosya bağlantısı veya dosyanın varlığı tek başına bir özelliğin tamamlandığını kanıtlamaz.

## Analysis pipeline

1. **Girdi doğrulama:** Var olan, okunabilir bir local dizin seçilir. İlk milestone Git repository olmayı şart koşmaz.
2. **Tarama ve sınıflandırma:** Dosya ağacı çıkarılır; Python, test, config ve documentation dosyaları belirlenir. Hariç bırakılanlar ve sınıflandırmanın sezgisel olduğu açıklanır.
3. **Parse:** Dil adaptörü kaynak metinden sembolleri ve importları çıkarır. Python için `ast` kullanılır.
4. **Import çözümleme:** Yerel modüller dosyalara eşlenir. External ve çözülemeyen importlar graph'a sahte dosyalar olarak eklenmez; ayrı raporlanır.
5. **Dependency graph:** Yerel Python dosyaları ve aralarındaki yönlü kenarlar oluşturulur. İzole Python dosyaları da node olarak korunur.
6. **Cycle analizi:** Strongly connected component'ler kullanılır. Birden fazla dosyalı bileşenler ve self-loop'lar cycle grubu sayılır; bütün basit cycle yolları enumerate edilmez.
7. **Metrikler:** LOC, en büyük dosyalar, dependency sayıları ve TODO/FIXME yorum işaretleri hesaplanır.
8. **Sonuç:** Tek bir yapılandırılmış sonuç, terminal özetine veya JSON'a dönüştürülür.

Pipeline modeller ve parser arayüzüne bağımlı olacak; CLI yalnızca giriş/çıkışı yönetecek. İlk sürüm sıralı ve senkron çalışacak. Hatalı bir dosya mümkünse diğerlerinin analizini engellemeyecek; kısmi sonuç açık tanılarla işaretlenecek. Geçersiz kök dizin gibi hatalar komutu başarısız bitirecek.

## Kritik teknik kararlar

- **Python AST önce:** Python için yeterli ve standart kütüphanede mevcut. Tree-sitter başlangıç bağımlılığı olmayacak; Dart adaptörü eklenirken değerlendirilecek. Parser arayüzü `supports(path)` ve `parse(path, source)` benzeri küçük bir Protocol olacak.
- **Graph dosya seviyesinde:** MVP 1 kenarları import bağımlılığını temsil eder. Bunlardan class çağrı akışı veya runtime bağımlılığı çıkarıldığı iddia edilmeyecek. NetworkX graph ve bileşen analizi için kullanılacak.
- **Import çözümleme sınırları:** Paketler, relative import, `src/` düzeni ve `__init__.py` testlerle ele alınacak. Dinamik importlar, namespace paketleri ve belirsiz isimler için çözülemeyen/ambiguous tanıları üretilecek. Kullanıcı repository'si import edilmeyecek veya çalıştırılmayacak.
- **Tarama sınırları:** `.git`, sanal ortamlar, cache ve build dizinleri varsayılan olarak hariç tutulacak. Symlink dizinler takip edilmeyecek. Okuma ve parse sorunları görünür olacak. `.gitignore` uyumluluğu açık bir kapsam kararı olarak ayrıca değerlendirilecek.
- **Metrik tanımları:** LOC ilk sürümde boş ve yorum satırları dahil fiziksel satır sayısıdır; Python LOC ayrıca gösterilir. TODO/FIXME sayımı yorum token'ları üzerinden yapılır; string içerikleri sayılmaz. Büyük dosyalar risk veya hotspot skoru olarak sunulmaz.
- **Deterministik sonuç:** Sıralama, path normalizasyonu ve cycle gösterimi kararlı olacak. JSON şema sürümü taşıyacak. Zaman damgaları gibi çalışmaya özgü metadata, ölçümlerin tekrar üretilebilirliğinden ayrı değerlendirilecek.
- **Test kapsamı dürüstlüğü:** Test dosyası eşleşmesi coverage değildir. Health/risk skorları ilk milestone kapsamı dışındadır; eklendiklerinde formülleri, eksik verileri ve gerekçeleri görünür olacak.
- **Persistence sonra:** FastAPI, Pydantic, SQLAlchemy ve PostgreSQL public repository milestone'unda eklenecek. API şemaları ve ORM çekirdeğe sızmayacak.
- **Güvenilmeyen kod:** Repository kodu çalıştırılmayacak. İleride clone işleminde URL doğrulama, timeout, disk limitleri ve checkout izolasyonu ayrı bir adım olacak.
- **Frontend son aşama:** React + TypeScript + Vite başlangıç tercihi. Graph kütüphanesi frontend milestone'unda lisans, ölçek ve etkileşim ihtiyaçlarına göre seçilecek.

## Milestone sırası

1. Local Python analiz çekirdeği + CLI + JSON + pytest.
2. Public GitHub repository clone/fetch + project + analiz snapshot persistence + API.
3. Project tracking + manuel task + TODO.md import; önce backend/API.
4. Code-aware tracking + dosya/modül bağlantıları + açıklanabilir evidence ve ilerleme tahmini.
5. Çekirdek genişletmeleri: Dart/Flutter, açıklanabilir health/risk, test eşleşmeleri ve Git geçmişi. Her biri ayrı küçük adım.
6. İsteğe bağlı AI katmanı: structured context üzerinden açıklamalar.
7. Frontend: project listesi, detaylar, roadmap, graph ve diğer tamamlanmış backend özellikleri.

Change impact, PR analizi, OAuth/private repositories ve semantic search sonraki backlog'da kalır. Her adım bir öncekinin çalışan sonucunu kullanır; tüm roadmap tek seferde uygulanmaz.
