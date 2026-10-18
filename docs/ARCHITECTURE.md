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
    │           │   ├── python.py     # Python AST adaptörü
    │           │   └── dart.py       # Dart lexer/parser adaptörü
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
3. **Parse:** Dil adaptörü kaynak metinden sembolleri ve importları çıkarır. Python için `ast`, Dart için standart kütüphane tabanlı lexer kullanılır.
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
- **Persistence 2.2:** SQLAlchemy 2.x lives only in the optional `projectlens.app.db` package; install it with `pip install -e "backend[dev,app]"`. `DATABASE_URL` is read only from the process environment. Tests use SQLite. ORM models are separate from `AnalysisResult`; integer primary keys keep SQLite/PostgreSQL behavior portable, and timestamps are normalized to UTC (SQLite reads are restored as timezone-aware values). A snapshot is unique by `(project_id, commit_sha, analyzer_schema_version)`: duplicates are rejected with `DuplicateSnapshotError`, never silently overwritten. Alembic owns schema changes and uses the same metadata naming convention as the ORM.
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

### Dart parser v1 scope

The Dart adapter uses a small hand-written lexer with no additional dependencies. It skips line comments, nested block comments, raw and ordinary single/double/triple quoted strings, and interpolation expressions, so declarations and markers inside them are ignored. It extracts class, mixin, enum, named/unnamed extension, typedef, top-level function/accessor, and class-like member declarations; method names are qualified as `Type.member`. Brace matching provides inclusive source ranges. Constructors may be recorded as methods when they have bodies; declaration-only constructors are omitted. An unnamed extension is represented as `<unnamed>`.

Import, export, `part`, and URI-form `part of` directives are stored in ImportRecord; that model does not preserve directive kind. The URI is the primary URI as written (conditional alternatives are ignored), `show` names are sorted, and `as`/`hide` clauses are not represented. TODO/FIXME markers use the Python parser's `KIND:line` convention and come only from comments. Unterminated strings/comments produce file-local SyntaxError diagnostics while retaining preceding declarations and comments.

This is a declaration-oriented lexer, not a complete Dart grammar: it does not perform type resolution, merge part files, or model all modern language constructs. Generated `.g.dart`, `.freezed.dart`, and `.gr.dart` files remain included. `.dart_tool` is excluded by the scanner. Dart files contribute to total file/physical LOC and comment marker metrics; Python-specific counts remain Python-only.

### Dart dependency resolution v1

The pipeline reads scanned `pubspec.yaml` files within the configured file size limit and extracts only a top-level `name:` line using a tolerant line reader; it does not load or execute YAML. Each pubspec directory is a package root, and a Dart file belongs to its nearest enclosing root. `package:<name>/<path>` resolves to that package's `lib/<path>` when the name is local and unique; local targets must exist among scanned Dart files. Duplicate local package names are unresolved as ambiguous. Unknown package names and `dart:` URIs are external references. Relative URIs resolve from the importing file, and paths escaping the repository are unresolved with a diagnostic. Other URI schemes are unresolved as unsupported; nothing is fetched.

The parser does not retain whether a URI came from `import`, `export`, `part`, or URI-form `part of`, so all recorded directives count uniformly as dependencies. Conditional-import alternatives are not retained. Pub workspaces and `dependency_overrides` are not interpreted, and path/git dependencies are not resolved; `package:` imports for packages not declared by a local pubspec remain external. Edges are merged by source/target with sorted evidence lines, distinct-neighbor counts, and strongly connected component cycle groups. Python and Dart graphs are merged into the same result; Python-only results retain their previous graph behavior.

### Dependency graph v1 decisions

Yerel modül indeksi `.py` dosyalarından kurulur; `.pyi` dosyaları modül kaynağı değildir. Repository kökü ve varsa en üstteki `src/` dizini source root sayılır. İsim çakışması olan modüller seçilmez, ambiguous olarak raporlanır. Namespace package dizinleri (`__init__.py` olmayan dizinler) indekslenmiş paket sayılmaz; bunlardan geçen yerel çözümlemeler unresolved/`NamespacePackage` tanısı alır. Dinamik importlar bu adımda kapsanmaz.

Kenar yalnızca en özgül yerel modül dosyasına gider; ara paketlerin `__init__.py` dosyalarına örtük kenar eklenmez. `from package import name`, önce `package.name` alt modülünü, yoksa package initializer'ını hedefler; star import package/modül hedefinde kalır. Yerel üst seviye isim aynı isimli external modüle üstün gelir. External stdlib/third-party etiketi analiz eden Python yorumlayıcısının `sys.stdlib_module_names` sürümüne bağlıdır. Kenar kanıtı sıralı import satırlarıdır; aynı dosya çifti için tek kenar üretilir. Gelen/giden sayılar distinct komşu dosyaları sayar. Cycle'lar strongly connected component'lerden çıkarılır; basit yollar enumerate edilmez.

Bilinen sınır: `ImportRecord` şu an `import x` ile `from y import z` ifadelerini ayrı işaretlemez; çözümleyici, tüm imported isimleri modül adına eşit olan absolute kaydı düz `import` sayar. Bu yüzden `from config import config` gibi, paket ile aynı adlı alt modülü olan nadir durumlarda edge alt modül yerine paketin `__init__.py` dosyasına gidebilir. Gerekirse parser kaydına `is_from` alanı eklenerek giderilir.

### CLI contract (milestone 1)

`python -m projectlens analyze PATH` and the installed `projectlens analyze PATH` command call the same synchronous pipeline. The CLI prints an ASCII-safe plain-text summary to stdout: root, file and Python file counts, physical and Python LOC, largest files, TODO/FIXME totals, dependency counts, cycle members, and diagnostics. The summary marks partial results explicitly. `--top N` controls largest files and `--max-diagnostics N` limits diagnostics shown in the terminal summary.

`--output FILE` writes `AnalysisResult.to_json()` as UTF-8 with a trailing newline. It writes through a temporary file in the destination directory and replaces the destination only after the complete write. A fatal failure leaves no newly truncated destination file; temporary files are cleaned up when possible. The summary is printed after a successful export. The serialized result omits the root path and contains repository-relative paths only, so copies of the same tree serialize identically. No timestamps or temporary paths are serialized.

Exit codes are stable: **0** means the pipeline result is complete; **1** means fatal root validation/readability or output-path/write failure, with a concise stderr message and no traceback; **2** is argparse's usage error; **3** means a result exists and was exported if requested, but `AnalysisResult.partial` is true. Partial is exactly the pipeline flag: unreadable or oversized files, parse failures/parser diagnostics, and unreadable scan entries make it true; expected exclusions and skipped symlinks do not.

The terminal summary always includes risk counts and up to three top-risk files with their factor IDs. A Git history line appears only when `--git-history` was supplied.

To prevent recursive report input, the exact `--output` path is excluded from scanning and gets a stable `Excluded` diagnostic whenever it lies under the root. Thus a first and repeated in-tree export have the same serialized analysis. Every JSON file within the configured scan size limit is also parsed as JSON and checked for the top-level `projectlens_format: projectlens-analysis` marker; marked results are skipped with an `Excluded` diagnostic. Oversized JSON files already follow the scanner's normal size-limit behavior. The marker is part of the deterministic result format and is not a timestamp or root identifier.

The selected root is intentionally not serialized. This makes the result portable and byte-identical across copies, at the cost of requiring the CLI invocation or surrounding context to identify which checkout was analyzed.

### Metrics and pipeline v1

The pipeline is a synchronous library function and does not depend on the CLI, HTTP, a database, or an AI provider. It selects a parser from a small in-process list by `supports(path)`. Repository files are read as bytes and decoded with the Python parser's encoding-cookie/BOM helper; repository code is never imported or executed. Root validation errors propagate as `ScanError`. Other scan, read, decode, parser, and dependency diagnostics are returned with the result in stable `(stage, path, error type, message)` order.

`AnalysisResult.partial` is true if a scanned file is unreadable, exceeds the scan size limit, cannot be parsed, or has a parser diagnostic, or if scanning encountered an unreadable directory/entry. Expected excluded-path and symlink-skipped diagnostics do not by themselves make a result partial. File records are retained for all discovered files, including unreadable, oversized, and parse-failed files. Their `analysis_status` records the outcome (`scanned`, `analyzed`, `analyzed_with_diagnostics`, `parse_failed`, `unreadable`, or `skipped_size_limit`).

`total_file_count` and `python_file_count` include every discovered record, even if its content could not be read or parsed. Physical LOC is the scanner's count of physical lines, including blank and comment lines, summed over files with a known count. Python LOC uses the same definition for scanner-classified Python files. Both LOC metrics report known and unavailable file counts and paths; unavailable LOC is not silently treated as measured zero. Largest files are ordered by descending known physical LOC and then ascending repository-relative path, with a configurable default limit of 10; these are size facts, not risk scores.

TODO/FIXME totals count parser-produced uppercase whole-word markers in comment tokens only. String contents do not count. Per-file counts include parsed Python and Dart files; `available` is false and the path is listed under `unavailable_files` if reading/decoding/parsing did not provide complete marker data. Totals are known occurrences, so they can be lower bounds when unavailable files exist. Dependency summary counts local graph edges, external import references, unresolved import references, and cycle groups. External and unresolved references are also retained in the serialized result. Result schema version 4 adds `frameworks` and `test_matches` alongside the reference collections and explicit `partial` flag.

### Framework detection and source/test matches (5.3)

Result schema version 4 adds `frameworks` and `test_matches` to the existing reference collections and explicit `partial` flag. `AnalysisResult.from_dict()` remains compatible with version 3 results: absent new fields default to empty collections and the original schema version is retained. API snapshot code stores and returns the result object unchanged.

`frameworks` is a sorted list of manifest declarations with `name`, `ecosystem`, `evidence_file`, bounded `evidence`, and `kind: "manifest"`. Detection is declaration-only: it reports known Python dependencies (FastAPI, Django, Flask, Starlette, pytest, SQLAlchemy, Pydantic) from pyproject, requirements, and setup.cfg; and Flutter, flutter_test, Riverpod, Bloc, Provider, and Get libraries from pubspec. It does not inspect code usage. The standard-library scanners tolerate common TOML/YAML forms and intentionally do not implement either full grammar; no repository code or package manager is executed. Each monorepo manifest is reported on its own. Manifest read/decode/size failures become diagnostics and make the result partial.

`test_matches` has one record per non-generated Python or Dart source file, with matching test paths and the rule (`import` or `name`). Resolved dependency edges from test files to sources win over name matches. Python names support `test_x.py`, `x_test.py`, and `tests/` mirrors; Dart supports matching paths under `lib/` and `test/`, then same-package basename matches. Initializers, `conftest.py`, generated `.g.dart`/`.freezed.dart`, and files classified as tests are not source candidates. `metrics.test_matching` reports source totals and counts by rule; its basis is `name/import heuristics; not coverage`. These are file associations only and make no coverage claim.

The CLI labels declarations as frameworks and describes test associations as matches. Neither terminal nor JSON output calls them coverage.

### Heuristic health indicator

Analysis stores `metrics.health` (formula version `1`), computed after test matching from existing static analysis facts. It is a heuristic indicator, not a quality guarantee, correctness measure, or coverage measure. Components are independently explained with a 0–100 score, weight, value, availability, and a reason sentence:

| Component | Weight | Formula |
| --- | ---: | --- |
| Cycles | 0.30 | `100 * (1 - min(1, 4 * files_in_cycles / files_in_graph))`; saturates at 25%. |
| Unresolved imports | 0.20 | `100 * (1 - min(1, 2 * unresolved / (local import references + unresolved)))`; saturates at 50%. External imports are excluded. |
| Test file presence | 0.30 | `100 * sources_with_matching_test / sources_total`, using the name/import heuristic, not coverage. |
| TODO density | 0.20 | `100 * (1 - min(1, markers_per_KLOC / 20))`; TODO+FIXME markers per 1000 physical LOC. |

The overall score is the weighted mean of available components with weights renormalized to sum to one, rounded to one decimal. It is null when fewer than two components are available; unavailable components are never treated as zero. Levels are good (80+), fair (60+), attention (40+), and poor (below 40). Confidence is high when all four components are available and the analysis is complete, medium when at least three are available (including a partial result), low with exactly two, and none if there is no overall score. `partial` echoes the analysis result. Missing components include their reasons. Cycle availability requires a nonzero eligible graph-file denominator; unresolved-import availability requires at least one local or unresolved reference; test presence requires sources; TODO density requires known LOC and complete comment-marker data. If any marker file is unavailable, density is unavailable because totals may be lower bounds.

The score uses only analyzer output: graph edges/cycles, unresolved import references, test matches, parsed marker totals, and known physical LOC on analyzed Python/Dart files. The cycle denominator includes eligible source/test files that appear in an edge or have an analyzed status. Constants are module-level in `analysis.health` and recorded in the output `thresholds`. Because `metrics` is explicitly free-form JSON and older snapshots can omit arbitrary metric keys, this addition does not change schema version 4. Consumers must treat `metrics.health` as optional when reading stored snapshots.

### Git history and explainable risk (5.5)

History is opt-in through `AnalysisOptions.git_history` (default false) or the CLI flags `--git-history --history-days N` (1-3650 days). The pipeline reuses the hardened, no-shell Git environment and bounded capture helper from `projectlens.git.checkout`; it does not create a second subprocess path. It asks Git for the work-tree root, shallow status, and HEAD identity/date, then runs one bounded `git log` for file changes. The window is based on HEAD's committer timestamp, with an inclusive lower boundary at `HEAD timestamp - N * 86400`; wall-clock time is never consulted. Repeated analysis of the same commit therefore has the same window.

The history reader excludes merge commits and rename tracking, limits output to 8 MiB and the walk to 20,000 in-window commits, and reports truncation with a note when the commit cap is reached. Paths are NUL-delimited, normalized to repository-relative `/` paths, restricted to files in the analysis inventory, and made relative to the work-tree root when analysis starts in a subdirectory. Deleted and out-of-scope files do not create churn records. Author emails are hashed in memory solely to count distinct authors; raw emails and hashes are not persisted, only the distinct-author count. Churn is a count of commits touching a file, not added/deleted lines, ownership, or defect probability.

When requested, `metrics.git_history` has `formula_version: "1"`, availability/reason, window and HEAD metadata, aggregate counts, a truncation flag, and at most 20 churn-ranked files. A missing/non-repository root (`not_a_git_repository`), shallow checkout (`shallow_history`), or repository without commits (`no_commits`) is informational: it is represented in this metric without a diagnostic and does not make the result partial. Git failures/timeouts and output-limit failures report `git_unavailable` or `output_limit`, add a `git_history/GitHistoryUnavailable` diagnostic, and make the result partial. If history is not requested, `metrics.git_history` is absent. API checkouts deliberately remove `.git` and are depth one, so they do not expose usable history; API analysis leaves the option off. History remains opt-in to avoid extra local Git work and to keep ordinary and API analyses independent of repository history. Consumers of stored snapshots must treat this metric as optional.

`metrics.risk` is always computed and is also optional when reading older stored snapshots. It has formula version `1`, counts for all four levels, confidence, thresholds, and the top 20 non-minimal files ordered by descending points and then path. Eligible files are analyzed Python/Dart sources. Factors add: churn 1 point at 4 commits and 2 at 10 (omitted if unavailable); physical size 1 at 500 LOC and 2 at 1000; cycle membership 1; no associated test match 1; and fan-in 1 at 10 incoming local edges. Test association uses the existing name/import heuristic and is not coverage. Totals map to minimal (0), low (1-2), medium (3-4), and high (5+). Each factor carries its point value and a numeric explanation. Confidence is high when churn is available and medium when the churn factor is unavailable. This is an explainable heuristic, not a prediction of defects. It can miss risk from runtime behavior, change size, semantic complexity, test quality, and unobserved repository history; churn does not mean bugs.

Both metrics are stored in the free-form `metrics` object without a schema-version change. Adding risk intentionally adds a metric key to current analyses even when history is disabled; in that case churn is absent from factors and `churn_available` is false. Readers of old snapshots must treat both `metrics.git_history` and `metrics.risk` as optional.

### Size and coupling findings (5.6)

The pipeline stores `metrics.findings` while parser symbols are still available. `SymbolRecord` is transient and is not part of the stored `AnalysisResult`; computing findings in this stage avoids a schema change while retaining the evidence in the free-form metrics object. Older snapshots may omit `metrics.findings`, so consumers must treat it as optional.

Formula version `1` reports `large_function` (function/method span at least 80 lines, warning at 150), `large_class` (class/mixin/enum/extension span at least 400 lines, warning at 800), `many_members` (at least 30 direct methods, warning at 60), `high_fan_out` (at least 15 distinct local targets, warning at 30), and `high_fan_in` (at least 10 distinct local dependents, notice only). A high fan-in reason describes a central dependency where changes have wide impact; this is not necessarily a defect. Two-file strongly connected pairs are already represented by cycle groups and do not produce duplicate mutual-dependency findings. Thresholds are included in each result.

Only analyzed files contribute. Test files and generated Dart files (`*.g.dart`, `*.freezed.dart`, `*.gr.dart`) are excluded from symbol-size findings, while test and generated files remain graph nodes for coupling counts. Symbol sizes use inclusive line spans, not complexity; a long declaration body may be simple. Direct methods are counted by qualified-name prefix (`Class.method`), excluding deeper qualified names such as `Class.Nested.method`. Findings are deterministic, sorted with warnings first, and capped at 50 with a `truncated` flag. These static thresholds are heuristics, not defect prediction.

### Safe public GitHub checkout (milestone 2.1)

The Git boundary accepts only ASCII `https://github.com/<owner>/<repo>` URLs with optional `.git` and trailing slash; it rejects credentials, ports, query/fragment, other hosts, extra path components, and invalid names. `projectlens.git.checkout_repository` creates a depth-one isolated checkout with a timeout and a maximum checkout size measured before Git metadata is removed. Git runs as an argument list without a shell, with prompts and inherited Git configuration/credential helpers disabled, hooks and fsmonitor disabled, symlink materialization disabled, submodule recursion disabled, and LFS smudging neutralized. The protocol allowlist permits HTTPS only for application calls. Requested commits must be full 40-character SHAs (a shallow fetch by abbreviated SHA is not possible); they are fetched shallowly by SHA and the resulting SHA is checked against the request. On Windows, read-only Git object files are cleared before removal.

The checkout's `.git` directory is removed before it is returned to analysis; the analyzer receives only the working tree. The result owns a temporary directory and must be closed with its context manager or `cleanup()`. `_clone_url_override` and `_runner` are private test seams for local repositories and simulated failures; they are not exposed by the public URL validator and are not for application callers. Repository contents remain untrusted data and are never executed by ProjectLens.

### FastAPI API and analysis jobs (milestone 2.3)

The optional HTTP layer lives under `projectlens.app.api` and orchestration under `projectlens.app.services`; neither Pydantic schemas nor ORM rows are imported by the analysis core, CLI, or Git package. Constructing `create_app(settings=None)` is the only place that creates the database engine and executor. `DATABASE_URL` comes from the existing environment settings helper. Run Alembic migrations before starting the server; the app does not create production tables. The API prefix is `/api/v1`, and the documented entry point is `uvicorn --factory projectlens.app.api:create_app`.

`POST /projects` validates and canonicalizes the repository URL, reuses a project by canonical URL, creates a persisted job, and returns 202. Equivalent URL forms (optional `.git` and trailing slash) identify the same project. Read routes are `GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/snapshots`, `GET /projects/{id}/snapshots/{snapshot_id}`, and `GET /projects/{id}/snapshots/latest`; `POST /projects/{id}/analyses` re-analyzes and `GET /jobs/{job_id}` reports job state. `GET /health` returns liveness and a database availability field. Snapshot results are returned with their stored JSON structure unchanged. Snapshot list pagination defaults to 20, accepts limits from 1 through 100, and caps offset at 10,000.

Jobs run in a bounded in-process `ThreadPoolExecutor` (default two workers and eight waiting slots; configurable with `PROJECTLENS_MAX_WORKERS`, `PROJECTLENS_MAX_QUEUE`, `PROJECTLENS_CHECKOUT_TIMEOUT`, and `PROJECTLENS_CHECKOUT_MAX_BYTES`). A full queue returns 503 with `Retry-After: 5`. An active job for the same project and requested branch or commit is reused. A job checks out the repository with the safe Git boundary, analyzes its working tree, persists the result, and always cleans up the checkout. Failures persist a stable safe code/message; absolute paths, Git stderr, environment values, and tracebacks are not returned.

The job table is persisted by Alembic revision `0002_analysis_jobs`. On application startup, queued or running rows left by a prior process are marked failed with code `interrupted`; the in-process executor does not resume work. This deployment model is for one API process: multiple workers would need shared coordination before being enabled. If a snapshot already exists for the same project, resolved commit SHA, and analyzer schema version, the job succeeds by linking to that snapshot rather than creating a duplicate. Deleting a project cascades to its jobs and snapshots.

All client errors use `{"error":{"code":"...","message":"..."}}`; validation, missing-resource, queue-full, checkout, timeout, invalid-ref, and analysis errors have stable machine-readable codes. Generic server errors do not expose exception details. Request bodies use the framework defaults for size limits. CORS is not enabled yet; it belongs with the frontend milestone.

### PostgreSQL test strategy, CI, and container deployment (2.4)

DB-touching tests share `backend/tests/conftest.py`. SQLite remains the default
and uses a temporary file per test. Setting `TEST_DATABASE_URL` adds a
PostgreSQL run for repository, API integration, and migration tests. The target
database name must end in `_test`; otherwise the fixture refuses to proceed.
For each test, only the ProjectLens tables and `alembic_version` are dropped
before and after the test. Repository and API tests create their schema from
the ORM metadata; migration tests run Alembic `upgrade head` and `downgrade
base`. `DATABASE_URL` is never selected as the test target.

The backend GitHub Actions workflow separates core checks from optional app
dependencies: the core suite runs on Python 3.10, 3.12, and 3.13 without the
`app` extra, while Python 3.12 runs the app suite against a disposable
PostgreSQL service and a `_test` database. A Docker image build job is included
without publishing an image.

Compose topology is PostgreSQL with a named volume and readiness probe, a
one-shot Alembic migration service, then the API after successful migration.
The API port binds to loopback, runs read-only with a temporary filesystem for
repository checkouts, and runs as a non-root user in the image. The Compose stack is **verified**: `docker compose up --build` on Docker 29.8
ran every migration to head, the API container became healthy, ran as uid
10001 with a read-only root filesystem, and a real end-to-end flow (public
repository clone, analysis, snapshot persistence) completed in the container
against PostgreSQL 18. The GitHub Actions workflow itself has not been run.

### Project tasks (milestone 3.1)

Tasks are persisted as `app.db.models.Task`, separate from analyzer core
dataclasses, and belong to a project with cascade deletion. A task stores a
1–200 character title, optional description up to 4,000 characters, status,
priority, optional trimmed category, stable per-project position, source and
optional source key, plus UTC creation/update/completion timestamps. Statuses
are `TODO`, `IN_PROGRESS`, `DONE`, and `BLOCKED`; priorities are `LOW`,
`MEDIUM`, `HIGH`, and `CRITICAL`. Sources are `manual` and reserved `import`.
The nullable `(project_id, source_key)` uniqueness supports later idempotent
TODO.md imports. Listing is ordered by position then ID and caps page size at
100 and offset at 10,000.

Status changes follow a pure transition table: `TODO` can move to `IN_PROGRESS`,
`DONE`, or `BLOCKED`; `IN_PROGRESS` can move to `TODO`, `DONE`, or `BLOCKED`;
`BLOCKED` can move to `TODO` or `IN_PROGRESS`; `DONE` can reopen to `TODO` or
`IN_PROGRESS`. Repeating the current status is an accepted idempotent no-op.
Entering `DONE` sets `completed_at`; leaving it clears that timestamp.

The `/api/v1/projects/{id}/tasks` endpoints create (201), list, read, partially
update, and delete (204) project-scoped tasks. List filters support one or more
statuses, priority, category, and title search. Invalid request values return
the standard validation envelope (`422`, `validation_error`); invalid status
edges return `409`, `invalid_status_transition`; missing projects or tasks
return scoped `404` errors. Unknown PATCH fields are rejected. Migration
`0003_project_tasks` adds the task table, portable checks, indexes, and cascade
foreign key.

### Roadmap import and progress (milestone 3.4)

`POST /api/v1/projects/{id}/roadmap/import` accepts `{"markdown": "...", "dry_run": false}` and parses the submitted text with the pure checklist parser. It never accepts a path or reads a server-side file, and rejects bodies over 1 MiB with a 413 error. Parser failures use the stable `invalid_checklist` code; request shape failures use `validation_error`. Imported tasks use source `import`, parser `source_key`, MEDIUM priority, and TODO/DONE initial status based on the checkbox. New items are appended in document order after all existing project tasks. Titles over the Task limit of 200 characters are skipped and reported. Categories join heading labels with ` / `; values longer than 80 characters become an ellipsis followed by the rightmost 79 characters. An empty heading path has no category.

Re-import matches only imported tasks by `(project, source_key)`. A new key creates a task. Unchecked items never modify existing task state; checked items move TODO or IN_PROGRESS to DONE using normal completion timestamps. A checked item matching BLOCKED is reported as a conflict. DONE remains DONE when unchecked. Existing title/category values are not rewritten, and manual-source tasks are never selected for update. Imported keys missing from a later document are reported as `missing_from_source` and remain in storage. The report includes exact counts, capped item arrays (first 200 entries per list) and per-list `truncated` flags. `dry_run: true` returns that report without writes. Each non-dry-run import is committed as one transaction; a uniqueness race causes one re-plan/retry, then a safe 409 `roadmap_import_conflict` if still unresolved. No migration is needed because the Task model already has the source/key fields and unique constraint.

`GET /api/v1/projects/{id}/roadmap/progress` applies progress formula version 1 to all task sources by default; `?source=manual` or `?source=import` filters the input. The response includes overall, category, and section totals, the formula version and description, and `manual_status_only: true`. It counts DONE divided by all tasks, gives IN_PROGRESS no partial credit, and keeps BLOCKED in the denominator. Empty roadmaps return `state: "empty"` and `percent_complete: null`. The API selects only status, category, and priority columns; it does not make analysis-based estimates, which belong to milestone 4.

### Code-aware tracking tasarımı (milestone 4)

**Amaç:** Manuel task durumunu analiz kanıtıyla yan yana göstermek; ikisini karıştırmamak. Manuel durum (`TODO/IN_PROGRESS/DONE/BLOCKED`) kullanıcının beyanıdır. Kod-bilinçli değerlendirme ise saklanan snapshot'tan hesaplanan, gerekçeli bir *tahmin*dir ve manuel durumu asla değiştirmez.

**Bağlantılar (`TaskFileLink`).** Task'a repository köküne göre `/` ayıraçlı bir yol bağlanır: tek dosya (`src/pkg/a.py`) veya dizin öneki (`src/pkg/`, sonda `/`). Bağlantı snapshot'a değil projeye aittir; yeni snapshot'larda aynı bağlantı yeniden değerlendirilir. Yollar doğrulanır (mutlak yol, `..`, ters eğik çizgi, kontrol karakteri reddedilir).

**Kabul kriterleri (`AcceptanceCriterion`).** Her kriter bir tür, parametreler ve açıklama taşır. Yalnızca saklanan AnalysisResult JSON'undan değerlendirilebilen türler desteklenir:

| Tür | Anlamı (snapshot verisinden) |
| --- | --- |
| `file_exists` | Belirtilen dosya kayıtlarda var ve okunabilir/analiz edilmiş |
| `path_has_files` | Dizin önekinde, isteğe bağlı dil/dosya sınıfı filtresiyle, en az N dosya var |
| `import_edge_exists` | A dosyasından B dosyasına yerel import kenarı var |
| `not_in_cycle` | Belirtilen dosya hiçbir cycle grubunda yok |
| `max_todo_markers` | Yol altındaki TODO/FIXME toplamı en çok N |
| `no_analysis_failures` | Yol altında parse/okuma hatalı dosya yok |
| `manual_attestation` | Kullanıcının kendi işaretlediği kriter (otomatik doğrulanamaz) |

Sembol (fonksiyon/class) kriterleri şimdilik yoktur: sembol kayıtları saklanan sonuca dahil değildir. Gerekirse sonraki milestone'da sonuç sözleşmesi genişletilir.

**Değerlendirme çıktısı.** Her kriter için `met`, `unmet` veya `unknown` sonucu ve gerekçe metni üretilir. `unknown` nedenleri: snapshot kısmi (`partial`) ve ilgili yol kapsanmıyor, dosya `skipped/unreadable`, yol snapshot'ta hiç yok ve varlığı kanıtlanamıyor, veya kriter manuel. Otomatik kanıt yoksa tahmin üretilmez.

**İlerleme tahmini.** `automatic_percent = met / (met + unmet)` yalnızca otomatik kriterler üzerinden; `unknown` paydaya girmez ama güven düzeyini düşürür. `manual_attestation` kriterleri ayrı raporlanır (kullanıcı beyanı, kanıt değil) ve otomatik yüzdeye karışmaz. Hiç otomatik kriter yoksa veya hepsi `unknown` ise tahmin `null` ve `confidence = "none"`. Güven: `high` (>=3 değerlendirilen kriter, unknown yok, snapshot tam), `medium`, `low`, `none`. Bağlı dosyaların varlığı bağlam olarak listelenir ama **ağırlığı sıfırdır**; "dosya var" tamamlanma kanıtı sayılmaz (yalnızca açıkça tanımlanmış bir `file_exists` kriteri sayılır).

**Sapma (divergence).** Manuel durum `DONE` iken tahmin düşükse (< %100 ve kanıt var) veya durum `TODO`/`BLOCKED` iken tahmin %100 ise bayrak konur; sistem durumu değiştirmez, yalnızca gösterir.

**Belirsizlik görünürlüğü.** Yanıtlar her zaman `confidence`, `reasons[]`, `unknown_criteria[]`, `snapshot` (id, commit, partial) ve `formula_version` içerir. Snapshot yoksa 200 ile `state: "no_snapshot"` döner (hata değil).

**Katmanlama.** Değerlendirme motoru `projectlens/tracking/evidence.py` içinde saf fonksiyonlardır (stdlib; düz dict/dataclass girdi). Persistence ve API `projectlens/app/` altındadır; ORM ve API şemaları motora sızmaz.

### Task links and acceptance criteria (milestone 4.2)

`TaskFileLink` and `AcceptanceCriterion` are project-scoped through their task and cascade with task deletion. Relative paths normalize to `/` separators, are bounded to 500 characters, and reject absolute paths, drive prefixes, `..` segments, and control characters. Criterion parameters are validated per kind in the API and repository; links and criteria are each limited to 50 per task. Migration `0004_task_links_and_criteria` adds both tables and their task indexes. CRUD routes live under `/api/v1/projects/{id}/tasks/{task_id}`; criterion kind is immutable after creation.

### Assessment endpoints (milestone 4.3)

`GET /api/v1/projects/{project_id}/tasks/{task_id}/assessment?snapshot=latest|{snapshot_id}` evaluates the task's ordered acceptance criteria and file links against the latest or explicitly project-scoped snapshot. With no latest snapshot it returns the engine's `no_snapshot` assessment; an unknown explicit snapshot is a 404. The response adds project/task IDs to the evidence engine output. `GET /api/v1/projects/{project_id}/roadmap/assessment` assesses every project task against one loaded latest snapshot and reports state, confidence, estimate availability, unknown criteria, and divergence aggregates. The synchronous aggregate is capped at 1,000 tasks. It reports an average estimate only for tasks with estimates and never combines estimated and manual progress; `/roadmap/progress` and task statuses are unchanged.
