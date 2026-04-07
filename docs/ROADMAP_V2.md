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

### P1.1: Artifact / Dosya Paylasimi
- `POST /v1/artifacts/upload` - dosya yukle
- `GET /v1/artifacts/{id}/download` - dosya indir
- Task'a artifact baglama
- Versiyon kontrolu
- Boyut limiti + temizlik politikasi

### P1.2: Human-in-the-Loop
- Task'ta onay noktasi (waiting_approval state)
- Dashboard'da onay/ret butonu
- Workflow'da approval adimi
- Bildirim: Telegram/email ile admin'e haber

### P1.3: Resource Locking
- `POST /v1/locks/acquire` - kaynak kilitle (dosya, repo, vs)
- `POST /v1/locks/release` - kilidi birak
- TTL bazli otomatik kilit birakma
- Cakisma tespiti ve bildirim

### P1.4: Observability / Tracing
- Her task icin trace ID
- Agent cagri zinciri izleme
- Performans metrikleri (response time, error rate)
- Structured log aggregation

### P1.5: Cost Tracking
- Agent basi token kullanimi
- Task basi maliyet hesaplama
- Gunluk/haftalik rapor
- Budget limitleri ve uyari

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

## Rust Rewrite

Tum sistem Rust'ta yeniden yazilacak:
- Axum web framework
- SQLx + libsql-rs (Turso)
- Tokio async runtime
- ~5MB RAM vs Python 55MB
- ~0 latency vs Python 100ms+
- Production-grade hata yonetimi
