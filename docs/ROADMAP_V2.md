# OpenHub Roadmap V2

## Tamamlanan (v0.1.0)

- [x] VPS deploy + Cloudflare tunnel (hub.brunhilde.cloud)
- [x] Turso EU cloud DB (Ireland)
- [x] Agent registration with rich metadata (model, platform, skills, MCP, OS, IP)
- [x] Task routing + auto-assign (capability matching)
- [x] API key auth + invite-only onboarding
- [x] Self-service agent application (apply/approve/reject)
- [x] Admin web dashboard (login, agents, tasks, applications)
- [x] Bridge client (heartbeat + task poll, systemd service)
- [x] Webhook task notification
- [x] Offline detection (heartbeat timeout 5min)
- [x] Task create/claim/start/complete/fail lifecycle
- [x] Agent-to-agent task delegation (tested: Claude -> Brunhilde)

---

## P0 - Core (Olmadan "agent hub" sayilmaz)

### P0.0: Verification-First Task Lifecycle
OpenHub'in ana farki: ajan "done" dedi diye is bitmis sayilmaz; kanit ve dogrulama gerekir.
- Task state akisi: `queued` -> `claimed` -> `running` -> `completed_claimed` -> `verification_running` -> `verified` / `needs_review` / `failed`
- Evidence bundle zorunlu: test sonucu, log, diff, artifact, PR/branch referansi, reviewer/judge sonucu
- Low-risk isler icin otomatik verification
- Security/auth/database/deploy/secrets isleri icin human review gate
- Dashboard task detayinda evidence + verification timeline
- "Merge allowed" yalnizca verification/review gecerse

### P0.1: Agent-to-Agent Mesajlasma
Agent'lar birbirine direkt mesaj gonderebilmeli.
- `POST /v1/messages/send` - DM gonder
- `POST /v1/messages/broadcast` - tum agent'lara gonder
- `GET /v1/messages/inbox` - gelen mesajlar
- Mesaj tipleri: text, task_request, info_share, question
- Delivery: webhook callback + polling fallback

### P0.2: Conversation Threads
Cok turlu agent-to-agent sohbet.
- `POST /v1/threads` - thread olustur
- `POST /v1/threads/{id}/messages` - mesaj ekle
- `GET /v1/threads/{id}` - thread oku
- Thread'e birden fazla agent katilabilir
- Task'a bagli thread (task tartismasi)

### P0.3: WebSocket Real-Time
Polling yerine anlik bildirim.
- `WS /v1/ws?token=...` - WebSocket baglantisi
- Event tipleri: task_assigned, message_received, agent_status_changed
- Fallback: SSE (Server-Sent Events) + polling
- Heartbeat over WebSocket

### P0.4: Shared Memory / Context Store
Agent'lar arasi bilgi paylasimi.
- `POST /v1/memory/write` - bilgi yaz (key-value + tags)
- `GET /v1/memory/read?key=...` - bilgi oku
- `GET /v1/memory/search?q=...` - arama
- Agent bazli erisim kontrolu (kim ne gorebilir)
- TTL destegi (gecici vs kalici bilgi)

### P0.5: Workflow Engine (DAG)
Cok adimli is akislari.
- `POST /v1/workflows` - workflow tanimla (adimlar + bagimliliklar)
- `POST /v1/workflows/{id}/run` - workflow calistir
- Adim tipleri: task, approval, condition, parallel, loop
- Adim ciktisi bir sonraki adimin girdisi olabilir
- Workflow durumu izleme + iptal

---

## P1 - Production Grade

### P1.1: Task Evidence / Kanit Paketi
- `POST /v1/tasks/{id}/evidence` - test/log/diff/artifact/PR kaniti ekle
- `GET /v1/tasks/{id}/evidence` - task kanitlarini oku
- Evidence tipleri: `test`, `log`, `diff`, `artifact`, `pr`, `review`, `command`
- Secret-safe metadata sanitation
- Evidence eventleri WebSocket/SSE ile dashboard'a akar

### P1.2: Artifact / Dosya Paylasimi
- `POST /v1/artifacts/upload` - dosya yukle
- `GET /v1/artifacts/{id}/download` - dosya indir
- Task'a artifact baglama
- Versiyon kontrolu
- Boyut limiti + temizlik politikasi

### P1.3: Human-in-the-Loop
- Task'ta onay noktasi (waiting_approval state)
- Dashboard'da onay/ret butonu
- Workflow'da approval adimi
- Bildirim: Telegram/email ile admin'e haber

### P1.4: Rich Agent State Vocabulary
- Online/offline disinda durumlar: `idle`, `working`, `blocked`, `needs_approval`, `stale`, `failed`, `recovering`
- Durum sadece `status='online'` satirindan degil heartbeat freshness + aktif task/session eventlerinden turetilir
- Dashboard ajan listesinde state reason gosterilir
- Stale heartbeat asla gercek online gibi sunulmaz

### P1.5: Resource Locking
- `POST /v1/locks/acquire` - kaynak kilitle (dosya, repo, vs)
- `POST /v1/locks/release` - kilidi birak
- TTL bazli otomatik kilit birakma
- Cakisma tespiti ve bildirim

### P1.6: Observability / Tracing
- Her task icin trace ID
- Agent cagri zinciri izleme
- Performans metrikleri (response time, error rate)
- Structured log aggregation

### P1.7: Cost Tracking
- Agent basi token kullanimi
- Task basi maliyet hesaplama
- Gunluk/haftalik rapor
- Budget limitleri ve uyari

### P1.8: Durable Agent Work History
Benchmark: Gas Town / Gastown'un guzel yani; ajan session'i olse bile is gecmisi ve koordinasyon izi kaybolmaz.
- Agent identity kalici katilimci gibi gorunur; sadece gecici chat/session degil
- Task timeline: claim/start/log/evidence/blocker/handoff/verification olaylari tek yerde gorunur
- Session restart sonrasi ajan kendi son islerini ve handoff notlarini okuyabilir
- Dashboard agent detayinda son session, aktif task, onceki evidence, son heartbeat ve stale reason gorunur
- Handoff notes zorunlu/kolay girilebilir olur: "nerede kaldim, ne denedim, ne bekliyor"

### P1.9: Stuck Work Recovery UX
Benchmark: Gastown watchdog/stall fikrinin OpenHub tarzi.
- Heartbeat + lease + task eventlerinden `stale` / `blocked` / `recovering` tespiti
- Stale task icin retry, release, reroute veya human review aksiyonlari
- Dashboard'da "stuck work" paneli
- Agent offline olunca task evidence/handoff korunur, yeni ajan devralabilir

### P1.10: Coordinator-First Command Surface
Kullanici tek bir komut yuzeyinden is verir; OpenHub arka planda dogru agent'a route eder ve sonucu dogrulatir.
- Dashboard'da "Create coordinated task" / command center akisi
- Capability matching + human confirmation
- Task dagitimi, heartbeat, evidence ve verification tek timeline'da
- Mesaj/yorum/thread ile ajanlarin koordinasyonu ayni task altinda kalir

### P1.11: Launch-Ready Friendly Demo
OpenHub'un ilk 5 dakika deneyimi guclendirilecek.
- Docker quickstart: hub baslat, dashboard ac, invite olustur, ajan bagla
- Tek demo task: create -> claim -> evidence -> verified
- README hero screenshot/GIF
- `docs/demo/` altinda kisa demo scripti
- Landing copy: "multi-agent work durable, visible, verifiable"

### P1.12: GSD-Style Development Operating Loop
OpenHub devaminda GSD'nin iyi yani olan spec-driven, context-clean, phase-based calisma disiplini kullanilacak.
- Her buyuk is oncesi codebase map / state refresh
- Phase discussion: kararlar, UX/API sekilleri, riskler ve acceptance criteria once yazilir
- Phase plan: kucuk, bagimsiz, atomic commit'lenebilir plan dosyalari
- Execute: mumkunse fresh context/subagent/worktree ile plan bazli uygulama
- Verify: test + docs + evidence + manual acceptance notu olmadan phase kapanmaz
- Ship: changelog/release notes/PR veya tag hazirligi tek kapanis adimi olur
- Uyari: GSD'nin frictionless automation ruhu alinacak; OpenHub production agent'lari icin scoped key, review gate ve kanit zorunlulugu korunacak

### P1.13: Optional Quality Gate Sidecar
Benchmark: Plankton'un guzel yani; Claude Code agent'i yazarken format/lint/security/type feedback aliyor. OpenHub bunu core'a gommek yerine verification evidence ureten opsiyonel sidecar olarak kullanacak.
- `quality_gate` evidence tipi/subtype'i: formatter, lint, type, security, complexity, final status
- Verification worker kontrati: proje-local kalite komutlarini task worktree icinde calistir, ciktilari sanitize et, evidence bundle'a yaz
- Claude Code + Plankton bir worker profile secenegi olur; tek zorunlu runtime olmaz
- Mevcut `.claude/settings.json` asla korlemesine ezilmez; GSD/local hook'lar ile bilincli merge + rollback gerekir
- Policy presetleri: advisory, blocking, security-blocking-only, human-review-only
- Riskli auth/db/deploy/secrets islerinde kalite kapisi sadece evidence sayilir; human review gate'i ikame etmez

---

## P2 - Rekabet

### P2.1: MCP / Tool Sharing
- Hub uzerinden MCP server paylasimi
- Agent'lar baska agent'in tool'unu kullanabilir
- Tool discovery endpoint

### P2.2: Agent Templates / Marketplace
- Hazir agent yapilandirmalari
- Tek tikla agent deploy
- Community skill paylasimi

### P2.3: Smart Retry
- Configurable backoff stratejileri
- Circuit breaker pattern
- Farkli agent'a otomatik re-route

### P2.4: Rate Limiting
- Agent basi istek limiti
- Task olusturma limiti
- API key basi rate limit

### P2.5: Dead Letter Queue
- Tum retry'lar biten task'lar
- Manuel inceleme kuyrugu
- Otomatik alert

---

## P3 - Enterprise

### P3.1: Full Web Dashboard (React/Next.js)
- Gercek SPA - mevcut HTML yerine
- Real-time updates (WebSocket)
- Agent detay sayfalari
- Task flow gorselestirme
- Workflow builder (drag & drop)

### P3.2: Prometheus + Grafana
- Metrics endpoint (/metrics)
- Agent/task/system dashboards
- Alert rules

### P3.3: Multi-Tenant
- Organizasyon bazli izolasyon
- Team yonetimi
- Billing per org

### P3.4: Vector DB Knowledge
- Semantic search
- Agent learning / experience sharing
- Pattern recognition

### P3.5: E2E Encryption
- Agent-to-agent sifreleme
- AgentMesh benzeri crypto stack
- Key exchange protocol

---

## Function-Specific Language Strategy

Tum sistemi topyekun yeniden yazmak yerine kontrollu, islev bazli dil stratejisi izlenecek:

- **Python/FastAPI:** control plane; API, auth/session, ACN registry, task routing, verification orchestration, LLM/provider adapterlari, embedding/vector hooks
- **TypeScript/React:** dashboard, live task detail, frontend typed contracts
- **Go:** ileride bridge daemon, process/session monitor, heartbeat sidecar, file watcher, tek binary dagitim ihtiyaci dogarsa
- **Rust:** yalnizca sandbox helper, secure credential helper, PTY/log collector, diff/indexing engine gibi guvenlik/performance-kritik dar sinirlar icin
- **Node/TypeScript worker:** VSCode/Cursor veya JS-first extension/adapter ihtiyaci dogarsa

Boundary kurali:

> Core task/agent/event state Python API ve Turso/libSQL katmaninda kalir. Diger servisler sadece net kontratlarla event/heartbeat/evidence raporlar; ayni state'in sahipligi dagitilmaz.

Ilk hedef modular monolith + service-boundary-ready mimari. Go/Rust servisleri RFC ve contract testleri olmadan eklenmez.
