# Codex AgentHub Local (Root Projesi) Planı

## Özet

Bu plan, `d:\OneDrive\OLD\Documents\SkorAI` root altında **ortak bağlanılabilen local çok-agent koordinasyon sistemi** için yeni bir proje tasarlar.

Amaç:
- Birden çok model/agent’ın aynı görev havuzuna bağlanması
- Görev, mesaj, artifact ve state paylaşımı
- Çakışmasız çalışma (lock/lease)
- Audit/log/retry görünürlüğü
- Local/LAN erişilebilir MVP

Bu turda **sadece plan** hazırlanır (Plan Mode). Dosya oluşturma/yazma yapılmaz.

## Proje Adı ve Konumu (Varsayılan)

- Proje adı: `Codex_AgentHub_Local`
- Konum: `d:\OneDrive\OLD\Documents\SkorAI\Codex_AgentHub_Local`

## Kapsam (MVP)

### Dahil
- FastAPI tabanlı local orchestrator servis
- SQLite tabanlı state store
- Local artifact storage (`./data/artifacts`)
- REST API + SSE event stream
- Agent registration / heartbeat
- Task queue + claim/lease + retry
- Message/thread sistemi
- Resource locks (file/path bazlı)
- Audit/event log
- Basit web dashboard (read-only + aksiyon butonları)
- Docker çalıştırma (opsiyonel ama dahil)

### Hariç (Phase 2+)
- Redis / distributed queue
- OAuth/SSO
- Multi-host HA
- Full RBAC matrix
- Model provider abstraction routing engine
- Advanced policy engine / approvals workflow UI (temel approval endpoint hariç)

## Mimari (Karar Tamam)

### Bileşenler
1. **Orchestrator API**
   - FastAPI
   - REST endpoints
   - SSE stream (`/v1/events/stream`)
2. **Worker Runtime (agent client SDK)**
   - Python client library
   - Poll + heartbeat + complete/fail helper
3. **State Store**
   - SQLite (`./data/state/agenthub.db`)
4. **Artifact Store**
   - Local filesystem (`./data/artifacts`)
5. **Dashboard**
   - FastAPI static templates (server-rendered minimal UI)
6. **Background Jobs**
   - Lease expiry cleanup
   - Retry scheduler
   - Event retention cleanup

### Network
- Default bind: `0.0.0.0:7788` (LAN erişimi için)
- Auth: API key header (`X-AgentHub-Key`)
- TLS: MVP’de yok (reverse proxy ile eklenebilir)

## Teknoloji Seçimi (Sabit)

- Python `3.11+`
- FastAPI + Uvicorn
- Pydantic v2
- SQLite (`sqlite3` stdlib) + migration scripts (basit SQL dosyaları)
- Jinja2 templates (dashboard)
- pytest (unit/integration)
- httpx (API tests/client)
- filelock benzeri davranış DB lock tablosu ile (ek paket gereksiz)

## Dizin Yapısı (Uygulanacak)

```text
Codex_AgentHub_Local/
  README.md
  pyproject.toml
  .env.example
  docker-compose.yml
  Dockerfile
  .gitignore

  app/
    main.py
    config.py
    logging.py
    dependencies.py

    api/
      routes_health.py
      routes_agents.py
      routes_tasks.py
      routes_messages.py
      routes_artifacts.py
      routes_locks.py
      routes_events.py
      routes_admin.py
      schemas.py

    core/
      orchestrator.py
      scheduler.py
      lease_manager.py
      retry_manager.py
      event_bus.py
      auth.py
      capability_matcher.py

    db/
      sqlite.py
      schema.sql
      migrations/
        001_initial.sql
      repositories/
        agents_repo.py
        tasks_repo.py
        messages_repo.py
        artifacts_repo.py
        locks_repo.py
        events_repo.py

    storage/
      artifact_store.py
      checksum.py

    dashboard/
      views.py
      templates/
        index.html
        tasks.html
        task_detail.html
        agents.html
        events.html

    clients/
      python_sdk/
        __init__.py
        client.py
        models.py
        worker_loop.py

  scripts/
    run_dev.ps1
    init_db.py
    seed_demo.py

  data/
    .gitkeep
    state/
    artifacts/

  tests/
    test_health.py
    test_agents.py
    test_tasks_lifecycle.py
    test_task_claim_concurrency.py
    test_retries.py
    test_locks.py
    test_artifacts.py
    test_sse_events.py
```

## Public API / Interface Tasarımı (Karar Tamam)

### Auth
- Header: `X-AgentHub-Key: <token>`
- Role mapping:
  - `admin`
  - `agent`
  - `viewer`

## 1) Health
- `GET /v1/health`
  - Response: service status, db status, version

## 2) Agents
- `POST /v1/agents/register`
  - Input:
    - `agent_name`
    - `capabilities[]` (örn: `["python_edit", "review", "web_research"]`)
    - `labels` (kv)
  - Output:
    - `agent_id`
    - `lease_ttl_sec`
- `POST /v1/agents/{agent_id}/heartbeat`
  - Updates status + current task + last_seen
- `POST /v1/agents/{agent_id}/disconnect`
  - Soft offline

## 3) Tasks
Task states (sabit):
- `queued`
- `claimed`
- `running`
- `waiting_approval`
- `completed`
- `failed`
- `dead_letter`
- `cancelled`

Priority:
- `0..100` (0 highest)

Endpoints:
- `POST /v1/tasks`
  - Human/admin task oluşturur
  - Input:
    - `title`
    - `task_type`
    - `payload` (json)
    - `priority`
    - `required_capabilities[]`
    - `idempotency_key` (optional)
    - `max_retries` (default 2)
    - `deadline_at` (optional)
- `GET /v1/tasks/next`
  - Query:
    - `agent_id`
  - Returns best matching queued task (capability + priority)
- `POST /v1/tasks/{task_id}/claim`
  - Lease oluşturur (`lease_until`)
- `POST /v1/tasks/{task_id}/start`
- `POST /v1/tasks/{task_id}/heartbeat`
  - Progress %, note
- `POST /v1/tasks/{task_id}/complete`
  - Output refs: artifact ids, summary, result payload
- `POST /v1/tasks/{task_id}/fail`
  - Error payload + `retryable`
  - Retryable ise scheduler yeniden `queued` yapar
- `POST /v1/tasks/{task_id}/cancel`
- `POST /v1/tasks/{task_id}/request-approval`
  - approval message + risk flags

## 4) Messages / Threads
- `POST /v1/threads`
- `POST /v1/threads/{thread_id}/messages`
  - sender_type: `agent|human|system`
  - sender_id
  - message_type: `note|question|decision|handoff`
  - content
  - refs (task/artifact ids)
- `GET /v1/threads/{thread_id}/messages`

## 5) Artifacts
- `POST /v1/artifacts`
  - Multipart file upload veya JSON text artifact
  - Metadata:
    - `artifact_type` (`report`, `patch`, `log`, `plan`, `summary`)
    - `task_id`
    - `thread_id`
    - `visibility` (`public`, `restricted`)
- `GET /v1/artifacts/{artifact_id}`
- `GET /v1/artifacts/{artifact_id}/download`

## 6) Locks (Çakışma önleme)
- `POST /v1/locks/acquire`
  - `resource_key` (örn: `repo:SkorAI_Analysis:file:src/api/api_endpoints_admin.py`)
  - `owner_agent_id`
  - `ttl_sec`
- `POST /v1/locks/renew`
- `POST /v1/locks/release`
- `GET /v1/locks`

Lock semantics:
- Lease-based
- Expired lock başkası tarafından alınabilir
- Unique constraint + expiry kontrolü DB transaction içinde

## 7) Events / Audit
- `GET /v1/events`
  - filter by task/agent/type/time
- `GET /v1/events/stream` (SSE)
  - dashboard ve clients için live updates

## 8) Admin
- `GET /v1/admin/stats`
- `POST /v1/admin/requeue-stuck`
- `POST /v1/admin/retry-dead-letter/{task_id}`
- `POST /v1/admin/retention/run`
- `GET /v1/admin/config`

## Veri Modeli (SQLite) — Karar Tamam

### Tablolar
- `agents`
  - `id`, `name`, `status`, `capabilities_json`, `labels_json`, `last_seen_at`, `current_task_id`
- `tasks`
  - `id`, `title`, `task_type`, `state`, `priority`, `payload_json`, `required_capabilities_json`
  - `owner_agent_id`, `lease_until`, `retry_count`, `max_retries`
  - `idempotency_key`, `deadline_at`, `created_at`, `updated_at`
- `task_attempts`
  - per claim/run attempt logs
- `threads`
- `messages`
- `artifacts`
  - `id`, `task_id`, `thread_id`, `path`, `artifact_type`, `mime_type`, `size_bytes`, `sha256`
- `locks`
  - `resource_key` UNIQUE, `owner_agent_id`, `lease_until`
- `events`
  - append-only audit/event stream
- `approvals`
  - `task_id`, `status`, `requested_by`, `approved_by`, `reason`
- `api_keys`
  - hashed tokens + role + owner

### Indexler
- `tasks(state, priority, created_at)`
- `tasks(owner_agent_id)`
- `tasks(lease_until)`
- `events(created_at)`
- `messages(thread_id, created_at)`
- `locks(resource_key)`

## Görev Dağıtım ve Claim Algoritması (Net)

### Matching sırası
1. `state = queued`
2. Capability tam uyum (`required_capabilities` subset of agent capabilities)
3. `priority ASC`
4. `created_at ASC`

### Claim transaction
- `BEGIN IMMEDIATE`
- Uygun task seç
- `state -> claimed`
- `owner_agent_id`, `lease_until=now+TTL`
- `task_attempt` aç
- `events` kaydı
- `COMMIT`

### Lease expiry davranışı
- Background scheduler her 10 sn:
  - `claimed/running` ve `lease_until < now` taskları tarar
  - `retry_count < max_retries` ise `queued`
  - değilse `dead_letter`

## Retry Politikası (Karar Tamam)

- Default `max_retries = 2`
- Retry backoff:
  - `retry_count=1`: 5 sn
  - `retry_count=2`: 30 sn
  - Sonrası dead-letter
- Sadece `fail(retryable=true)` veya lease timeout durumunda retry
- `fail(retryable=false)` direkt `failed`
- Admin manual requeue mümkün

## Approval / Human-in-the-loop (MVP Minimal)

- Agent `request-approval` endpoint’i ile task’ı `waiting_approval` yapabilir
- Human/admin dashboard’dan:
  - approve -> `queued` veya `running` (task policy’ye göre)
  - reject -> `failed`
- Approval event’leri `events` ve `messages` içine yazılır

## Dashboard (MVP) — Kapsam

### Sayfalar
- `/` dashboard overview
- `/tasks`
- `/tasks/{id}`
- `/agents`
- `/events`
- `/locks`

### Özellikler
- filtreleme (state/priority/agent)
- stuck task görünümü
- manual requeue/cancel
- approval action
- live updates SSE

## Güvenlik (MVP Varsayılanlar)

- API key zorunlu (dev modda `ALLOW_ANON=false` default)
- Role checks:
  - `viewer`: read-only
  - `agent`: claim/run/message/artifact own actions
  - `admin`: full control
- Artifact path traversal koruması:
  - tüm artifact path’leri sistem tarafından üretilir
  - user path input kabul edilmez
- Request body size limiti
- Basic rate limit (IP + key) opsiyonel, default açık değil

## Konfigürasyon (ENV) — Net Liste

- `AGENTHUB_HOST=0.0.0.0`
- `AGENTHUB_PORT=7788`
- `AGENTHUB_DB_PATH=./data/state/agenthub.db`
- `AGENTHUB_ARTIFACT_DIR=./data/artifacts`
- `AGENTHUB_EVENT_RETENTION_DAYS=30`
- `AGENTHUB_MESSAGE_RETENTION_DAYS=90`
- `AGENTHUB_LOCK_SWEEP_INTERVAL_SEC=10`
- `AGENTHUB_TASK_LEASE_TTL_SEC=60`
- `AGENTHUB_API_KEYS_FILE=./data/state/api_keys.bootstrap.json` (ilk bootstrap için)
- `AGENTHUB_LOG_LEVEL=INFO`

## Docker / Çalıştırma Planı

### Local dev (default)
- `uvicorn app.main:app --host 0.0.0.0 --port 7788 --reload`

### Docker
- Volume mounts:
  - `./data:/app/data`
- Port:
  - `7788:7788`

### Compose service
- `agenthub` tek servis (MVP)
- Healthcheck: `GET /v1/health`

## Test Planı (Karar Tamam)

### Unit tests
- Capability matching
- Retry/backoff hesaplama
- Lease expiry kararları
- Lock acquire/renew/release semantics
- Artifact checksum/path sanitizer

### Integration tests (SQLite temp DB)
- Task lifecycle:
  - create -> claim -> start -> complete
- Fail + retry flow:
  - fail(retryable=true) -> requeue -> claim again
- Non-retryable fail:
  - fail(retryable=false) -> failed
- Lease timeout recovery:
  - running task lease expire -> retry/dead-letter
- Concurrency:
  - 2 agent aynı task’ı claim etmeye çalışır -> sadece biri kazanır
- Approval:
  - running/claimed task -> waiting_approval -> approve -> resume
- SSE events:
  - task transition event stream yayınlanır
- Artifact upload/download integrity:
  - SHA256 doğrulanır

### Security tests
- Invalid API key -> 401
- Viewer role write endpoint -> 403
- Path traversal attempt in artifact metadata -> rejected

## Kabul Kriterleri (Acceptance Criteria)

1. En az 3 agent aynı anda bağlanıp farklı görevleri çakışmasız işleyebiliyor
2. Aynı task aynı anda iki agent tarafından claim edilemiyor
3. Agent çökmesi/heartbeat kesilmesi durumunda task lease timeout ile tekrar kuyruğa dönüyor
4. Artifact’ler lokal diskte tutuluyor ve API üzerinden listelenip indirilebiliyor
5. Dashboard task/agent/event durumlarını canlıya yakın gösteriyor
6. Tüm task state transition’ları audit event olarak kayıt altına alınıyor
7. Sistem restart sonrası SQLite state korunuyor (`./data` mount ile)

## Uygulama Aşamaları (İş Sırası)

### Phase 1 (MVP çekirdek)
1. Repo scaffold + config + logging
2. SQLite schema + repositories
3. Health + auth + agents endpoints
4. Tasks lifecycle + claim/lease
5. Events + audit
6. Locks API
7. Basic artifact store
8. Background lease/retry scheduler
9. pytest integration tests

### Phase 2 (kullanılabilirlik)
1. Messages/threads
2. Approval flow
3. Dashboard views + SSE
4. Admin endpoints (requeue, dead-letter)
5. Retention cleanup jobs

### Phase 3 (gelişmiş)
1. Python SDK worker loop
2. Model routing / arbitration hooks
3. Redis pub/sub (optional)
4. Metrics/observability
5. Rich RBAC/policies

## Public API / Type Ekleri (Implementere net bilgi)

### Yeni tipler
- `AgentRegistrationRequest`
- `AgentHeartbeatRequest`
- `TaskCreateRequest`
- `TaskClaimResponse`
- `TaskCompleteRequest`
- `TaskFailRequest`
- `LockAcquireRequest`
- `ArtifactCreateResponse`
- `EventRecord`
- `ApprovalRequest`

### State enum’ları
- `TaskState`
- `AgentStatus`
- `MessageType`
- `ArtifactType`
- `ApprovalStatus`

## Varsayımlar ve Seçilen Defaultlar

- Hedef ortam başlangıçta **tek makine / LAN erişimli local sistem**
- MVP için **Python + FastAPI + SQLite** seçildi (hızlı ve taşınabilir)
- Güvenlik minimum viable düzeyde: **API key + role**
- Mesajlaşma için başlangıçta **REST + SSE**, WebSocket zorunlu değil
- Artifact depolama **local disk**
- Orchestrator tek instance (HA yok)
- “Direkt model-to-model chat” yerine **ortak state/orchestrator** yaklaşımı esas

