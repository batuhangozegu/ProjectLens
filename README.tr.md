English: [README.md](README.md)

# ProjectLens

ProjectLens, kod depolarını yerel olarak inceleyen bir analiz aracıdır. Kurulabilir CLI; Python ve Dart dosyalarını kodu çalıştırmadan ayrıştırır, Python importlarını ve Dart dosya/paket URI'lerini çözümler, bağımlılık döngülerini bulur, tanımlı framework'leri ve kaynak–test dosyası eşleşmelerini gösterir. Temel metrikleri hesaplar ve tekrarlanabilir JSON çıktısı üretir. FastAPI backend ve React/TypeScript web arayüzü üzerinden herkese açık GitHub depolarını analiz etmek, sonuçları saklamak ve proje görevlerini izlemek de mümkündür.

Analiz JSON'undaki `metrics.health`, bağımlılık döngüleri, çözümlenemeyen importlar, ad/import benzerliğine göre test dosyası eşleşmeleri ve TODO/FIXME yoğunluğuna dayanan, gerekçeleri görülebilen bir göstergedir (formül sürümü 1). Kalite, doğruluk veya test kapsamı garantisi vermez. Eksik veriye dayanan bileşenler hesaplanamaz olarak gösterilir; eski kayıtlı analizlerde bu alan bulunmayabilir.

Yeni analizlerdeki `metrics.risk`; istendiğinde Git değişim sıklığını, dosya boyutunu, döngüleri, test eşleşmelerini ve yerel bağımlılıkların dosyaya geliş sayısını kullanır. Bu statik gösterge hata tahmini değildir; test eşleşmesi de test kapsamı değildir. Git geçmişi isteğe bağlıdır ve zaman aralığı HEAD commit'inin tarihine göre belirlenir. Git deposu olmayan dizinlerde ve API'nin tek commit derinliğindeki klonlarında geçmiş bilgisi kullanılamaz. Eski analizlerde `metrics.risk` ve `metrics.git_history` bulunmayabilir.

`metrics.findings`, büyük fonksiyon/sınıfları, çok metotlu sınıfları ve yerel bağımlılık giriş/çıkışı yüksek dosyaları gösterir. Belgelenmiş eşikler ve satır aralıklarıyla üretilen bu bulgular, inceleme için başlangıç noktalarıdır; hata tahmini değildir. Eski analizler bu alanı içermeyebilir. Ayrıntılar [mimari belgesinde](docs/ARCHITECTURE.md#size-and-coupling-findings-56).

## Desteklenen diller

| Destek düzeyi | Diller / dosyalar |
| --- | --- |
| Ayrıştırma: importlar, bağımlılık grafiği, döngüler, semboller ve boyut bulguları | Python, Dart (Flutter) |
| Manifest üzerinden framework tespiti | Python: `pyproject.toml`, `requirements*.txt`; Dart: `pubspec.yaml` |
| Yalnızca sayım: dosya sayısı, fiziksel satır sayısı, dil etiketi ve dosya ağacı | Diğerleri; örneğin JavaScript/TypeScript, Java, Go, yapılandırma ve dokümantasyon dosyaları |

Diğer diller dosya ağacında ve boyut metriklerinde görünür; bağımlılık kenarları, importlara dayalı sağlık bileşenleri ve kod bulguları üretilmez. Dart ayrıştırıcısı, bildirimlere odaklanan küçük bir lexer'dır; tam dil grameri veya tip çözümlemesi sunmaz. Ayrıntılar için [mimari belgesine](docs/ARCHITECTURE.md) bakabilirsiniz.

## Docker Compose ile hızlı başlangıç

Docker ve Docker Compose kurulu olmalıdır. Depo kökünde `.env.compose.example` dosyasını `.env` adıyla kopyalayın. `POSTGRES_PASSWORD` değerini yerel bir parolayla değiştirin. Parola bağlantı URL'sine yerleştirildiği için URL'de güvenle kullanılabilen karakterler seçin; gerçek bilgileri sürüm kontrolüne eklemeyin.

```sh
cp .env.compose.example .env
# .env dosyasındaki parolayı değiştirin, ardından:
docker compose up --build
```

PowerShell'de kopyalama için `Copy-Item .env.compose.example .env` kullanabilirsiniz.

Compose; veriyi adlandırılmış bir volume'de saklayan PostgreSQL'i başlatır, sağlık kontrolünü bekler, migration işlemlerini tek seferlik bir serviste çalıştırır ve API'yi açar. API yalnızca `127.0.0.1:${API_PORT}` adresine bağlanır; varsayılan port `8000`'dir. Sağlık kontrolü: `http://127.0.0.1:8000/api/v1/health`; etkileşimli API belgesi: `http://127.0.0.1:8000/docs`.

Bu Compose dosyası veritabanını ve backend'i çalıştırır. Web arayüzünü ayrıca, aşağıdaki npm adımlarıyla başlatın. AI varsayılan olarak kapalıdır; açmak için yerel bir Compose override dosyasında `api` servisinin `environment` bölümüne `AI_ENABLED: "true"` ekleyin.

İmaj oluşturma ve `docker compose up --build` akışı daha önce Docker 29.8 ile doğrulanmıştır: migration'lar tamamlanmış, API sağlıklı duruma geçmiş ve herkese açık bir deponun gerçek analizi PostgreSQL'e kaydedilmiştir. API konteyneri root olmayan kullanıcıyla ve salt okunur dosya sistemiyle çalışır.

```sh
docker compose down
```

Servisleri durdurur. `docker compose down -v` komutu veritabanı volume'ünü de siler; saklanan projeleri korumak istiyorsanız `-v` kullanmayın.

## Docker olmadan yerel kurulum

Backend için Python 3.10 veya üstü, GitHub depolarını klonlamak için Git gerekir. Web arayüzü için Node.js ve npm kurulu olmalıdır. Depo kökünden:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e 'backend[dev,app]'
```

PowerShell'de sanal ortamı `.venv\Scripts\Activate.ps1` ile etkinleştirin. Yalnızca analiz motoru ve CLI kullanacaksanız `python -m pip install -e 'backend[dev]'` yeterlidir. `dev` test araçlarını; `app` ise API, veritabanı ve migration bağımlılıklarını kurar.

### PostgreSQL ile backend

PostgreSQL'de geliştirme kullanıcısı ve veritabanı oluşturun. Örnek parolayı kendi yerel parolanızla değiştirin; geliştirme veritabanının adı `_dev` ile bitsin.

```sh
psql -U postgres -c "CREATE ROLE projectlens LOGIN PASSWORD 'YEREL_PAROLANIZ';"
psql -U postgres -c "CREATE DATABASE projectlens_dev OWNER projectlens;"
```

`backend/.env.example` dosyasını `backend/.env` olarak kopyalayın ve `DATABASE_URL` değerini yerel bağlantınıza göre değiştirin:

```dotenv
DATABASE_URL=postgresql+psycopg://projectlens:YEREL_PAROLANIZ@localhost:5432/projectlens_dev
```

Veritabanı ayarı önce süreç ortamından, yoksa çalışma dizinindeki veya `backend/` altındaki `.env` dosyasından okunur. Gerçek kimlik bilgilerini Git'e eklemeyin. AI değişkenleri bu veritabanı `.env` okuyucusuyla yüklenmez; onları API sürecinin ortamında tanımlayın.

```sh
cd backend
alembic upgrade head
uvicorn --factory projectlens.app.api:create_app --host 127.0.0.1 --port 8000
```

### SQLite ile backend

Yerel denemeler için PostgreSQL kurmadan SQLite kullanabilirsiniz. Aynı `app` bağımlılıklarını kurduktan sonra `backend/` dizininde:

```sh
export DATABASE_URL='sqlite:///./projectlens_dev.sqlite'
alembic upgrade head
uvicorn --factory projectlens.app.api:create_app --host 127.0.0.1 --port 8000
```

PowerShell karşılığı:

```powershell
cd backend
$env:DATABASE_URL = 'sqlite:///./projectlens_dev.sqlite'
alembic upgrade head
uvicorn --factory projectlens.app.api:create_app --host 127.0.0.1 --port 8000
```

SQLite dosyası çalışma dizininde oluşur. Süreç ortamındaki `DATABASE_URL`, `.env` dosyasındaki PostgreSQL ayarının önüne geçer.

### Web arayüzünü çalıştırma

API açıkken ikinci bir terminalde, depo kökünden:

```sh
cd frontend
npm install
npm run dev
```

Terminalde yazılan yerel adresi açın; genellikle `http://localhost:5173` olur. Vite geliştirme sunucusu `/api` isteklerini `http://localhost:8000` adresine yönlendirir. Farklı bir API öneki için `VITE_API_BASE` kullanılır; varsayılan `/api/v1`'dir. Statik dağıtımda bu değer derleme sırasında ayarlanır. Üretim derlemesi `npm run build` ile alınabilir.

## Web arayüzünü kullanma

1. **Projeleriniz:** Herkese açık bir GitHub deposunun `https://github.com/sahip/depo` adresini girip **Proje ekle** düğmesine basın. Analiz arka planda çalışır; tamamlandığında liste güncellenir. API yalnızca herkese açık HTTPS GitHub adreslerini kabul eder.
2. **Genel Bakış:** Projeyi açarak son analiz kaydını ve özetini inceleyin. Analiz henüz tamamlanmamışsa yüklenme/boş durumunu bekleyin. Yeni analizler ayrı snapshot olarak saklanır.
3. **Dosyalar:** Açılıp kapanabilen dosya ağacından dosya seçin; bağımlılık grafiği ve ayrıntı panelini inceleyin. Döngüdeki dosyalar grafikte vurgulanır. Grafik en fazla 120 dosya gösterir; klavyeyle kullanılabilen dosya ağacı alternatif gezinme yoludur.
4. **Analizler:** Metrikleri, sağlık puanının bileşenlerini, sıralanmış riskleri ve mevcutsa Git etkinliğini görün. Bunlar statik göstergelerdir; hatasızlık, testlerin geçmesi veya test kapsamı anlamına gelmez. Kullanılamayan veriler ayrıca belirtilir.
5. **Yol Haritası:** Markdown görevlerini aşağıdaki API ile içe aktarın. Görev durumları ve elle yönetilen ilerleme, analiz verisine dayanan değerlendirmelerle yan yana gösterilir. Durum değişiklikleri kaydedilir. Kod değerlendirmesi görev durumunu otomatik değiştirmez; veri eksikliği ve güven düzeyi görünür kalır.
6. **Yapay Zeka:** İsteğe bağlı depo, mimari veya risk açıklaması isteyin. Kendi anahtarınızı kullanma akışında sağlayıcı, model ve gerekiyorsa uyumlu sunucu adresini seçin; anahtar tarayıcıda kalır ve her istekle başlıkta gönderilir. Bu backend sözleşmesini kullanmak için web istemcisinin aşağıdaki `X-AI-*` başlıklarını göndermesi gerekir. Açıklama istemek veya bağlantı testi yapmak dışında sağlayıcıya otomatik çağrı yapılmaz. Yalnızca aşağıda belirtilen sınırlı analiz verileri gönderilir.
7. **Proje silme:** Proje kartındaki **Sil** veya genel bakıştaki **Projeyi sil** işlemini onaylayın. Proje ve ilişkili analiz/görev kayıtları silinir. Kuyrukta ya da çalışmakta olan analizi bulunan proje, işlem bitene kadar silinemez.

Gezinme URL hash'lerini kullanır; örneğin `#/projects/1/files`. Bu nedenle arayüz herhangi bir statik dosya sunucusunda da çalışabilir. Daha fazla bilgi ve ekran görüntüleri [frontend README'sinde](frontend/README.md#using-the-app).

## Yol haritasını API ile içe aktarma

API sunucudaki bir `TODO.md` dosyasını kendiliğinden okumaz. Markdown kontrol listesi metnini JSON gövdesindeki `markdown` alanına gönderin. İstek sınırı 1 MiB'dir. Önizleme için `dry_run: true` kullanın; gerçek kayıt için `false` gönderin.

```sh
curl -X POST http://127.0.0.1:8000/api/v1/projects/PROJE_ID/roadmap/import \
  -H 'Content-Type: application/json' \
  --data-binary '{"markdown":"# Kurulum\n- [ ] Bagimliliklari kur\n- [x] Projeyi olustur\n","dry_run":true}'
curl http://127.0.0.1:8000/api/v1/projects/PROJE_ID/roadmap/progress
curl 'http://127.0.0.1:8000/api/v1/projects/PROJE_ID/roadmap/progress?source=import'
```

Yeniden içe aktarma, ayrıştırıcının kararlı anahtarlarını eşleştirerek mükerrer görev oluşturmaz. İşaretli kutular yalnızca mevcut `TODO` veya `IN_PROGRESS` görevlerini tamamlayabilir. Mevcut başlık/kategoriler ve elle oluşturulmuş görevler korunur.

Elle yönetilen ilerlemede yalnızca `DONE` tamamlanmış sayılır. `IN_PROGRESS` kısmi puan getirmez; `BLOCKED` görevler toplam görev sayısında kalır. Boş yol haritasında yüzde `null`, durum `state: "empty"` olur. Bu oran analizden hesaplanan tahminleri içermez.

Kod verisine dayanan değerlendirmeler ayrı uçlardadır:

```text
GET /api/v1/projects/PROJE_ID/tasks/GOREV_ID/assessment
GET /api/v1/projects/PROJE_ID/roadmap/assessment
```

Snapshot kanıtlarını, bilinmeyen kriterleri ve belirsizliği raporlarlar; elle yönetilen ilerlemeyle birleştirilmezler. Görev–dosya bağlantıları ve kabul kriterleri de API ile yönetilebilir. Bir dosyanın varlığı tek başına özelliğin tamamlandığını kanıtlamaz.

## İsteğe bağlı AI: kendi API anahtarını kullanma

Uvicorn'u başlatmadan önce API sürecinde `AI_ENABLED=true` ayarlayın. POSIX kabuğunda `export AI_ENABLED=true`, PowerShell'de `$env:AI_ENABLED = 'true'` kullanabilirsiniz. Varsayılan davranış kapalıdır. Compose kullanıyorsanız değişkeni yerel bir override üzerinden `api` servisinin ortamına ekleyin.

Kullanıcının anahtarı tarayıcıda tutulur ve her AI isteğinde `X-AI-Key` başlığıyla gönderilir. Backend anahtarı yalnızca isteği işlerken bellekte kullanır ve seçilen sağlayıcıya kimlik doğrulama amacıyla iletir. Veritabanına, dosyaya, snapshot'a veya önbelleğe kaydetmez; prompt'a, loglara, hata metnine ya da yanıt gövdesine eklemez.

Her iki AI ucu aynı başlıkları kabul eder:

| Başlık | Değer ve sınır |
| --- | --- |
| `X-AI-Provider` | Tam olarak `anthropic`, `openai` veya `openai-compatible`; herhangi bir AI başlığı gönderiliyorsa zorunlu |
| `X-AI-Model` | 1–200 ASCII karakter; harf/rakamla başlar, devamında harf/rakam veya `._:/+@-` bulunabilir |
| `X-AI-Base-Url` | Yalnızca uyumlu sağlayıcıda zorunlu; HTTP(S), host gerekli, en fazla 2.048 ASCII karakter; kullanıcı bilgisi, sorgu ve fragment içeremez |
| `X-AI-Key` | Verildiğinde 1–4.096 görünür ASCII karakter; boşluk içeremez. Anthropic/OpenAI için zorunlu, yerel uyumlu sunucularda isteğe bağlı |

Varsayılan modeller Anthropic için `claude-haiku-4-5-20251001`, OpenAI için `gpt-4.1-mini`'dir. İkisinde de modeli değiştirebilirsiniz. Uyumlu sağlayıcıda kurulu modelin adını açıkça belirtmeniz gerekir. Ağdan model listesi alınmaz. Hesabınızda modelin kullanılabilirliğini resmi [Anthropic](https://platform.claude.com/docs/en/models/haiku-4-5/overview) ve [OpenAI](https://developers.openai.com/api/docs/models/gpt-4.1-mini) belgelerinden kontrol edin.

Ollama için örnek taban adres `http://localhost:11434`, LM Studio için `http://localhost:1234/v1` olabilir. Yalnızca sunucu kökü verilirse `/v1` eklenir; açıkça verilen API yolu korunur. Sonuna `/chat/completions` eklenir. Docker'da `localhost`, API konteynerini ifade eder; bilgisayarınızdaki model sunucusu için konteynerden erişilebilen bir adres gerekir. Uzak bağlantılarda anahtar için HTTPS kullanın.

Depo verisi göndermeden, anahtarsız yerel model sunucusunu sınayın:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/ai/test \
  -H 'X-AI-Provider: openai-compatible' \
  -H 'X-AI-Model: KURULU_MODEL_ADI' \
  -H 'X-AI-Base-Url: http://localhost:11434'
```

Bu uç yalnızca sabit bir bağlantı testi prompt'u ve en fazla 16 çıktı token'ı kullanır. Başarılı yanıt `{"ok":true,"provider":"openai-compatible","model":"KURULU_MODEL_ADI"}` biçimindedir. Proje veya analiz kaydı okumaz. Anthropic/OpenAI kullanırken sağlayıcıyı/modeli seçip `X-AI-Key` başlığını da gönderin; taban URL başlığını kullanmayın.

Analiz açıklaması istemek için:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/projects/PROJE_ID/ai/explanations \
  -H 'Content-Type: application/json' \
  -H 'X-AI-Provider: openai-compatible' \
  -H 'X-AI-Model: KURULU_MODEL_ADI' \
  -H 'X-AI-Base-Url: http://localhost:11434' \
  -d '{"kind":"architecture","snapshot":"latest"}'
```

`kind`, `repository`, `architecture` veya `risk`; `snapshot`, `latest` veya o projeye ait snapshot ID'si olabilir. Yanıt; açıklama metni, kaynak referansları, bağlam bütçesi, kullanım bilgisi ve uyarı içerir. Üretilen açıklamalar sunucuda saklanmaz.

Sağlayıcıya ne gider: sabit sistem talimatı ve kayıtlı analizden seçilmiş sınırlı metadata. İstenen açıklama türüne göre dosya/dil sayıları, göreli dosya yolları ve boyutları, örnek bağımlılıklar, framework ve manifest referansları, test eşleşmeleri, sağlık/risk/bulgu özetleri ve kaynak referansları seçilir. Kaynak dosyaların içeriği, klonlanmış depo, depo URL'si, Git kimlik bilgileri, görevler veya snapshot'ın tamamı gönderilmez. Dosya adları ve analiz metadatası yine de hassas olabilir. Anahtar yalnızca kimlik doğrulama başlığında gider.

Varsayılan sınırlar `AI_MAX_CONTEXT_BYTES=16384`, `AI_MAX_OUTPUT_TOKENS=512`, `AI_TIMEOUT_S=20`'dir. Bayt sınırı seçilen bağlam JSON'una aittir; sabit talimatlar ve istek zarfı ek yer kaplar. Zaman aşımı her denemedeki soket işlemlerine uygulanır, toplam işlem süresi garantisi değildir. Sağlayıcı yanıtı 64 KiB'yi, dönen metin 16 KiB UTF-8'i aşarsa reddedilir. Uyumlu sunucu kullanım bilgisi vermiyorsa token sayıları sıfır olarak raporlanır.

Hiçbir AI başlığı yoksa API, süreç ortamındaki `PROJECTLENS_AI_PROVIDER`, `PROJECTLENS_AI_MODEL`, `PROJECTLENS_AI_BASE_URL`, `PROJECTLENS_AI_API_KEY` değerlerini kullanabilir. Bunlar işletmecinin sağladığı ayarlardır; ProjectLens onları kaydetmez. Herhangi bir AI başlığı varsa tüm seçim o isteğe aittir; ortam anahtarı, tarayıcıdan seçilen sunucuya taşınmaz. Hiçbir sağlayıcı yapılandırılmamışsa kullanılabilirlik hatası döner. Tekrarlanan veya geçersiz başlıklar değerleri yansıtılmadan reddedilir.

| Durum | HTTP / hata kodu |
| --- | --- |
| AI kapalı | `503 ai_disabled` |
| Geçersiz başlık/ayar | `422 validation_error` |
| Zorunlu anahtar eksik veya sağlayıcı 401/403 döndürdü | `401 ai_auth_failed` |
| Zaman aşımı | `503 ai_timeout` |
| Sağlayıcı/ağ kullanılamıyor veya kota/hız sınırı nedeniyle 429 | `503 ai_unavailable` |
| Bozuk, boş, fazla büyük, anahtarı yansıtan yanıt veya diğer istek reddi | `502 ai_invalid_response` |

Yalnızca kullanılabilirlik hataları bir kez yeniden denenir; bu ikinci bir ücretli çağrı oluşturabilir. Ücret seçtiğiniz modele ve sağlayıcıya bağlıdır; fiyat listesi ağdan alınmaz. AI çıktıları tavsiye niteliğindedir, kaynaklarını kontrol edin. Depodan gelen değerler güvenilmeyen veri olarak sınırlandırılır; bu yaklaşım prompt injection riskini azaltır ama modelin talimatlara uymasını garanti etmez. Tam sözleşme [mimari belgesinde](docs/ARCHITECTURE.md#ai-explanations-cost-and-data-transfer-6265).

## CLI kullanımı

CLI, API veya veritabanı gerektirmeden yerel bir dizini analiz eder:

```sh
python -m projectlens analyze /projenizin/yolu
projectlens analyze . --output analysis.json
python -m projectlens analyze . --top 5 --max-diagnostics 3
python -m projectlens analyze . --git-history --history-days 180
```

`--output DOSYA`, tam sonucu UTF-8 JSON olarak yazar; terminal özeti yine gösterilir. JSON tekrarlanabilirdir ve depo köküne göre göreli yollar kullanır. Mutlak kök yol bilerek çıkarılır; başka dizine kopyalanmış aynı ağaç aynı JSON'u üretir. En büyük dosya ve tanı gösterim sınırları terminal özetini etkiler; `--top`, JSON'daki en büyük dosya sayısını da belirler.

Git geçmişi toplamanın çıktı ve commit sınırları vardır. Merge commit'leri ve yeniden adlandırma takibi dahil değildir. Ham e-posta adresleri yerine yalnızca yazar sayıları saklanır. Değişim sıklığı satır değişikliği veya hata olasılığı değil, commit sayısıdır. Formül, veri bulunamama nedenleri ve sınırlar [mimari belgesinde](docs/ARCHITECTURE.md#git-history-and-explainable-risk-55).

### Örnek çıktı

`python -m projectlens analyze backend/tests/fixtures/sample_repo` komutunun çıktısı aşağıdadır. `Root:` yolu kısaltılmıştır; terminal çıktısının geri kalanı İngilizce olarak korunmuştur.

```text
ProjectLens analysis
Root: .../sample_repo
*** PARTIAL RESULT: some files or directories could not be fully analyzed. ***

Files: 10 (Python: 8)
Physical LOC: 25 (known: 10, unavailable: 0)
Python LOC: 21 (known: 8, unavailable: 0)
Largest files:
       7 LOC  src/pkg/left.py
       4 LOC  src/pkg/right.py
       3 LOC  broken.py
       2 LOC  README.md
       2 LOC  pyproject.toml
       2 LOC  src/isolated.py
       2 LOC  tests/test_sample.py
       1 LOC  flat.py
       1 LOC  flat_consumer.py
       1 LOC  src/pkg/__init__.py
TODO/FIXME: 2 (TODO: 1, FIXME: 1)
Dependencies: 3 local edges, 1 external, 0 unresolved
Cycle groups: 1
Frameworks declared: 0
Test matches: 0 of 6 source files have a matching test file (name/import heuristic, not coverage)
Health: 25.0 (poor, confidence: medium)
  Health component unavailable (todo_density): Marker data is incomplete (1 files unavailable), with 2 known markers across 18 LOC; TODO/FIXME density cannot be scored.
Risk: 0 high, 0 medium, 6 low
  src/pkg/left.py (low, 2 points: cycle, untested)
  src/pkg/right.py (low, 2 points: cycle, untested)
  flat.py (low, 1 points: untested)
  1. src/pkg/left.py, src/pkg/right.py
Diagnostics: 2
  parse/SyntaxError [broken.py]: invalid syntax (line 3)
  parse/TokenizeError [broken.py]: ('unexpected EOF in multi-line statement', (3, 0)) (line 3)
```

Örnek depoda sözdizimi hatalı bir dosya vardır; sonuç üretildiği halde komut 3 koduyla çıkar.

### Çıkış kodları

| Kod | Anlamı |
| --- | --- |
| 0 | Analiz, pipeline'ın kısmi sonuç saydığı bir durum olmadan tamamlandı. |
| 1 | Analizi veya çıktıyı engelleyen hata: geçersiz, bulunamayan, okunamayan ya da dizin olmayan kök; geçersiz/yazılamayan çıktı yolu veya çıktı olarak dizin seçilmesi. Hata traceback olmadan stderr'e yazılır. |
| 2 | Argparse kullanım hatası. |
| 3 | Sonuç üretildi ama okunamayan dosya/dizin, boyut sınırı, ayrıştırma hatası veya ayrıştırıcı tanıları nedeniyle `AnalysisResult.partial` doğru. İstenen JSON, bu kod dönmeden önce yazılır. |

Beklenen dışlamalar ve sembolik bağlantıların atlanması tek başına sonucu kısmi yapmaz.

## API özeti

Tüm uygulama uçları `/api/v1` önekini kullanır. Tam istek/yanıt şemaları çalışan API'nin `/docs` sayfasında bulunur. Hatalar genel olarak `{"error":{"code":"…","message":"…"}}` zarfıyla döner.

| Yöntem ve yol | İşlev |
| --- | --- |
| `GET /health` | API/veritabanı sağlık bilgisi |
| `GET /projects` | Projeleri listeleme |
| `POST /projects` | Proje oluşturma ve analizi kuyruğa ekleme; 202 ile proje/iş ID'leri döner |
| `GET /projects/{id}` | Proje ve son snapshot özeti |
| `DELETE /projects/{id}` | Projeyi; snapshot, iş, görev, dosya bağlantıları ve kabul kriterleriyle silme; başarılıysa 204 |
| `POST /projects/{id}/analyses` | Yeni analiz başlatma |
| `GET /jobs/{id}` | Analiz işinin durumunu sorgulama |
| `GET /projects/{id}/snapshots` | Snapshot listesi |
| `GET /projects/{id}/snapshots/latest`, `GET /projects/{id}/snapshots/{snapshot_id}` | Kayıtlı analiz JSON'u |
| `/projects/{id}/tasks` | Görev listeleme/oluşturma ve görev bazında okuma/güncelleme/silme |
| `/projects/{id}/tasks/{task_id}/links`, `/criteria` | Dosya bağlantısı ve kabul kriteri işlemleri |
| `POST /projects/{id}/roadmap/import` | Markdown kontrol listesi içe aktarma ve önizleme |
| `GET /projects/{id}/roadmap/progress` | Elle yönetilen görev ilerlemesi |
| `GET /projects/{id}/tasks/{task_id}/assessment` | Görevin analiz kanıtlarıyla değerlendirilmesi |
| `GET /projects/{id}/roadmap/assessment` | Proje görevlerinin ortak snapshot üzerinden değerlendirilmesi |
| `POST /ai/test` | Depo verisi içermeyen AI bağlantı testi |
| `POST /projects/{id}/ai/explanations` | Seçilmiş analiz verilerinin AI ile açıklanması |

Proje oluşturma ve iş durumunu sorgulama örneği; adresi erişebildiğiniz herkese açık bir depoyla değiştirin:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/projects \
  -H 'Content-Type: application/json' \
  -d '{"repository_url":"https://github.com/SAHIP/DEPO","branch":"main"}'
curl http://127.0.0.1:8000/api/v1/jobs/IS_ID
curl http://127.0.0.1:8000/api/v1/health
curl -X DELETE http://127.0.0.1:8000/api/v1/projects/PROJE_ID
```

Oluşturma ucu hemen yanıt verir; dönen `job_url` üzerinden tamamlanmayı izleyin. Olmayan proje silinirse 404, kuyruğa alınmış veya çalışan analizi varken silinirse `409 project_analysis_active` döner.

## Testleri çalıştırma

Depo kökünden varsayılan test çalıştırması, veritabanına dokunan testlerde birbirinden yalıtılmış geçici SQLite dosyaları kullanır:

```sh
PYTHONPATH=backend/src python -m pytest backend/tests -p no:cacheprovider
```

PowerShell'de:

```powershell
$env:PYTHONPATH = 'backend/src'
python -m pytest backend/tests -p no:cacheprovider
```

PostgreSQL testlerini de çalıştırmak için adı `_test` ile biten, silinebilir ayrı bir veritabanı oluşturun. `TEST_DATABASE_URL` ile bunu seçin; `DATABASE_URL` test hedefi seçiminde kullanılmaz.

```sh
TEST_DATABASE_URL='postgresql+psycopg://projectlens:YEREL_PAROLANIZ@localhost:5432/projectlens_test' \
  PYTHONPATH=backend/src python -m pytest backend/tests -p no:cacheprovider
```

PowerShell'de önce `$env:TEST_DATABASE_URL` ve `$env:PYTHONPATH` ayarlayın, ardından aynı pytest komutunu çalıştırın. Test fixture'ı her veritabanı testinden önce ve sonra hedef test veritabanının şemasını temizler; veritabanı adının `_test` ile bitmesini zorunlu tutar. Geliştirme ya da gerçek verilerinizin olduğu veritabanını kullanmayın.

AI testleri ağ taşımasını taklit eder; gerçek sağlayıcıya bağlanmaz ve gerçek anahtar gerektirmez. İstek şekli, hata eşleme, başlık doğrulaması, ortam ayarlarına dönüş ve anahtarların yanıt/loglarda görünmemesi test edilir. `FakeProvider` ile mevcut deterministik testler de kullanılabilir.

Web arayüzü testleri ve derlemesi:

```sh
cd frontend
npm test
npm run build
```

Frontend testleri Vitest, jsdom ve Testing Library kullanır.

## Kapsam ve sınırlar

- Python ve Dart dosyaları semboller, import/direktif kayıtları ve yorum işaretleri için ayrıştırılır. Dart desteği standart kütüphaneyle yazılmış küçük bir lexer kullanır; tipleri çözmez.
- Python importları ve Dart'ın göreli/yerel `package:` direktifleri ortak bağımlılık grafiğine katılır. Dart paket çözümlemesi yalnızca yerel pubspec adlarını kullanır; bilinmeyen paketler dış bağımlılık sayılır. Paket yöneticisi veya depo kodu çalıştırılmaz.
- Dosya sınıfları sezgisel olarak belirlenir. `.gitignore` uygulanmaz; yerleşik dışlanan dizinler ve açık tarayıcı dışlamaları geçerlidir.
- LOC fiziksel satır sayısıdır; boş satırlar ve yorumlar dahildir.
- Framework tespiti manifest'te tanımlı, tanınan bağımlılıkları raporlar; kodda gerçekten kullanıldıkları anlamına gelmez. Kaynak–test eşleşmeleri çözülmüş importlar ve ad/yol benzerliğine dayanır; test kapsamını veya testlerin geçtiğini göstermez.
- Sağlık ve risk göstergeleri statik sezgisellere dayanır. Eksik veriler hesaplanamayan bileşenler olarak görünür; eski snapshot'lar yeni metrikleri içermeyebilir.
- API, veritabanı, görev takibi, AI ve web arayüzü analiz çekirdeğinin üstündeki ayrı katmanlardır. API için `app` bağımlılık grubu gerekir. AI ile onboarding ve görev önerileri henüz plan aşamasındadır.
- Depo kodu hiçbir zaman import edilmez veya çalıştırılmaz.
- ProjectLens JSON çıktıları `projectlens_format` işareti taşır. Tarama boyut sınırına uyan mevcut işaretli JSON'lar dışlanıp `Excluded` olarak raporlanır. O çalıştırmanın tam `--output` yolu da taranan dizinin içinde olsa bile dışlanır.

## Projenin durumu

Yerel analiz çekirdeği; herkese açık GitHub depoları için analiz işleri; kalıcılık ve API; görev/yol haritası takibi; kabul kriterlerine dayalı değerlendirmeler; Python/Dart genişletmeleri; isteğe bağlı AI açıklamaları ve React web arayüzü uygulanmıştır. PostgreSQL testleri, CI akışı ve Docker Compose kurulumu belgelenmiştir; Compose daha önce yerel ortamda doğrulanmıştır.

AI ile onboarding/görev önerileri, özel depolar ve ek entegrasyonlar planlanan işler arasındadır. Yapılacaklar [TODO.md](TODO.md), analiz/API sözleşmeleri [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) içindedir.

## Güvenlik notları

Henüz kimlik doğrulama yoktur. API'yi ve web arayüzünü localhost üzerinde çalıştırın, internete açmayın. API'ye ulaşabilen biri proje silebilir ve analiz başlatabilir. Uyumlu AI sunucu adresleri yerel modeller için localhost/LAN erişimine bilerek izin verir; bu adreslere isteği tarayıcı değil backend yapar.

Yalnızca herkese açık HTTPS GitHub depoları kabul edilir; özel depo kimlik doğrulaması henüz yoktur. Depo kodu çalıştırılmaz. Veritabanı parolalarını ve sağlayıcı anahtarlarını sürüm kontrolünden uzak tutun. Tarayıcıdan gelen AI anahtarları sunucuda saklanmaz. Harici proxy ve gözlemleme araçlarında başlık kaydını/HTTP debug çıktısını kapalı tutun; localhost dışına anahtar gönderirken HTTPS kullanın.

AI açıklamaları isteğe bağlıdır ve doğrulanmalıdır. Kaynak kod gönderilmese bile dosya adları ve analiz metadatası hassas olabilir; istekte bulunmadan önce seçtiğiniz sağlayıcının veri politikasını değerlendirin.
