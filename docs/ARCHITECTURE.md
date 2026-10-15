# ProjectLens — mimari ve dosya yapısı

## Kapsam ve yaklaşım

Önce çalışan, test edilmiş bir local Python analiz motoru kurulacak. 1.1 adımında çalıştırılabilir paket, CLI temeli, veri modelleri ve parser arayüzü oluşturulur; tarama ve analiz henüz uygulanmamıştır. Backend, takip sistemi ve AI katmanı çekirdeğin üzerine ayrı adımlarla eklenecek. Frontend en son yapılacak.

Başlangıç mimarisi modüler bir Python paketi olacak. Mikroservis, plugin registry, event bus veya worker altyapısı gerekmiyor. CLI ve ileride API, aynı analiz pipeline'ını çağıracak. Analiz çekirdeği FastAPI, SQLAlchemy veya herhangi bir AI sağlayıcısını import etmeyecek.

Proje adı **ProjectLens**, Python paketi ve komut adı **projectlens** olacak.

## Dosya yapısı

Paketleme ayarları, CLI temeli, analiz veri modelleri ve parser Protocol'ü aşağıdaki yapıda oluşturulmuştur. Tarayıcı, somut dil parser'ı, pipeline, graph ve metrik modülleri ilgili sonraki TODO adımlarında eklenecektir.

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

### Scanner v1 scope

The scanner does not read or interpret `.gitignore` in v1. It uses its built-in exclusions and any additional `AnalysisOptions.exclude_patterns`; excluded paths are reported as scan diagnostics. A later step may add `.gitignore` support. Symlink directories are not followed and symlink files are not read. Oversized and unreadable files remain listed without LOC and carry diagnostics. File classification is heuristic. File contents are read as bytes only for physical LOC counting; scanned code is never imported or executed.

### Python parser v1 scope

The Python parser uses only `ast` and `tokenize`; it never imports or executes repository code. Function, async function, class, and method symbols use dot-separated lexical qualified names, including nested definitions (for example `Outer.method.inner`). A function directly in a class body has kind `method`; functions nested inside functions have kind `function`. Symbol start lines include the earliest decorator line; end lines use the AST node's `end_lineno`. Import aliases are preserved in `ImportRecord.imported_names` as `name as alias`; each imported name is retained in source order. Relative levels and statement lines are recorded, including imports nested in blocks. No imports are resolved here.

Only uppercase whole-word `TODO` and `FIXME` occurrences in comment tokens count. Marker strings use `KIND:line`, are ordered by line then source occurrence, and ignore string/docstring contents. If tokenization fails, comments yielded before the failure are kept and a `TokenizeError` diagnostic is added. Syntax, null-byte, resource-limit, and byte-decoding failures are represented as parse diagnostics; `decode_source` follows Python encoding cookies and UTF-8 BOM detection. Symbols and imports are sorted deterministically by source position and stable field values.

### Dependency graph v1 decisions

Yerel modül indeksi `.py` dosyalarından kurulur; `.pyi` dosyaları modül kaynağı değildir. Repository kökü ve varsa en üstteki `src/` dizini source root sayılır. İsim çakışması olan modüller seçilmez, ambiguous olarak raporlanır. Namespace package dizinleri (`__init__.py` olmayan dizinler) indekslenmiş paket sayılmaz; bunlardan geçen yerel çözümlemeler unresolved/`NamespacePackage` tanısı alır. Dinamik importlar bu adımda kapsanmaz.

Kenar yalnızca en özgül yerel modül dosyasına gider; ara paketlerin `__init__.py` dosyalarına örtük kenar eklenmez. `from package import name`, önce `package.name` alt modülünü, yoksa package initializer'ını hedefler; star import package/modül hedefinde kalır. Yerel üst seviye isim aynı isimli external modüle üstün gelir. External stdlib/third-party etiketi analiz eden Python yorumlayıcısının `sys.stdlib_module_names` sürümüne bağlıdır. Kenar kanıtı sıralı import satırlarıdır; aynı dosya çifti için tek kenar üretilir. Gelen/giden sayılar distinct komşu dosyaları sayar. Cycle'lar strongly connected component'lerden çıkarılır; basit yollar enumerate edilmez.

Bilinen sınır: `ImportRecord` şu an `import x` ile `from y import z` ifadelerini ayrı işaretlemez; çözümleyici, tüm imported isimleri modül adına eşit olan absolute kaydı düz `import` sayar. Bu yüzden `from config import config` gibi, paket ile aynı adlı alt modülü olan nadir durumlarda edge alt modül yerine paketin `__init__.py` dosyasına gidebilir. Gerekirse parser kaydına `is_from` alanı eklenerek giderilir.

### CLI contract (milestone 1)

`python -m projectlens analyze PATH` and the installed `projectlens analyze PATH` command call the same synchronous pipeline. The CLI prints an ASCII-safe plain-text summary to stdout: root, file and Python file counts, physical and Python LOC, largest files, TODO/FIXME totals, dependency counts, cycle members, and diagnostics. The summary marks partial results explicitly. `--top N` controls largest files and `--max-diagnostics N` limits diagnostics shown in the terminal summary.

`--output FILE` writes `AnalysisResult.to_json()` as UTF-8 with a trailing newline. It writes through a temporary file in the destination directory and replaces the destination only after the complete write. A fatal failure leaves no newly truncated destination file; temporary files are cleaned up when possible. The summary is printed after a successful export. The serialized result omits the root path and contains repository-relative paths only, so copies of the same tree serialize identically. No timestamps or temporary paths are serialized.

Exit codes are stable: **0** means the pipeline result is complete; **1** means fatal root validation/readability or output-path/write failure, with a concise stderr message and no traceback; **2** is argparse's usage error; **3** means a result exists and was exported if requested, but `AnalysisResult.partial` is true. Partial is exactly the pipeline flag: unreadable or oversized files, parse failures/parser diagnostics, and unreadable scan entries make it true; expected exclusions and skipped symlinks do not.

To prevent recursive report input, the exact `--output` path is excluded from scanning and gets a stable `Excluded` diagnostic whenever it lies under the root. Thus a first and repeated in-tree export have the same serialized analysis. Every JSON file within the configured scan size limit is also parsed as JSON and checked for the top-level `projectlens_format: projectlens-analysis` marker; marked results are skipped with an `Excluded` diagnostic. Oversized JSON files already follow the scanner's normal size-limit behavior. The marker is part of the deterministic result format and is not a timestamp or root identifier.

The selected root is intentionally not serialized. This makes the result portable and byte-identical across copies, at the cost of requiring the CLI invocation or surrounding context to identify which checkout was analyzed.

### Metrics and pipeline v1

The pipeline is a synchronous library function and does not depend on the CLI, HTTP, a database, or an AI provider. It selects a parser from a small in-process list by `supports(path)`. Repository files are read as bytes and decoded with the Python parser's encoding-cookie/BOM helper; repository code is never imported or executed. Root validation errors propagate as `ScanError`. Other scan, read, decode, parser, and dependency diagnostics are returned with the result in stable `(stage, path, error type, message)` order.

`AnalysisResult.partial` is true if a scanned file is unreadable, exceeds the scan size limit, cannot be parsed, or has a parser diagnostic, or if scanning encountered an unreadable directory/entry. Expected excluded-path and symlink-skipped diagnostics do not by themselves make a result partial. File records are retained for all discovered files, including unreadable, oversized, and parse-failed files. Their `analysis_status` records the outcome (`scanned`, `analyzed`, `analyzed_with_diagnostics`, `parse_failed`, `unreadable`, or `skipped_size_limit`).

`total_file_count` and `python_file_count` include every discovered record, even if its content could not be read or parsed. Physical LOC is the scanner's count of physical lines, including blank and comment lines, summed over files with a known count. Python LOC uses the same definition for scanner-classified Python files. Both LOC metrics report known and unavailable file counts and paths; unavailable LOC is not silently treated as measured zero. Largest files are ordered by descending known physical LOC and then ascending repository-relative path, with a configurable default limit of 10; these are size facts, not risk scores.

TODO/FIXME totals count parser-produced uppercase whole-word markers in comment tokens only. String contents do not count. Per-file counts include each Python file; `available` is false and the path is listed under `unavailable_files` if reading/decoding/tokenization did not provide complete marker data. Totals are known occurrences, so they can be lower bounds when unavailable files exist. Dependency summary counts local graph edges, external import references, unresolved import references, and cycle groups. External and unresolved references are also retained in the serialized result. Result schema version 3 adds those reference collections and the explicit `partial` flag.

### Safe public GitHub checkout (milestone 2.1)

The Git boundary accepts only ASCII `https://github.com/<owner>/<repo>` URLs with optional `.git` and trailing slash; it rejects credentials, ports, query/fragment, other hosts, extra path components, and invalid names. `projectlens.git.checkout_repository` creates a depth-one isolated checkout with a timeout and a maximum checkout size measured before Git metadata is removed. Git runs as an argument list without a shell, with prompts and inherited Git configuration/credential helpers disabled, hooks and fsmonitor disabled, symlink materialization disabled, submodule recursion disabled, and LFS smudging neutralized. The protocol allowlist permits HTTPS only for application calls. Requested commits must be full 40-character SHAs (a shallow fetch by abbreviated SHA is not possible); they are fetched shallowly by SHA and the resulting SHA is checked against the request. On Windows, read-only Git object files are cleared before removal.

The checkout's `.git` directory is removed before it is returned to analysis; the analyzer receives only the working tree. The result owns a temporary directory and must be closed with its context manager or `cleanup()`. `_clone_url_override` and `_runner` are private test seams for local repositories and simulated failures; they are not exposed by the public URL validator and are not for application callers. Repository contents remain untrusted data and are never executed by ProjectLens.
