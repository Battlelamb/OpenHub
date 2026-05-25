# Phase 06: Kanban Board + Workflow Canvas — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace the Tasks list page with a fully-functional Kanban board (drag-drop → backend API → DB → refetch) that opens a React Flow workflow canvas on task click.

**Architecture:** 
- Frontend: `@hello-pangea/dnd` for drag-drop, `@xyflow/react` for canvas
- Backend: `PATCH /v1/tasks/{task_id}/status` admin endpoint with transition validation
- State: TanStack Query invalidation after each mutation

**Tech Stack:** React 19, TypeScript, Tailwind, TanStack Query, FastAPI, SQLite/Turso

---

## Current State Assessment

### What exists (scaffold — built without GSD, needs verification):
- `web/src/components/kanban/KanbanBoard.tsx` (130 lines)
- `web/src/components/kanban/KanbanColumn.tsx` (63 lines)
- `web/src/components/kanban/KanbanCard.tsx` (102 lines)
- `web/src/components/canvas/WorkflowCanvas.tsx` (211 lines)
- `web/src/routes/_authed/tasks/index.tsx` (17 lines)
- `web/src/hooks/queries/useTasks.ts` — `useTransitionTaskStatus()` hook
- `app/services/task_service.py` — `admin_transition_status()` method
- `app/api/routes_tasks.py` — `PATCH /{task_id}/status` endpoint

### What's missing (critical gaps):
1. **Zero backend tests** for admin_transition_status or PATCH endpoint
2. **Zero frontend tests** for Kanban/Canvas
3. **No error handling** — failed transitions silently fail
4. **No loading states** during drag-drop transitions
5. **Missing "cancelled" column** — 6 statuses, only 5 columns
6. **No E2E verification** of the full drag-drop → API → DB → refetch cycle

---

## Tasks

### Task 06-01: Backend unit tests for admin_transition_status

**Objective:** Prove the service method correctly validates transitions, updates DB, and rejects invalid moves.

**Files:**
- Create: `tests/unit/test_admin_transition.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_admin_transition.py
"""Tests for TaskService.admin_transition_status (Phase 06-01)."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.services.task_service import TaskService
from app.models.tasks import Task, TaskStatus


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def service(mock_db):
    return TaskService(mock_db)


def _make_task(status="queued", task_id="t1"):
    return Task(
        id=task_id, title="Test", description="Desc",
        task_type="feature", priority=50, status=status,
        required_capabilities=["python"], max_retries=2,
        retry_count=0, labels={}, payload={}, artifact_ids=[],
    )


class TestAdminTransitionStatus:
    """Test valid and invalid state transitions."""

    @pytest.mark.parametrize("from_status,to_status", [
        ("queued", "claimed"),
        ("queued", "running"),
        ("queued", "cancelled"),
        ("claimed", "queued"),
        ("claimed", "running"),
        ("running", "completed"),
        ("running", "failed"),
        ("running", "queued"),
        ("completed", "queued"),
        ("failed", "queued"),
        ("cancelled", "queued"),
    ])
    def test_valid_transitions(self, service, from_status, to_status):
        task = _make_task(status=from_status)
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = task
        service.task_repo.update.return_value = _make_task(status=to_status)

        result = service.admin_transition_status("t1", to_status, "admin1")
        assert result is not None
        service.task_repo.update.assert_called_once()

    @pytest.mark.parametrize("from_status,to_status", [
        ("queued", "completed"),
        ("queued", "failed"),
        ("claimed", "completed"),
        ("claimed", "failed"),
        ("running", "claimed"),
        ("completed", "running"),
        ("completed", "failed"),
        ("failed", "running"),
        ("failed", "completed"),
        ("cancelled", "running"),
        ("cancelled", "completed"),
    ])
    def test_invalid_transitions_raise(self, service, from_status, to_status):
        task = _make_task(status=from_status)
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = task

        with pytest.raises(ValueError, match="not allowed"):
            service.admin_transition_status("t1", to_status, "admin1")

    def test_task_not_found_returns_none(self, service):
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = None

        result = service.admin_transition_status("nonexistent", "queued", "admin1")
        assert result is None

    def test_transition_sets_claimed_at(self, service):
        task = _make_task(status="queued")
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = task
        service.task_repo.update.return_value = _make_task(status="claimed")

        service.admin_transition_status("t1", "claimed", "admin1")
        call_args = service.task_repo.update.call_args
        updates = call_args[0][1]
        assert "claimed_at" in updates

    def test_transition_to_queued_resets_assignment(self, service):
        task = _make_task(status="running")
        service.task_repo = MagicMock()
        service.task_repo.get_by_id.return_value = task
        service.task_repo.update.return_value = _make_task(status="queued")

        service.admin_transition_status("t1", "queued", "admin1")
        call_args = service.task_repo.update.call_args
        updates = call_args[0][1]
        assert updates["owner_agent_id"] is None
        assert updates["claimed_at"] is None
        assert updates["started_at"] is None
        assert updates["lease_until"] is None
```

**Step 2: Run tests to verify failure**

Run: `cd /home/brunhilde/OpenHub && source .venv/bin/activate && python -m pytest tests/unit/test_admin_transition.py -v`
Expected: Tests should PASS (service method already exists). If they fail, fix the service method.

**Step 3: Verify**

Run: `python -m pytest tests/unit/test_admin_transition.py -v --tb=short`
Expected: All parametrized tests pass.

**Step 4: Commit**

```bash
git add tests/unit/test_admin_transition.py
git commit -m "test: add unit tests for admin_transition_status (Phase 06-01)"
```

---

### Task 06-02: Backend integration tests for PATCH endpoint

**Objective:** Prove the HTTP endpoint returns correct status codes (200, 404, 409) and response shapes.

**Files:**
- Create: `tests/integration/test_patch_task_status.py`

**Step 1: Write failing tests**

```python
# tests/integration/test_patch_task_status.py
"""Integration tests for PATCH /v1/tasks/{task_id}/status (Phase 06-02)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_token(client: TestClient) -> str:
    """Get admin JWT token."""
    resp = client.post("/v1/auth/admin/login", data={
        "username": "<admin-user-from-env>", "password": "<admin-password-from-env>"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def queued_task_id(client: TestClient, auth_headers: dict) -> str:
    """Create a task and return its ID."""
    resp = client.post("/v1/tasks/", json={
        "title": "Test task",
        "description": "For PATCH testing",
        "required_capabilities": ["python"],
    }, headers=auth_headers)
    assert resp.status_code == 200
    return resp.json()["id"]


class TestPatchTaskStatus:
    """Test PATCH /v1/tasks/{task_id}/status endpoint."""

    def test_queued_to_claimed(self, client, auth_headers, queued_task_id):
        resp = client.patch(
            f"/v1/tasks/{queued_task_id}/status",
            json={"status": "claimed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "claimed"

    def test_queued_to_completed_is_409(self, client, auth_headers, queued_task_id):
        resp = client.patch(
            f"/v1/tasks/{queued_task_id}/status",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert "not allowed" in resp.json()["detail"]

    def test_nonexistent_task_is_404(self, client, auth_headers):
        resp = client.patch(
            "/v1/tasks/nonexistent-id/status",
            json={"status": "queued"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_invalid_status_value_is_422(self, client, auth_headers, queued_task_id):
        resp = client.patch(
            f"/v1/tasks/{queued_task_id}/status",
            json={"status": "bogus"},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # Pydantic validation

    def test_full_lifecycle(self, client, auth_headers, queued_task_id):
        """queued → claimed → running → completed"""
        tid = queued_task_id
        for target in ["claimed", "running", "completed"]:
            resp = client.patch(
                f"/v1/tasks/{tid}/status",
                json={"status": target},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == target

    def test_cancel_from_running(self, client, auth_headers, queued_task_id):
        """queued → claimed → running → cancelled"""
        tid = queued_task_id
        for target in ["claimed", "running", "cancelled"]:
            resp = client.patch(
                f"/v1/tasks/{tid}/status",
                json={"status": target},
                headers=auth_headers,
            )
            assert resp.status_code == 200
```

**Step 2: Run tests**

Run: `cd /home/brunhilde/OpenHub && source .venv/bin/activate && python -m pytest tests/integration/test_patch_task_status.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/test_patch_task_status.py
git commit -m "test: add integration tests for PATCH /status endpoint (Phase 06-02)"
```

---

### Task 06-03: Fix Kanban — add cancelled column + error toast + loading state

**Objective:** Complete the Kanban UI with all 6 status columns, error handling, and loading feedback.

**Files:**
- Modify: `web/src/components/kanban/KanbanBoard.tsx`
- Modify: `web/src/components/kanban/KanbanColumn.tsx`

**Step 1: Add cancelled column to COLUMNS array**

Add to `KanbanBoard.tsx`:
```tsx
import { Ban } from 'lucide-react'
// ...
{ id: 'cancelled', title: 'Cancelled', icon: <Ban className="h-4 w-4" />, color: 'text-zinc-500' },
```

**Step 2: Add error toast on failed transition**

In `KanbanBoard.tsx`, add `onError` to the mutation:
```tsx
import { toast } from 'sonner'

const transitionStatus = useTransitionTaskStatus()
// Replace the mutation call in handleDragEnd:
transitionStatus.mutate(
  { taskId: draggableId, status: destination.droppableId },
  {
    onError: (error) => {
      toast.error(`Failed to move task: ${error.message}`)
    },
  }
)
```

**Step 3: Add loading indicator to KanbanCard**

When a task is being transitioned, show a subtle spinner overlay on the card. Use the `isPending` state from the mutation.

**Step 4: Verify visually**

Run: `cd /home/brunhilde/OpenHub/web && npm run dev`
Navigate to /dashboard/tasks, verify 6 columns, drag a task, check toast on error.

**Step 5: Commit**

```bash
git add web/src/components/kanban/KanbanBoard.tsx web/src/components/kanban/KanbanCard.tsx
git commit -m "feat(kanban): add cancelled column, error toast, loading state (Phase 06-03)"
```

---

### Task 06-04: Frontend component tests for Kanban

**Objective:** Prove KanbanBoard renders columns, groups tasks by status, and handles drag events.

**Files:**
- Create: `web/src/components/kanban/KanbanBoard.test.tsx`

**Step 1: Write tests**

```tsx
// KanbanBoard.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { KanbanBoard } from './KanbanBoard'

// Mock the hooks
vi.mock('@/hooks/queries/useTasks', () => ({
  useTasks: vi.fn(),
  useTransitionTaskStatus: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

vi.mock('@/components/canvas/WorkflowCanvas', () => ({
  WorkflowCanvas: () => <div data-testid="workflow-canvas" />,
}))

describe('KanbanBoard', () => {
  it('renders all 6 column headers', () => {
    const { useTasks } = require('@/hooks/queries/useTasks')
    useTasks.mockReturnValue({ data: [], isLoading: false })
    
    render(<KanbanBoard />)
    
    expect(screen.getByText('Queued')).toBeInTheDocument()
    expect(screen.getByText('Claimed')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('Cancelled')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    const { useTasks } = require('@/hooks/queries/useTasks')
    useTasks.mockReturnValue({ data: undefined, isLoading: true })
    
    render(<KanbanBoard />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('shows task count', () => {
    const { useTasks } = require('@/hooks/queries/useTasks')
    useTasks.mockReturnValue({
      data: [
        { id: '1', title: 'Task A', status: 'queued', priority: 3, created_at: '', updated_at: '' },
        { id: '2', title: 'Task B', status: 'running', priority: 3, created_at: '', updated_at: '' },
      ],
      isLoading: false,
    })
    
    render(<KanbanBoard />)
    expect(screen.getByText('2 total')).toBeInTheDocument()
  })
})
```

**Step 2: Run tests**

Run: `cd /home/brunhilde/OpenHub/web && npx vitest run src/components/kanban/KanbanBoard.test.tsx`

**Step 3: Commit**

```bash
git add web/src/components/kanban/KanbanBoard.test.tsx
git commit -m "test(kanban): add component tests for KanbanBoard (Phase 06-04)"
```

---

### Task 06-05: E2E verification — drag-drop cycle

**Objective:** Prove the full cycle: drag task in UI → PATCH API → DB updated → UI refetches and shows new column.

**Files:**
- Modify: `tests/e2e/test_app.py` (add Kanban E2E test)

**Step 1: Write E2E test**

```python
def test_kanban_drag_drop_cycle(page, base_url, admin_token):
    """Drag a queued task to 'claimed' column via API and verify UI updates."""
    # Create a task via API
    resp = requests.post(f"{base_url}/v1/tasks/", json={
        "title": "E2E Kanban Test",
        "description": "Should move to claimed",
        "required_capabilities": ["test"],
    }, headers={"Authorization": f"Bearer {admin_token}"})
    task_id = resp.json()["id"]

    # Transition via PATCH (simulates drag-drop)
    resp = requests.patch(
        f"{base_url}/v1/tasks/{task_id}/status",
        json={"status": "claimed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "claimed"

    # Navigate to tasks page and verify
    page.goto(f"{base_url}/dashboard/tasks")
    # ... verify task appears in Claimed column
```

**Step 2: Commit**

```bash
git add tests/e2e/test_app.py
git commit -m "test(e2e): add Kanban drag-drop cycle test (Phase 06-05)"
```

---

### Task 06-06: Full verification + STATE.md update

**Objective:** Run all tests, verify build, update project state.

**Step 1: Run all tests**
```bash
# Backend
cd /home/brunhilde/OpenHub && source .venv/bin/activate && python -m pytest tests/ -x -q

# Frontend
cd /home/brunhilde/OpenHub/web && npx vitest run

# Build
cd /home/brunhilde/OpenHub/web && npm run build
```

**Step 2: Update STATE.md**

**Step 3: Commit**
```bash
git add -A
git commit -m "feat: Phase 06 Kanban + Canvas complete (GSD verified)"
```

---

## Valid Transition Map

```
queued    → claimed, running, cancelled
claimed   → queued, running, cancelled
running   → queued, completed, failed, cancelled
completed → queued
failed    → queued
cancelled → queued
```

## Risks & Notes

1. **Drag-drop visual feedback** — `@hello-pangea/dnd` provides optimistic UI, but backend may reject (409). Need to handle rollback or refetch.
2. **Turso connection** — some tests may fail if Turso credentials not available (pre-existing skip).
3. **React Flow bundle size** — `@xyflow/react` adds ~100KB gzipped. Consider lazy loading.
