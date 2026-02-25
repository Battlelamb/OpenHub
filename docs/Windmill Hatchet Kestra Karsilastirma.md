# Windmill vs Hatchet vs Kestra — Detaylı Karşılaştırma Raporu

## Özet

Bu rapor, workflow orchestration ve backend otomasyon alanındaki üç öne çıkan açık kaynak aracı — Windmill, Hatchet ve Kestra — derinlemesine incelemektedir. Her biri farklı bir felsefeden yola çıkar: Windmill script-first performansa, Hatchet PostgreSQL-native AI agent pipeline'larına, Kestra ise YAML-declarative geniş ekosistem entegrasyonuna odaklanır. Rapor; mimari, performans, dil desteği, CLI/DevOps, deployment, lisanslama, fiyatlandırma ve OpenHub benzeri agent orchestration senaryoları açısından her aracı bağımsız olarak değerlendirir.

***

# BÖLÜM 1: WINDMILL

## 1.1 Genel Bakış

Windmill, Rust ile yazılmış açık kaynaklı bir workflow engine ve developer platformudur. Script'leri webhook'lara, workflow'lara ve UI'lara dönüştürür. Airflow'dan 13 kat daha hızlı olduğunu iddia eder. TypeScript, Python, Go, PHP, Bash, C#, SQL, Rust ve herhangi bir Docker image destekler.[^1][^2][^3]

Temel bileşenleri:
- **Execution runtime** — Worker fleet üzerinde düşük gecikmeli fonksiyon çalıştırma
- **Orchestrator** — Low-code builder veya YAML ile flow oluşturma
- **Low-code app editor** — Drag-and-drop dashboard'lar
- **Full-code app builder** — React/Svelte frontend'ler Windmill backend'ine bağlanır

[^2]

## 1.2 Mimari ve Performans

### Rust Core

Windmill'in backend'i tamamen Rust ile yazılmıştır. Bu seçim özellikle scheduler performansında büyük fark yaratır — tokio runtime ile work-stealing scheduler, PostgreSQL LISTEN/NOTIFY ile zero-copy mesaj geçişi sağlar. Idle durumda ~287MB bellek tüketir (Rust core + PostgreSQL), bu n8n'in ~516MB'sine ve Temporal'ın ~832MB'sine kıyasla oldukça düşüktür.[^4]

### Worker Mimarisi

Worker'lar otonom process'lerdir, her biri aynı anda tek bir job çalıştırır ve tüm CPU/belleği kullanır. Bu tasarımın avantajları:[^5]

- Yatay ölçekleme: worker ekle = throughput artar, overhead yok
- Her worker ayda 26 milyon job çalıştırabilir (100ms/job bazında)[^5]
- Worker'lar sadece bir database URL'i gerektirir — ayrı VPC'lerde bile çalışabilir[^5]
- Worker grupları ile priority queue'lar oluşturulabilir (high-priority, default, low-priority)[^6]

### Benchmark Sonuçları

| Metrik | Değer | Kaynak |
|--------|-------|--------|
| Job overhead (queue → start → result) | ~50ms | [^1] |
| Hafif Deno job toplam süresi | ~100ms | [^1] |
| Flow orchestration overhead | Sub-20ms | [^7] |
| 100 worker'a kadar lineer ölçeklenme | Doğrulanmış | [^8] |
| 100 worker throughput (100ms job) | 981 job/s | [^8] |
| 100 eşzamanlı workflow altında bellek | ~150MB sabit (orchestrator) | [^4] |
| PostgreSQL yazma (workflow başına) | ~5-10 write | [^4] |

Windmill, ağ bölünmesi (network partition) durumunda read-only moda geçer, kuyruktaki job'lar bekler, yeni gönderimler HTTP 503 ile reddedilir — bağlantı geri geldiğinde graceful recovery gerçekleşir.[^4]

## 1.3 CLI ve Git Entegrasyonu

Windmill CLI (`wmill`) Node.js 20+ gerektirir ve npm ile global kurulur. Temel yetenekler:[^9]

- **Workspace sync** — Klasörleri ve GitHub repo'larını workspace ile senkronize eder[^10]
- **Script/flow çalıştırma** — Terminal'den doğrudan script ve flow çalıştırma[^9]
- **Git Sync** — Workspace değişiklikleri otomatik olarak Git'e push edilebilir; doğrudan main'e push veya PR oluşturma desteklenir[^11]
- **Branch-specific items** — Ortama özel konfigürasyonlar (staging/production)[^10]
- **CI/CD entegrasyonu** — GitOps-style deployment, Git-based CI/CD pipeline'ları ile tam uyumlu[^10]

VS Code ve JetBrains IDE'ler için extension'lar mevcuttur, local development ile workspace arasında otomatik senkronizasyon sağlar.[^10]

## 1.4 Dil Desteği

| Dil | Durum |
|-----|-------|
| TypeScript (Deno/Bun) | ✅ Tam destek |
| Python | ✅ Tam destek (dedicated worker'lar ile cold-start eliminasyonu)[^12] |
| Go | ✅ Tam destek |
| PHP | ✅ Desteklenir |
| Bash | ✅ Desteklenir |
| C# | ✅ Desteklenir |
| SQL | ✅ Desteklenir |
| Rust | ✅ Desteklenir |
| Docker image | ✅ Herhangi bir image çalıştırılabilir |

[^2]

## 1.5 Lisans ve Fiyatlandırma

| Plan | Fiyat | Özellikler |
|------|-------|------------|
| Free & Open-source (Self-host) | $0 | Sınırsız execution, max 50 kullanıcı, 3 workspace, Docker/K8s deployment[^13] |
| Enterprise Self-host | $120/ay'dan başlayan | Audit log, SAML/SCIM, autoscaling, priority queue, worker group yönetim UI, concurrency limit[^13] |
| Enterprise Cloud | $170/ay'dan başlayan | Developer $20/ay + Operator $10/ay ek maliyet[^13] |
| AWS Marketplace | $440-$4,400/ay | Basic (10 seat, 4 CU) ile Large (100 seat, 40 CU) arası[^14] |

**Lisans: AGPLv3** — Açık kaynak ama ticari kullanımda dikkat gerektirir. Enterprise Edition için `windmill-ee` image kullanılır. Non-profit ve üniversitelere %60 indirim uygulanır.[^15][^13]

## 1.6 Güçlü ve Zayıf Yönler

**Güçlü yönler:**
- Kanıtlanmış Rust performansı — benchmark'lar halka açık ve doğrulanabilir[^8]
- 20+ dil desteği ve Docker image çalıştırma esnekliği[^2]
- PostgreSQL-only bağımlılık — Redis gerekmez[^4]
- Mature CLI + Git Sync + VS Code entegrasyonu[^10]
- Worker izolasyonu ve auto-scaling[^6]

**Zayıf yönler:**
- AGPLv3 lisansı ticari embedded kullanımda kısıtlayıcı olabilir
- Enterprise özellikler (autoscaling, concurrency limit, priority) ücretli planda[^13]
- Topluluk Temporal/Airflow'a kıyasla daha küçük[^16]

***

# BÖLÜM 2: HATCHET

## 2.1 Genel Bakış

Hatchet, PostgreSQL üzerine inşa edilmiş modern bir task orchestration platformudur. Mühendislik ekiplerinin düşük gecikmeli, yüksek throughput'lu veri ingestion ve agentic AI pipeline'ları kurmasına yardımcı olur. 100% MIT lisanslıdır. Ayda 1 milyardan fazla task işler ve 10.000'den fazla self-host deployment'ı vardır.[^17][^18]

Hatchet'ın temel felsefesi: fonksiyonlar (task'lar) yazılır, worker'larda çalıştırılır, DAG veya parent/child ilişkileri ile workflow'lar oluşturulur — hepsi code-first.[^18]

## 2.2 Mimari ve Performans

### PostgreSQL-Native Tasarım

Hatchet'ın tüm altyapısı PostgreSQL üzerine kuruludur. Bu kararın 5 temel nedeni:[^19]

1. **Operasyonel basitlik** — Tek bir veritabanı izle, yedekle, ölçekle
2. **ACID garantileri** — Task state transition'ları atomik
3. **Query esnekliği** — Task verisi ile kullanıcı verisini join'le, analitik yap
4. **Kanıtlanmış ölçeklenme** — Günde 100+ milyon task PostgreSQL üzerinde
5. **Kolay deployment** — Self-host için sadece PostgreSQL yeterli

### v1 Engine Yenilikleri

Hatchet v1, tam bir engine rewrite'ı ile geldi — yine PostgreSQL üzerine:[^20]

- **DAG-based workflow'lar** — Sleep condition, event-based triggering, parent output'una göre conditional execution
- **Durable execution** — Fonksiyonların failure'dan kurtulması: intermediate result'lar cache'lenir ve retry'da otomatik replay yapılır. Durable sleep ve durable event desteği
- **Queue özellikleri** — Key-based concurrency queue (fair queueing), rate limiting, sticky assignment, worker affinity
- **Performans iyileştirmeleri** — Range-based partitioning, hash-based partitioning, monitoring/queue tablo ayrımı, buffered read/write, identity column'lar, agresif PostgreSQL trigger kullanımı

RabbitMQ artık zorunlu bağımlılık değil — basit workload'lar için sadece PostgreSQL yeterli. Yüksek throughput deployment'lar için opsiyonel olarak kullanılabilir.[^20]

### Performans Metrikleri

| Metrik | Değer | Kaynak |
|--------|-------|--------|
| Task dispatch latency (hot worker) | Sub-25ms | [^18] |
| Eşzamanlı task kapasitesi | 1000'ler | [^18] |
| Günlük task işleme (production) | 20.000+/dakika (>1B/ay) | [^20] |
| Peak burst | 5.000+ task/s (≈25K tx/s) | [^20] |
| PostgreSQL write (task başına) | ~5 transaction minimum | [^20] |
| Basit workload bağımlılık | Sadece PostgreSQL | [^18] |

## 2.3 SDK ve Dil Desteği

Hatchet, Python, TypeScript ve Go olmak üzere üç dilde SDK sunar. Worker'lar kendi altyapınızda çalışır. gRPC üzerinden Hatchet engine ile iletişim kurar.[^18]

**Python SDK örneği:**
```python
@hatchet.workflow(name="first-workflow", on_events=["user:create"])
class MyWorkflow:
    @hatchet.step()
    def step1(self, context):
        return {"result": "success"}
```

**TypeScript SDK örneği:**
```typescript
const workflow: Workflow = {
  id: "first-typescript-workflow",
  on: { event: "user:create" },
  steps: [...]
};
```



Python SDK'sı v1 ile birlikte first-class Pydantic desteği sunuyor — bu, Celery'den geçenler için önemli bir type-safety avantajı.[^20]

## 2.4 Deployment

### Self-Hosted (Docker Compose)

Hatchet'ın self-hosted deployment'ı şu servislerden oluşur:[^21]

| Servis | Açıklama |
|--------|----------|
| `postgres` | PostgreSQL 15.6 (zorunlu, tek bağımlılık) |
| `rabbitmq` | Opsiyonel — yüksek throughput için internal messaging |
| `hatchet-engine` | Core orchestration engine |
| `hatchet-api` | REST API servisi |
| `hatchet-frontend` | Dashboard UI |
| `caddy` | Reverse proxy |
| `hatchet-migrate` | Database migration |

Basitleştirilmiş deployment için `hatchet-lite` image'ı tüm internal servisleri tek bir binary'de birleştirir.[^20]

### Cloud

Hatchet Cloud managed hosting sunar. Self-host ile Cloud arasındaki tek fark: Cloud'da managed worker'lar mevcut — core engine ve API aynı.[^17]

## 2.5 Fiyatlandırma

| Plan | Fiyat | Öne Çıkanlar |
|------|-------|--------------|
| Free (Cloud) | $0/ay | 2K task/gün, 1 worker, test ve küçük ölçek[^22] |
| Starter (Cloud) | $180/ay | 20K task/gün, 50 worker, 3 kullanıcı[^22] |
| Growth (Cloud) | $425/ay | 100K task/gün, 200 worker, 10 kullanıcı, 7 gün retention[^22] |
| Self-Host Support (Essential) | $500/ay | 2 iş günü SLA, Slack channel[^22] |
| Self-Host Support (Enterprise) | $2,000/ay | 1 iş günü SLA, monthly office hours, advanced guidance[^22] |
| Custom | İletişim | SOC2/HIPAA/BAA, özel limit'ler[^22] |

**Lisans: 100% MIT** — Self-host tamamen ücretsiz, hiçbir özellik kısıtlaması yok. Cloud ile birebir aynı engine çalışır.[^17]

## 2.6 Güçlü ve Zayıf Yönler

**Güçlü yönler:**
- MIT lisansı — tam açık kaynak, ticari kullanımda sıfır kısıtlama[^17]
- PostgreSQL-only bağımlılık — operasyonel basitlik[^19]
- Durable execution — Temporal benzeri replay mekanizması[^20]
- AI agent pipeline'ları için özel olarak tasarlanmış (webhooks, child spawning, dynamic workflow)[^18]
- Sub-25ms task dispatch[^18]
- Python + TypeScript + Go SDK'ları

**Zayıf yönler:**
- Visual workflow builder yok — tamamen code-first, DAG görüntüleme mevcut ama düzenleme için no-code editör yok[^20]
- Dil desteği 3 dil ile sınırlı (Python, TS, Go) — Windmill'in 20+ diline kıyasla dar
- PostgreSQL yüksek hacimde sorunlu olabilir — her task minimum 5 transaction, 25K tx/s'de ciddi optimizasyon gerekti[^20]
- Hâlâ genç ekosistem — entegrasyon sayısı Kestra veya n8n ile karşılaştırılamaz

***

# BÖLÜM 3: KESTRA

## 3.1 Genel Bakış

Kestra, Apache 2.0 lisanslı, event-driven bir declarative orchestration platformudur. Java ile yazılmıştır (Java %71.9, Vue %18.7). GitHub'da **26.3K yıldız**, 2.5K fork ve 425 contributor ile bu üçlü arasında en büyük topluluğa sahiptir. v1.2.0 sürümü Ocak 2026'da yayınlanmıştır — 384 release ile oldukça olgun.[^23]

Temel felsefesi: **Infrastructure as Code prensiplerini tüm workflow'lara taşımak** — YAML ile declarative tanımlama, UI'dan veya API'den yapılan değişiklikler otomatik olarak YAML'a yansır.[^23]

## 3.2 YAML-Declarative Paradigma

Kestra'da her workflow tek bir YAML dosyası ile tanımlanır:[^24]

```yaml
id: hello_world
namespace: dev
tasks:
  - id: say_hello
    type: io.kestra.plugin.core.log.Log
    message: "Hello, World!"
```

Bu yaklaşımın avantajları:[^24]
- **Kolay öğrenme** — YAML syntax'ı basit, teknik olmayan ekip üyeleri de workflow oluşturabilir
- **Built-in syntax validation** — Hata execution öncesi yakalanır
- **Platform bağımsızlık** — Orchestration mantığı iş mantığından ayrı, mevcut koda dokunmadan orchestrate edilir
- **Azaltılmış bakım** — YAML düzenle, CI/CD gereksiz
- **Versiyon kontrolü** — Tek dosya = kolay Git takibi, PR review, rollback

YAML tanımı UI'dan veya API'den değiştirilse bile her zaman code olarak yönetilir.[^25][^23]

## 3.3 Plugin Ekosistemi

Kestra'nın en güçlü yanlarından biri **1100+ plugin** ekosistemidir. Bu plugin'ler:[^24]

- **Veritabanları** — PostgreSQL, MySQL, MongoDB, Snowflake, BigQuery ve daha fazlası
- **Cloud servisleri** — AWS (S3, Lambda, SQS, Batch), Google Cloud (GCS, Pub/Sub, BigQuery), Azure (Blob, Event Hubs)
- **Mesaj kuyrukları** — Kafka, Redis, Pulsar, AMQP, MQTT, NATS, AWS SQS, Google Pub/Sub
- **Infrastructure as Code** — Terraform ve Ansible CLI plugin'leri[^26]
- **Script dilleri** — Python, Node.js, R, Go, Shell ve daha fazlası
- **Monitoring** — Slack, email, PagerDuty notifikasyonları
- **Docker & Kubernetes** — Container ve K8s job çalıştırma

Custom plugin geliştirme de desteklenir.[^23]

## 3.4 Mimari

### Bileşenler

Kestra şu temel bileşenlerden oluşur:[^23]

- **Flows** — Core iş birimi, task'lardan oluşan workflow
- **Tasks** — Script çalıştırma, veri taşıma, API çağrısı gibi tekil iş birimleri
- **Namespaces** — Flow'ların mantıksal gruplandırması ve izolasyonu
- **Triggers** — Schedule veya event bazlı flow başlatma
- **Inputs & Variables** — Flow ve task'lara geçirilen parametreler

### Dayanıklılık Özellikleri

Kestra, production-grade dayanıklılık için şunları sunar:[^23]
- Namespace'ler, label'lar, subflow'lar
- Retry mekanizmaları ve timeout'lar
- Error handling
- Conditional branching
- Parallel ve sequential task execution
- Backfill desteği
- Dynamic task'lar

### Ölçeklenebilirlik

Kestra, milyonlarca workflow işlemek üzere tasarlanmıştır — yüksek erişilebilirlik ve hata toleransı ile. Task Runner'lar ile script'ler local, remote (SSH), serverless container veya Docker/Kubernetes üzerinde çalıştırılabilir.[^23]

## 3.5 CLI, Terraform ve DevOps

Kestra, Infrastructure as Code yaklaşımını destekleyen güçlü DevOps araçlarına sahiptir:[^23]

- **Git entegrasyonu** — Flow'lar Git repo'sunda saklanabilir, built-in editor'dan doğrudan Git branch'ine push
- **CI/CD** — Flow deployment'ı CI/CD pipeline'ları ile otomatize edilir
- **Terraform Provider** — Resmi Terraform provider ile Kestra kaynakları yönetilir[^23]
- **REST API** — API-first felsefe, tüm işlemler API üzerinden yapılabilir[^25]
- **Kestra CLI** — Komut satırından flow yönetimi ve execution

### Terraform Örneği

Kestra'nın Terraform plugin'i ile doğrudan workflow içinden infrastructure yönetimi yapılabilir — S3 bucket oluşturma, Kubernetes resource provisioning gibi.[^26]

## 3.6 Deployment

### Lokal (Docker)

Tek komut ile başlatılır:[^23]

```bash
docker run --pull=always --rm -it -p 8080:8080 --user=root \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /tmp:/tmp kestra/kestra:latest server local
```

### Cloud Deployment

| Platform | Yöntem |
|----------|--------|
| AWS | CloudFormation template |
| Google Cloud | Terraform module |
| Railway | Otomatik Docker deployment (~$5-10/ay)[^27] |
| Kubernetes | Helm chart |
| Docker Compose | Production-ready konfigürasyon |

[^23]

## 3.7 Lisans ve Fiyatlandırma

| Plan | Fiyat | Özellikler |
|------|-------|------------|
| Open-Source | Ücretsiz | Sınırsız kullanıcı, workflow oluşturma/çalıştırma, multi-cloud/on-prem, code editor, tüm plugin'ler, Git entegrasyonu[^28] |
| Enterprise | Instance başına (custom) | Task Runner'lar, service account/API token, dedicated storage, tenant isolation, cluster monitoring, high-throughput event handling[^28] |
| Kestra Cloud | Custom | Managed hosting, otomatik scaling, enterprise destek[^27] |

**Lisans: Apache 2.0** — Tam açık kaynak, ticari kullanımda hiçbir kısıtlama yok.[^23]

## 3.8 Güçlü ve Zayıf Yönler

**Güçlü yönler:**
- En büyük topluluk (26.3K star, 425 contributor) ve en olgun proje (384 release, v1.2.0)[^23]
- 1100+ plugin — en geniş entegrasyon ekosistemi[^24]
- Apache 2.0 lisansı — ticari kullanımda tam serbestlik[^23]
- YAML-declarative — teknik olmayan ekip üyeleri de workflow oluşturabilir[^24]
- Terraform Provider ile IaC entegrasyonu[^23]
- Real-time event trigger'lar (Kafka, Redis, SQS, Pub/Sub vb.)[^23]

**Zayıf yönler:**
- Java tabanlı — JVM overhead'i ve bellek tüketimi Rust-based Windmill'e kıyasla daha yüksek
- YAML-only paradigma — karmaşık iş mantığı YAML'da kısıtlayıcı olabilir; code-first yaklaşım Windmill/Hatchet kadar doğal değil
- AI agent orchestration için özel feature'lar yok — Hatchet'ın child spawning, dynamic workflow gibi agent-specific primitive'lerine sahip değil
- Sub-20ms overhead garantisi yok — performans benchmark'ları Windmill kadar detaylı yayınlanmamış

***

# KARŞILAŞTIRMA

## Ana Özellikler

| Kriter | Windmill | Hatchet | Kestra |
|--------|----------|---------|--------|
| **Temel Paradigma** | Script-first, polyglot | Code-first, task-centric | YAML-declarative |
| **Core Dili** | Rust[^4] | Go[^20] | Java[^23] |
| **Lisans** | AGPLv3[^13] | MIT[^17] | Apache 2.0[^23] |
| **GitHub Stars** | ~10K | ~5K | 26.3K[^23] |
| **Dil Desteği** | 20+ dil + Docker[^2] | Python, TS, Go[^18] | Any (plugin bazlı)[^23] |
| **Plugin/Entegrasyon** | 100+ (Hub)[^7] | SDK-based (gRPC) | 1100+[^24] |
| **Visual UI** | Web IDE + flow builder[^2] | Dashboard (monitoring)[^20] | YAML editor + topology view[^23] |
| **CLI** | `wmill` (npm)[^9] | `hatchet` CLI | `kestra` CLI + Terraform[^23] |
| **Git Entegrasyonu** | Native Git Sync + CI/CD[^10] | Workflow-as-code (Git doğal)[^18] | Built-in Git push + CI/CD[^23] |

## Performans ve Ölçeklenme

| Kriter | Windmill | Hatchet | Kestra |
|--------|----------|---------|--------|
| **Orchestration Overhead** | Sub-20ms[^7] | Sub-25ms[^18] | Belirtilmemiş |
| **Job Start Latency** | ~50ms[^1] | 25ms[^18] | 5-30s (Airflow benzeri)[^18] |
| **Idle Bellek** | ~287MB[^4] | PostgreSQL + engine | JVM bazlı (daha yüksek) |
| **DB Bağımlılığı** | PostgreSQL only[^4] | PostgreSQL only[^19] | PostgreSQL/MySQL + opsiyonel Kafka/Elasticsearch |
| **Max Throughput (kanıtlanmış)** | 981 job/s (100 worker)[^8] | 5K+ task/s, >1B/ay[^20] | Milyonlarca workflow (claim)[^23] |
| **Worker Modeli** | 1 job/worker, horizontal scale[^5] | Concurrent task per worker[^20] | Task Runner (Docker/K8s) |
| **Crash Recovery** | DB checkpoint, <5s[^4] | Durable execution replay[^20] | Retry + error handling[^23] |

## Deployment Karmaşıklığı

| Kriter | Windmill | Hatchet | Kestra |
|--------|----------|---------|--------|
| **Minimum Bağımlılık** | PostgreSQL | PostgreSQL | Docker |
| **Docker Compose** | ✅ (~3 dk)[^16] | ✅ (6+ servis)[^21] | ✅ (tek komut)[^23] |
| **Kubernetes** | ✅ Helm chart | ✅ Helm chart[^20] | ✅ Helm chart[^23] |
| **Managed Cloud** | Windmill Cloud[^7] | Hatchet Cloud[^22] | Kestra Cloud[^27] |
| **Self-host Kolaylığı** | Kolay (PG-only)[^4] | Kolay (PG-only, lite mode)[^20] | Çok kolay (tek docker run)[^23] |

## OpenHub Agent Orchestration Uygunluğu

| Senaryo | Windmill | Hatchet | Kestra |
|---------|----------|---------|--------|
| **Python + TS aynı pipeline** | ✅ Native polyglot[^2] | ✅ SDK bazlı[^18] | ✅ Plugin bazlı[^23] |
| **AI agent pipeline'ları** | ⚠️ Script bazlı, özel feature yok | ✅ Durable exec + child spawn + webhooks[^18] | ⚠️ Genel orchestration, agent-specific yok |
| **High-throughput task queue** | ✅ Kanıtlanmış lineer ölçeklenme[^8] | ✅ >1B task/ay[^20] | ✅ Ölçeklenebilir ama benchmark yok |
| **CLI + Git workflow** | ✅ En iyi (wmill + Git Sync + VS Code)[^10] | ⚠️ Code-first ama CLI sınırlı | ✅ İyi (CLI + Terraform + Git)[^23] |
| **Durable long-running workflow** | ✅ İyi (DB checkpoint)[^4] | ✅ En iyi (Temporal-style replay)[^20] | ✅ İyi (retry + error handling)[^23] |
| **Entegrasyon genişliği** | Orta (100+) | Düşük (SDK bazlı) | ✅ En geniş (1100+ plugin)[^24] |
| **Lisans esnekliği** | ⚠️ AGPLv3 kısıtlayıcı | ✅ MIT — en serbest[^17] | ✅ Apache 2.0 — serbest[^23] |

## Karar Matrisi

| Öncelik | Öneri |
|---------|-------|
| **Performans + polyglot + CLI/Git** → | **Windmill** — Rust core, 20+ dil, kanıtlanmış benchmark'lar, en olgun CLI/Git entegrasyonu[^7][^8] |
| **AI agent pipeline + MIT lisans + durable execution** → | **Hatchet** — Agent-specific primitive'ler, Temporal-style durability, PostgreSQL-only basitlik[^18][^20] |
| **Geniş entegrasyon + YAML IaC + en büyük topluluk** → | **Kestra** — 1100+ plugin, Apache 2.0, Terraform provider, en olgun ekosistem[^23][^24] |
| **Hepsini birleştir** → | Windmill (core execution) + Hatchet (durable AI agent pipeline'ları) veya Windmill + Kestra (geniş entegrasyon + execution performansı) |

---

## References

1. [windmill-labs/windmill: Open-source developer platform to ... - GitHub](https://github.com/windmill-labs/windmill) - Open-source developer platform to power your entire infra and turn scripts into webhooks, workflows ...

2. [What is Windmill? | Windmill](https://www.windmill.dev/docs/intro) - Whether compared to workflow engines like Temporal and Airflow or UI builders like Retool, Windmill ...

3. [Windmill Labs, Inc - GitHub](https://github.com/windmill-labs) - Open-source developer platform to power your entire infra and turn scripts into webhooks, workflows ...

4. [n8n vs Windmill vs Temporal for Self-Hosting - arcbjorn](https://blog.arcbjorn.com/workflow-automation) - This analysis compares three fundamentally different orchestration approaches for 1-2 server deploym...

5. [Workers and worker groups - Windmill](https://www.windmill.dev/docs/core_concepts/worker_groups) - They are at the basis of Windmill's architecture as run the jobs. The number of workers can be horiz...

6. [Scaling workers - Windmill](https://www.windmill.dev/docs/advanced/scaling) - Scaling workers. Windmill uses a worker queue architecture where workers pull jobs from a shared que...

7. [Windmill | Build, deploy and monitor internal software at scale](https://www.windmill.dev) - Open-source workflow engine to build workflows, data pipelines and internal tools at scale. Self-hos...

8. [Scaling Windmill workers](https://www.windmill.dev/docs/misc/benchmarks/competitors/results/scaling) - Windmill scales linearly with the number of workers (at least up to 100 workers). We can also notice...

9. [Command-line interface (CLI) - Windmill](https://www.windmill.dev/docs/advanced/cli) - How do I use the Windmill CLI? Sync, deploy and manage scripts, flows, apps and resources from your ...

10. [Development Tools and Workflow | windmill-labs/windmilldocs ...](https://deepwiki.com/windmill-labs/windmilldocs/4-development-tools-and-workflow) - This document covers Windmill's comprehensive development ecosystem, including command-line interfac...

11. [Windmill.dev Demo - Local Development](https://www.youtube.com/watch?v=sxNW_6J4RG8) - 00:00 Introduction
00:15 Windmill CLI
00:41 VS Code Extension
01:35 Git Sync
02:18 Conclusion

12. [What is Windmill? - tools.dev](https://blog.boldtech.dev/what-is-windmill-dev/) - Windmill is a script-driven, open-source workflow engine and app development platform designed to he...

13. [Pricing](https://www.windmill.dev/pricing) - Windmill pricing based on compute units. Free Community Edition, Team and Enterprise plans available...

14. [AWS Marketplace: Windmill EE Self-Hosted (helm) - Amazon.com](https://aws.amazon.com/marketplace/pp/prodview-gojmh6g2hrdzo) - Windmill is an open-source developer platform and workflow engine designed to turn scripts into auto...

15. [Plans & How to upgrade - Windmill](https://www.windmill.dev/docs/misc/plans_details) - What are Windmill's pricing plans? Free, Team and Enterprise tiers for cloud and self-hosted deploym...

16. [Top 10 Open-Source Tools for Workflow Automation](https://www.usecollect.com/blog/top-10-open-source-tools-for-workflow-automation) - By 2025, over 3,000 organizations have adopted this platform, drawn to its robust performance and hi...

17. [Show HN: Hatchet – Open-source distributed task queue](https://news.ycombinator.com/item?id=39643136) - Everything we've built so far has been 100% MIT licensed. We'd like to keep it that way and make mon...

18. [Hatchet Documentation: What is Hatchet?](https://docs.hatchet.run) - Hatchet is a modern orchestration platform that helps engineering teams build low-latency and high-t...

19. [Alexander Belanger's Post](https://www.linkedin.com/posts/alexander-belanger-aa3974135_5-reasons-we-built-hatchets-core-on-postgresql-activity-7374427733038358528-pDj5) - 5 reasons we built Hatchet's core on PostgreSQL instead of specialized queue systems: 1. Operational...

20. [Show HN: Hatchet v1 – A task orchestration platform built on Postgres](https://news.ycombinator.com/item?id=43572733) - We're building an open-source platform for managing background tasks, using Postgres as the underlyi...

21. [Docker Compose](https://v0-docs.hatchet.run/self-hosting/docker-compose)

22. [Hatchet Cloud Reviews and Pricing 2025](https://www.f6s.com/software/hatchet-cloud) - Hatchet Cloud reviews, pricing and more with discounts and Distributed Work Queue alternatives. Hatc...

23. [kestra-io/kestra: Event Driven Orchestration & Scheduling ...](https://github.com/kestra-io/kestra) - Kestra is an open-source, event-driven orchestration platform that makes both scheduled and event-dr...

24. [Declarative Orchestration with Kestra](https://kestra.io/features/declarative-data-orchestration) - Bring Infrastructure as Code Best Practices to All Workflows

25. [Kestra - Simon Späti](https://www.ssp.sh/brain/kestra/) - Built with an API-first philosophy, Kestra enables users to define and manage data pipelines through...

26. [How to Automate Infrastructure using Kestra, Ansible and Terraform](https://kestra.io/blogs/2024-04-16-infrastructure-orchestration-using-kestra) - Learn how to orchestrate infrastructure components using Kestra.

27. [Deploy Kestra [Updated Feb '26] - Railway](https://railway.com/deploy/kestra) - 5,0

28. [Compare all Versions of Kestra](https://3501b01f.kestra-io.pages.dev/pricing) - Choose the right plan for your needs. Start with the Open Source version and scale with the Enterpri...

