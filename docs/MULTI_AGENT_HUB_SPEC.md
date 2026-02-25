# Multi-Agent Collaboration Hub — Proje Spec

> **Durum:** Fikir/Spec asamasi. Ayri bir sprint'te implement edilecek.
> **Tarih:** 24 Subat 2026
> **Iliskili Proje:** SkorAI (FE + BE)

---

## 1. Problem

Birden fazla AI agent (Claude Code, Cursor, Copilot, custom script) ayni codebase uzerinde calisiyor ama:

- Birbirlerinin varligindan haberleri yok
- Ayni dosyayi ayni anda degistirebilirler (conflict)
- FE ve BE paralel gelistirmede contract drift riski var
- Bir agent'in buldugu insight diger agent'a aktarilmiyor
- Koordinasyon tamamen manual (kullanici araciligiyla)

---

## 2. Cozum: MCP Collaboration Hub

Local bir MCP (Model Context Protocol) server'i, tum agent'larin baglanabildigi merkezi bir koordinasyon noktasi.

### Mimari

```
┌─────────────────────────────────────────────────┐
│            MCP Collaboration Hub                │
│          (custom MCP server - local)            │
│                                                 │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Task Queue   │  │ Shared Context Store     │  │
│  │ (SQLite)     │  │ (findings, decisions)    │  │
│  └─────────────┘  └──────────────────────────┘  │
│                                                 │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Agent        │  │ Event Bus                │  │
│  │ Registry     │  │ (file watch + polling)   │  │
│  └─────────────┘  └──────────────────────────┘  │
└──────┬──────────────┬──────────────┬────────────┘
       │              │              │
  Claude Code    Claude Code    Cursor / Copilot /
  (Instance 1)   (Instance 2)   baska agent
       │              │              │
   SkorAI_FE      SkorAI_BE      Review / QA
```

---

## 3. Core Components

### 3.1 Task Queue

- SQLite-backed task tablosu
- Her task: id, description, priority, status, assigned_to, created_at, updated_at, output
- Status: `pending` → `in_progress` → `completed` / `failed`
- Agent'lar task alir (`claim`), ilerlemesini raporlar, sonucu yazar

### 3.2 Shared Context Store

- Agent'larin buldugu bilgileri paylastigi alan
- Kategoriler: `finding`, `decision`, `contract_change`, `bug`, `todo`
- Her entry: category, content, severity, source_agent, timestamp
- Diger agent'lar sorgulayabilir: "son 1 saatte ne bulundu?"

### 3.3 Agent Registry

- Hangi agent online, ne uzerinde calisiyor, hangi workspace
- Heartbeat mekanizmasi (her 30sn status update)
- Agent capabilities: `["code_edit", "test_run", "docker_build", "review"]`

### 3.4 Event Bus

- File-system watcher: belirli dosyalar degistiginde notify
- Polling-based fallback: her N saniyede "yeni bir sey var mi?" kontrolu
- Ozellikle contract dosyalari (OpenAPI spec, types) icin tetikleme

---

## 4. MCP Server Tool Tanimlari

```typescript
// Agent kayit
register_agent(name: string, workspace: string, capabilities: string[])
  → { agent_id: string, registered_at: string }

// Task yonetimi
assign_task(description: string, priority: "low"|"medium"|"high", assigned_to?: string)
  → { task_id: string }

get_my_tasks(agent_id: string, status?: string)
  → { tasks: Task[] }

report_progress(task_id: string, status: string, output?: string)
  → { success: boolean }

// Bilgi paylasimi
share_finding(category: string, content: string, severity: "info"|"warning"|"critical")
  → { finding_id: string }

get_findings(category?: string, since?: string, severity?: string)
  → { findings: Finding[] }

// Contract drift kontrolu
check_contract_drift(fe_version: string, be_version: string)
  → { compatible: boolean, breaking_changes: string[] }

// Agent durumu
get_active_agents()
  → { agents: AgentInfo[] }

heartbeat(agent_id: string, current_task?: string)
  → { ack: boolean, notifications: Notification[] }
```

---

## 5. Use Cases

### 5.1 FE + BE Paralel Gelistirme

1. BE agent yeni endpoint ekler
2. `share_finding("contract_change", "POST /api/v1/new-endpoint added", "info")` cagirir
3. FE agent `get_findings("contract_change")` ile ogrenip uyum saglar

### 5.2 Code Review Findings Paylasimi

1. Review agent codebase'i tarar, 15 bulgu bulur
2. Her birini `share_finding("bug", "Unused import in utils.py:42", "warning")` ile paylesir
3. Diger agent'lar bu bilgiyi fix ederken kullanir

### 5.3 Automated QA Agent

1. Surekli calisir, her commit sonrasi smoke test kosar
2. Basarisiz olursa: `assign_task("Fix failing smoke test: /health returns 500", "high")`
3. Diger agent task'i alip fix eder

### 5.4 Cross-Repo Refactoring

1. BE agent API response format'i degistirir
2. `share_finding("contract_change", "Response field 'score' renamed to 'credit_score'", "critical")`
3. FE agent otomatik olarak uyumlu degisikligi yapar

---

## 6. Tech Stack Secenekleri

### Secenek A: Python (FastMCP)

```python
from fastmcp import FastMCP

mcp = FastMCP("collaboration-hub")

@mcp.tool()
def register_agent(name: str, workspace: str, capabilities: list[str]):
    ...

@mcp.tool()
def share_finding(category: str, content: str, severity: str):
    ...
```

**Artilari:** SkorAI BE zaten Python, kolay entegrasyon
**Eksileri:** FastMCP nispeten yeni

### Secenek B: TypeScript (MCP SDK)

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({ name: "collaboration-hub" });

server.tool("register_agent", { ... }, async (args) => { ... });
server.tool("share_finding", { ... }, async (args) => { ... });
```

**Artilari:** MCP SDK'nin resmi dili, daha olgun
**Eksileri:** Ayri runtime (Node.js)

### Oneri: **Python (FastMCP)** — SkorAI ekosistemiyle uyumlu

---

## 7. Implementation Roadmap

### Phase 1: File-Based MVP (1-2 gun)

- Shared dizin: `d:/OneDrive/OLD/Documents/SkorAI/.collab/`
- JSON dosyalari: `tasks.json`, `findings.json`, `agents.json`
- Sifir server, sadece dosya okuma/yazma
- Her Claude Code instance bu dizini kullanir
- **Minimum viable coordination**

### Phase 2: MCP Server (3-5 gun)

- FastMCP ile proper MCP server
- SQLite backend (ayri DB, SkorAI DB degil)
- Claude Code `.claude/mcp_servers.json`'a eklenir
- Tool-based iletisim (dosya yerine)
- Heartbeat + notifications

### Phase 3: Dashboard UI (5-10 gun)

- SkorAI_FE'ye `/collab` sayfasi eklenir
- Canli agent durumu, task listesi, findings timeline
- WebSocket ile real-time updates
- Manual task atama UI

---

## 8. SkorAI Entegrasyonu

### MCP Server Konfigurasyonu

`.claude/mcp_servers.json`'a eklenir:

```json
{
  "collaboration-hub": {
    "command": "python",
    "args": ["-m", "collab_hub.server"],
    "cwd": "d:/OneDrive/OLD/Documents/SkorAI"
  }
}
```

### Mevcut Altyapi ile Uyum

- SQLite deneyimi zaten var (SkorAI backend)
- MCP tooling zaten kurulu (Perplexity, Puppeteer, Manus)
- Docker deployment: hub ayri container olabilir veya host'ta calisir
- Contract governance: CLAUDE.md'deki release rules ile entegre

---

## 9. Data Model

```sql
-- Agent registry
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workspace TEXT,
    capabilities TEXT,  -- JSON array
    last_heartbeat TEXT,
    current_task TEXT,
    status TEXT DEFAULT 'online'
);

-- Task queue
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    assigned_to TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    output TEXT,
    FOREIGN KEY (assigned_to) REFERENCES agents(id)
);

-- Shared findings
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    source_agent TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_agent) REFERENCES agents(id)
);

-- Contract versions
CREATE TABLE contract_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fe_version TEXT,
    be_version TEXT,
    openapi_hash TEXT,
    compatible BOOLEAN,
    breaking_changes TEXT,  -- JSON array
    checked_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. Acik Sorular (Sonra Cevaplanacak)

1. Agent authentication gerekli mi? (local ortam, muhtemelen hayir)
2. Findings retention suresi ne olmali? (7 gun? 30 gun?)
3. Conflict resolution: ayni task'i 2 agent claim ederse?
4. File watcher icin hangi dosyalar izlenmeli? (openapi.yaml, types/, API routes)
5. Dashboard'a kimler erisebilmeli?

---

> **Sonraki adim:** Phase 1 (file-based MVP) ile baslanabilir — sifir altyapi, hemen test edilebilir.
