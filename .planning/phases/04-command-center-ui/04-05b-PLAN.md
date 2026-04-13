---
phase: 04-command-center-ui
plan: 05b
type: execute
wave: 4
depends_on: ["04-02", "04-03", "04-04", "04-05"]
files_modified:
  - web/src/routes/_authed/tasks/index.tsx
  - web/src/routes/_authed/tasks/$taskId.tsx
  - web/src/components/forms/TaskCreateForm.tsx
  - web/src/components/forms/TaskCreateForm.test.tsx
  - web/src/components/common/TraceTimeline.tsx
  - web/src/components/common/TraceTimeline.test.tsx
  - web/src/i18n/namespaces/tasks.ts
  - web/src/mocks/handlers/tasks.ts
  - web/src/components/ui/dialog.tsx
  - web/src/components/ui/alert-dialog.tsx
  - web/src/components/ui/select.tsx
  - web/src/components/ui/textarea.tsx
autonomous: true
requirements: ["UI-03", "UI-04", "UI-05", "UI-12"]
must_haves:
  truths:
    - "Tasks list /tasks filterable by status, real-time updates via WS merge (UI-03)"
    - "Task create dialog uses react-hook-form + zod, calls useCreateTask mutation (UI-04)"
    - "Task cancel uses AlertDialog confirmation with exact UI-SPEC copy, calls useCancelTask (UI-05)"
    - "Task detail /tasks/$taskId renders TraceTimeline component implementing UI-SPEC trace viewer spec (UI-12)"
    - "TraceTimeline: vertical timeline, 16px per level indent, verbatim category color tokens (llm=violet-400, tool=sky-400, db=amber-400, http=emerald-400, internal=zinc-500, error=red-500)"
    - "Plan 05b only writes to its own i18n namespace stub (tasks.ts) and msw handler stub (tasks.ts) — never touches web/src/i18n/index.ts or web/src/mocks/handlers.ts"
    - "TaskStatusBadge is IMPORTED from Plan 05's web/src/components/common/StatusBadge.tsx (no duplication)"
    - "ResponsiveList is IMPORTED from Plan 05's web/src/components/common/ResponsiveList.tsx (no duplication)"
  artifacts:
    - path: web/src/routes/_authed/tasks/index.tsx
      provides: "UI-03 task list + UI-04 create dialog + UI-05 cancel action"
    - path: web/src/routes/_authed/tasks/$taskId.tsx
      provides: "Task detail drilldown with TraceTimeline slot"
    - path: web/src/components/forms/TaskCreateForm.tsx
      provides: "UI-04 react-hook-form + zod task create form"
    - path: web/src/components/common/TraceTimeline.tsx
      provides: "UI-12 vertical trace timeline with color-coded categories"
  key_links:
    - from: web/src/routes/_authed/tasks/index.tsx
      to: web/src/hooks/queries/useTasks.ts
      via: "useTasks, useCreateTask, useCancelTask"
      pattern: "useTasks|useCreateTask|useCancelTask"
    - from: web/src/components/forms/TaskCreateForm.tsx
      to: web/src/hooks/queries/useAgents.ts
      via: "agent selector dropdown"
      pattern: "useAgents"
    - from: web/src/routes/_authed/tasks/index.tsx
      to: web/src/components/common/StatusBadge.tsx
      via: "TaskStatusBadge import from Plan 05"
      pattern: "TaskStatusBadge"
    - from: web/src/routes/_authed/tasks/$taskId.tsx
      to: web/src/components/common/TraceTimeline.tsx
      via: "TraceTimeline render at bottom of detail page"
      pattern: "TraceTimeline"
---

<objective>
Build the Operations **Tasks** feature routes: Tasks list (UI-03), Task create dialog (UI-04), Task cancel action (UI-05), Task detail with TraceTimeline (UI-12). Splits out from the original Plan 05 for context-budget sanity.

This plan is one of three parallel Wave 4 plans: 04-05 (Agents+Workflows), 04-05b (Tasks), 04-06 (Visibility). It depends on Plan 05 because it imports shared primitives `ResponsiveList` and `TaskStatusBadge` from files created by Plan 05. Since Plans 05 and 05b run in the same wave, 05b MUST declare Plan 05 in depends_on; the execute-phase wave resolver will either serialize them within Wave 4 or (preferred) treat both Wave 4 concurrency as acceptable because files_modified are disjoint and the shared files are read-only.

NOTE: If strict wave ordering is required (05 finishes before 05b starts), the execute-phase orchestrator will honor `depends_on: ["04-05"]` and run 05b after 05 within the same wave. Plan 06 has no dependency on either 05 or 05b and runs truly in parallel.

Purpose: Ship the "operate tasks" surface. Users can list, filter, create, cancel, and inspect tasks with distributed trace visualization.

Output: `/tasks`, `/tasks/{id}` both work in dev. Task create dialog dispatches tasks. Cancel action confirms then mutates. TraceTimeline renders nested spans when data present.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-command-center-ui/04-CONTEXT.md
@.planning/phases/04-command-center-ui/04-UI-SPEC.md
@.planning/phases/04-command-center-ui/04-02-SUMMARY.md
@.planning/phases/04-command-center-ui/04-03-SUMMARY.md
@.planning/phases/04-command-center-ui/04-04-SUMMARY.md
@.planning/phases/04-command-center-ui/04-05-SUMMARY.md

<interfaces>
From Plan 04 (data layer):
- useTasks(filters?) → UseQueryResult<Task[]>
- useTask(id) → UseQueryResult<Task>
- useCreateTask() → UseMutationResult<Task, Error, CreateTaskPayload>
- useCancelTask() → UseMutationResult<Task, Error, string>
- useAgents() for agent selector in TaskCreateForm
- types from web/src/types/entities.ts: Task, TaskStatus

From Plan 04 (frozen aggregators — DO NOT EDIT):
- web/src/i18n/index.ts — registers `tasks` namespace stub. This plan OVERWRITES web/src/i18n/namespaces/tasks.ts ONLY.
- web/src/mocks/handlers.ts — spreads `tasksHandlers`. This plan OVERWRITES web/src/mocks/handlers/tasks.ts ONLY.

From Plan 05 (shared primitives — IMPORT, do not duplicate):
- web/src/components/common/StatusBadge.tsx exports `TaskStatusBadge` (with all 6 status tokens)
- web/src/components/common/ResponsiveList.tsx exports `ResponsiveList<T>`
- web/src/components/ui/badge.tsx installed
- web/src/components/ui/table.tsx installed

Task status color tokens (UI-SPEC § Color § Status color map) — already implemented by Plan 05 StatusBadge:
queued=zinc-400, claimed=violet-400, running=sky-400 (animate-pulse), completed=emerald-500, failed=red-500, cancelled=zinc-500 strikethrough

Trace viewer (UI-SPEC lines 270-286): vertical timeline, 16px per level indent (pl-4), category colors: llm=violet-400, tool=sky-400, db=amber-400, http=emerald-400, internal=zinc-500, error=red-500, duration bar proportional width.

Copy table strings (UI-SPEC lines 164-206) — MUST come from locales, no inline English.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install tasks-specific shadcn primitives + tasks i18n stub fill + tasks msw stub fill + TraceTimeline component</name>
  <files>web/src/components/ui/dialog.tsx, web/src/components/ui/alert-dialog.tsx, web/src/components/ui/select.tsx, web/src/components/ui/textarea.tsx, web/src/i18n/namespaces/tasks.ts, web/src/mocks/handlers/tasks.ts, web/src/components/common/TraceTimeline.tsx, web/src/components/common/TraceTimeline.test.tsx</files>
  <read_first>
    - .planning/phases/04-command-center-ui/04-UI-SPEC.md (Trace viewer lines 270-286, Destructive actions lines 207-212, Copy table task entries)
    - web/components.json
    - web/src/components/common/StatusBadge.tsx (from Plan 05 — confirm TaskStatusBadge export)
    - web/src/components/common/ResponsiveList.tsx (from Plan 05 — confirm Column<T> type)
    - web/src/i18n/namespaces/tasks.ts (stub from Plan 04 — OVERWRITE)
    - web/src/mocks/handlers/tasks.ts (stub from Plan 04 — OVERWRITE)
  </read_first>
  <action>
Install shadcn primitives specific to tasks flows:
```bash
cd /home/omer/projects/OpenHub/web
npx shadcn@latest add dialog -y
npx shadcn@latest add alert-dialog -y
npx shadcn@latest add select -y
npx shadcn@latest add textarea -y
```

Note: `badge` and `table` are already installed by Plan 05. Do NOT reinstall.

Write `web/src/i18n/namespaces/tasks.ts` (OVERWRITE the Plan 04 stub):
```ts
export const en = {
  title: "Tasks",
  createCta: "Create task",
  dialogTitle: "Create task",
  dispatchCta: "Dispatch task",
  cancelCta: "Cancel task",
  cancelConfirmBody: "Cancel task: This will stop the running task. The agent will receive a cancel signal. Continue?",
  cancelConfirmBack: "Keep running",
  columns: { title: "Title", status: "Status", agent: "Agent", priority: "Priority", updated: "Updated" },
  filterAll: "All",
  emptyHeading: "No tasks yet",
  emptyBody: "Click Create task to dispatch your first task.",
  fields: { title: "Title", description: "Description", priority: "Priority", agent: "Agent", capabilities: "Required capabilities" },
  status: { queued: "queued", claimed: "claimed", running: "running", completed: "completed", failed: "failed", cancelled: "cancelled" },
  trace: {
    emptyHeading: "No trace available",
    emptyBody: "Traces appear once the task is claimed and the agent emits spans.",
  },
} as const

export const tr = {
  title: "Gorevler",
  createCta: "Gorev olustur",
  dialogTitle: "Gorev olustur",
  dispatchCta: "Gorevi gonder",
  cancelCta: "Gorevi iptal et",
  cancelConfirmBody: "Gorevi iptal et: Bu, calisan gorevi durdurur. Ajan iptal sinyali alir. Devam?",
  cancelConfirmBack: "Calismaya devam",
  columns: { title: "Baslik", status: "Durum", agent: "Ajan", priority: "Oncelik", updated: "Guncellendi" },
  filterAll: "Tumu",
  emptyHeading: "Henuz gorev yok",
  emptyBody: "Ilk gorevini olusturmak icin Gorev olustur'a tikla.",
  fields: { title: "Baslik", description: "Aciklama", priority: "Oncelik", agent: "Ajan", capabilities: "Gerekli yetenekler" },
  status: { queued: "kuyrukta", claimed: "alindi", running: "calisiyor", completed: "tamamlandi", failed: "basarisiz", cancelled: "iptal" },
  trace: {
    emptyHeading: "Trace mevcut degil",
    emptyBody: "Gorev alindiginda ve ajan span'lar yayinladiginda trace'ler gorunur.",
  },
} as const
```

Write `web/src/mocks/handlers/tasks.ts` (OVERWRITE the Plan 04 stub):
```ts
import { http, HttpResponse, type HttpHandler } from 'msw'

export const tasksHandlers: HttpHandler[] = [
  http.get('/v1/tasks', () => HttpResponse.json([])),
  http.get('/v1/tasks/:id', ({ params }) => HttpResponse.json({
    id: params.id, title: 'mock', status: 'queued', priority: 3, created_at: '', updated_at: ''
  })),
  http.post('/v1/tasks', async ({ request }) => {
    const body: any = await request.json()
    return HttpResponse.json({ ...body, id: 't1', status: 'queued', created_at: '', updated_at: '' })
  }),
  http.post('/v1/tasks/:id/cancel', ({ params }) => HttpResponse.json({
    id: params.id, title: 'mock', status: 'cancelled', priority: 3, created_at: '', updated_at: ''
  })),
]
```

Write `web/src/components/common/TraceTimeline.tsx`:
```tsx
import { cn } from '@/lib/utils'

export interface TraceSpan {
  id: string
  name: string
  category: 'llm' | 'tool' | 'db' | 'http' | 'internal' | 'error'
  duration_ms: number
  start_ms: number
  children?: TraceSpan[]
  attributes?: Record<string, unknown>
}

// UI-SPEC trace viewer spec: verbatim category color tokens
const categoryColors: Record<TraceSpan['category'], string> = {
  llm: 'violet-400',
  tool: 'sky-400',
  db: 'amber-400',
  http: 'emerald-400',
  internal: 'zinc-500',
  error: 'red-500',
}

interface NodeProps {
  span: TraceSpan
  depth: number
  rootDuration: number
}

function Node({ span, depth, rootDuration }: NodeProps) {
  const color = categoryColors[span.category]
  const widthPct = rootDuration > 0 ? (span.duration_ms / rootDuration) * 100 : 0
  return (
    <div>
      <div
        className="flex items-center gap-2 border-l-[3px] py-1"
        style={{ borderColor: `var(--tw-${color}, currentColor)`, paddingLeft: `${Math.min(depth, 6) * 16}px` }}
      >
        <span className={`size-2 rounded-full bg-${color}`} />
        <span className="flex-1 truncate text-sm text-zinc-50">{span.name}</span>
        <div className="relative h-2 w-40 rounded bg-zinc-800">
          <div className={`absolute left-0 top-0 h-full rounded bg-${color}/60`} style={{ width: `${widthPct}%` }} />
        </div>
        <span className="w-16 text-right font-mono text-xs text-zinc-400 tabular-nums">{span.duration_ms}ms</span>
      </div>
      {span.children?.map((child) => (
        <Node key={child.id} span={child} depth={depth + 1} rootDuration={rootDuration} />
      ))}
    </div>
  )
}

export function TraceTimeline({ root }: { root: TraceSpan | null }) {
  if (!root) return null
  return (
    <div className={cn('rounded-lg border border-zinc-800 bg-zinc-900 p-4 font-sans')}>
      <Node span={root} depth={0} rootDuration={root.duration_ms} />
    </div>
  )
}
```

Write `web/src/components/common/TraceTimeline.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TraceTimeline, type TraceSpan } from './TraceTimeline'

const sample: TraceSpan = {
  id: 'root',
  name: 'task.execute',
  category: 'internal',
  duration_ms: 1000,
  start_ms: 0,
  children: [
    { id: 'c1', name: 'llm.chat', category: 'llm', duration_ms: 400, start_ms: 100 },
    { id: 'c2', name: 'db.query', category: 'db', duration_ms: 150, start_ms: 500 },
  ],
}

describe('TraceTimeline', () => {
  it('renders root span name', () => {
    render(<TraceTimeline root={sample} />)
    expect(screen.getByText('task.execute')).toBeInTheDocument()
  })

  it('renders nested children', () => {
    render(<TraceTimeline root={sample} />)
    expect(screen.getByText('llm.chat')).toBeInTheDocument()
    expect(screen.getByText('db.query')).toBeInTheDocument()
  })

  it('renders nothing when root is null', () => {
    const { container } = render(<TraceTimeline root={null} />)
    expect(container.firstChild).toBeNull()
  })
})
```
  </action>
  <verify>
    <automated>cd /home/omer/projects/OpenHub/web &amp;&amp; npm run test -- --run src/components/common/TraceTimeline.test.tsx &amp;&amp; npm run typecheck</automated>
  </verify>
  <acceptance_criteria>
    - Files exist: `web/src/components/ui/{dialog,alert-dialog,select,textarea}.tsx`
    - `web/src/components/common/TraceTimeline.tsx` contains all 6 category color tokens (violet-400, sky-400, amber-400, emerald-400, zinc-500, red-500)
    - `web/src/i18n/namespaces/tasks.ts` exports `en` with `title === "Tasks"` and `cancelConfirmBody` starting with "Cancel task:"
    - `web/src/i18n/namespaces/tasks.ts` exports `tr` with `cancelConfirmBody: "Gorevi iptal et: Bu, calisan gorevi durdurur. Ajan iptal sinyali alir. Devam?"`
    - `web/src/mocks/handlers/tasks.ts` contains `'/v1/tasks'` AND `'/v1/tasks/:id/cancel'` AND `tasksHandlers` export
    - This plan does NOT modify `web/src/i18n/index.ts` or `web/src/mocks/handlers.ts` (frozen by Plan 04)
    - `cd web && npm run test -- --run src/components/common/TraceTimeline.test.tsx` exits 0
    - `cd web && npm run typecheck` exits 0
  </acceptance_criteria>
  <done>
Tasks shadcn primitives + i18n stub + msw stub + TraceTimeline shipped. No shared file edits.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TaskCreateForm (react-hook-form + zod) + test</name>
  <files>web/src/components/forms/TaskCreateForm.tsx, web/src/components/forms/TaskCreateForm.test.tsx</files>
  <behavior>
    - TaskCreateForm: zod schema {title: min(1), description: optional, priority: int 1-5, agent_id: optional}
    - TaskCreateForm: submit calls useCreateTask mutation, success closes dialog
    - TaskCreateForm.test: render form, fill title + priority, submit, verify POST /v1/tasks received payload with title + priority
  </behavior>
  <read_first>
    - web/src/hooks/queries/useTasks.ts (from Plan 04)
    - web/src/hooks/queries/useAgents.ts (from Plan 04)
    - web/src/components/ui/form.tsx (confirm Plan 03 exists)
    - web/src/components/ui/select.tsx, textarea.tsx (from Task 1)
    - .planning/phases/04-command-center-ui/04-UI-SPEC.md (Task create fields lines 164-206)
  </read_first>
  <action>
Write `web/src/components/forms/TaskCreateForm.tsx`:
```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { useCreateTask } from '@/hooks/queries/useTasks'
import { useAgents } from '@/hooks/queries/useAgents'
import { ApiError } from '@/lib/api-client'

const schema = z.object({
  title: z.string().min(1, 'Title required'),
  description: z.string().optional(),
  priority: z.coerce.number().int().min(1).max(5).default(3),
  agent_id: z.string().optional().nullable(),
})

type Values = z.infer<typeof schema>

export function TaskCreateForm({ onDone }: { onDone?: () => void }) {
  const { t } = useTranslation(['tasks', 'common'])
  const createTask = useCreateTask()
  const { data: agents = [] } = useAgents()

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { title: '', description: '', priority: 3, agent_id: null },
  })

  const onSubmit = async (v: Values) => {
    try {
      await createTask.mutateAsync({
        title: v.title,
        description: v.description,
        priority: v.priority,
        agent_id: v.agent_id || null,
      })
      form.reset()
      onDone?.()
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.problem.title, { description: err.problem.detail })
      } else {
        toast.error(t('common:requestFailed'))
      }
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tasks:fields.title')}</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tasks:fields.description')}</FormLabel>
              <FormControl>
                <Textarea rows={3} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="priority"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tasks:fields.priority')}</FormLabel>
              <FormControl>
                <Input type="number" min={1} max={5} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="agent_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tasks:fields.agent')}</FormLabel>
              <Select onValueChange={field.onChange} value={field.value ?? undefined}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="-" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {agents.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={createTask.isPending}>
          {t('tasks:dispatchCta')}
        </Button>
      </form>
    </Form>
  )
}
```

Write `web/src/components/forms/TaskCreateForm.test.tsx`:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import React from 'react'
import { server } from '@/mocks/server'
import { TaskCreateForm } from './TaskCreateForm'
import '@/i18n'

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children)
}

describe('TaskCreateForm', () => {
  it('submits valid payload to /v1/tasks', async () => {
    let receivedBody: any = null
    server.use(
      http.get('/v1/agents', () => HttpResponse.json([])),
      http.post('/v1/tasks', async ({ request }) => {
        receivedBody = await request.json()
        return HttpResponse.json({
          id: 't1',
          title: receivedBody.title,
          status: 'queued',
          priority: receivedBody.priority,
          created_at: '',
          updated_at: '',
        })
      }),
    )

    render(<TaskCreateForm />, { wrapper: wrap() })
    const user = userEvent.setup()

    await user.type(await screen.findByLabelText(/title|baslik/i), 'Do the thing')
    await user.click(screen.getByRole('button', { name: /dispatch|gonder/i }))

    await waitFor(() => expect(receivedBody).not.toBeNull())
    expect(receivedBody.title).toBe('Do the thing')
    expect(receivedBody.priority).toBe(3)
  })
})
```
  </action>
  <verify>
    <automated>cd /home/omer/projects/OpenHub/web &amp;&amp; npm run test -- --run src/components/forms/TaskCreateForm.test.tsx &amp;&amp; npm run typecheck</automated>
  </verify>
  <acceptance_criteria>
    - `web/src/components/forms/TaskCreateForm.tsx` contains `useCreateTask` AND `zodResolver` AND `useAgents`
    - `web/src/components/forms/TaskCreateForm.test.tsx` asserts `receivedBody.title` AND `receivedBody.priority`
    - `cd web && npm run test -- --run src/components/forms/TaskCreateForm.test.tsx` exits 0
    - `cd web && npm run typecheck` exits 0
  </acceptance_criteria>
  <done>
TaskCreateForm implemented and tested with msw-intercepted POST /v1/tasks assertion.
  </done>
</task>

<task type="auto">
  <name>Task 3: Tasks list route (filter + create dialog + cancel AlertDialog) + Task detail route with TraceTimeline</name>
  <files>web/src/routes/_authed/tasks/index.tsx, web/src/routes/_authed/tasks/$taskId.tsx</files>
  <read_first>
    - web/src/hooks/queries/useTasks.ts (from Plan 04)
    - web/src/components/common/StatusBadge.tsx (from Plan 05 — import TaskStatusBadge)
    - web/src/components/common/ResponsiveList.tsx (from Plan 05 — import)
    - web/src/components/common/TraceTimeline.tsx (from Task 1)
    - web/src/components/forms/TaskCreateForm.tsx (from Task 2)
    - web/src/components/ui/dialog.tsx, alert-dialog.tsx, select.tsx (from Task 1)
    - web/src/i18n/namespaces/tasks.ts (from Task 1 — confirm key names)
    - .planning/phases/04-command-center-ui/04-UI-SPEC.md (Destructive actions lines 207-212, Copy table task entries)
  </read_first>
  <action>
Write `web/src/routes/_authed/tasks/index.tsx`:
```tsx
import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { useTasks, useCancelTask } from '@/hooks/queries/useTasks'
import { ResponsiveList } from '@/components/common/ResponsiveList'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TaskCreateForm } from '@/components/forms/TaskCreateForm'
import type { Task, TaskStatus } from '@/types/entities'

export const Route = createFileRoute('/_authed/tasks/')({
  component: TasksList,
})

const ALL_STATUSES: TaskStatus[] = ['queued', 'claimed', 'running', 'completed', 'failed', 'cancelled']

function TasksList() {
  const { t } = useTranslation('tasks')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const { data: tasks = [] } = useTasks({ status: statusFilter || undefined })
  const cancelTask = useCancelTask()
  const [dialogOpen, setDialogOpen] = useState(false)

  const canCancel = (s: TaskStatus) => s === 'queued' || s === 'claimed' || s === 'running'

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-zinc-50">{t('title')}</h1>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder={t('filterAll')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filterAll')}</SelectItem>
              {ALL_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {t(`status.${s}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>{t('createCta')}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('dialogTitle')}</DialogTitle>
              </DialogHeader>
              <TaskCreateForm onDone={() => setDialogOpen(false)} />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <ResponsiveList<Task>
        items={tasks}
        columns={[
          {
            key: 'title',
            label: t('columns.title'),
            render: (ta) => (
              <Link to={'/tasks/$taskId' as any} params={{ taskId: ta.id }} className="text-zinc-50 hover:text-emerald-500">
                {ta.title}
              </Link>
            ),
          },
          {
            key: 'status',
            label: t('columns.status'),
            render: (ta) => <TaskStatusBadge status={ta.status} label={t(`status.${ta.status}`)} />,
          },
          { key: 'agent_id', label: t('columns.agent'), render: (ta) => <span className="font-mono text-xs">{ta.agent_id ?? '-'}</span> },
          { key: 'priority', label: t('columns.priority') },
          {
            key: 'actions' as any,
            label: '',
            render: (ta) =>
              canCancel(ta.status) ? (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button size="sm" variant="destructive">
                      {t('cancelCta')}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{t('cancelCta')}</AlertDialogTitle>
                      <AlertDialogDescription>{t('cancelConfirmBody')}</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{t('cancelConfirmBack')}</AlertDialogCancel>
                      <AlertDialogAction
                        className="bg-red-500 hover:bg-red-600"
                        onClick={() => cancelTask.mutate(ta.id)}
                      >
                        {t('cancelCta')}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              ) : null,
          },
        ]}
        cardRender={(ta) => (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <Link to={'/tasks/$taskId' as any} params={{ taskId: ta.id }} className="font-semibold text-zinc-50">
                {ta.title}
              </Link>
              <TaskStatusBadge status={ta.status} label={t(`status.${ta.status}`)} />
            </div>
            {canCancel(ta.status) && (
              <Button size="sm" variant="destructive" onClick={() => cancelTask.mutate(ta.id)}>
                {t('cancelCta')}
              </Button>
            )}
          </div>
        )}
        emptyState={
          <div className="p-6 text-center">
            <div className="text-lg font-semibold text-zinc-50">{t('emptyHeading')}</div>
            <div className="mt-2 text-sm text-zinc-400">{t('emptyBody')}</div>
          </div>
        }
      />
    </div>
  )
}
```

Write `web/src/routes/_authed/tasks/$taskId.tsx`:
```tsx
import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { useTask } from '@/hooks/queries/useTasks'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { TraceTimeline } from '@/components/common/TraceTimeline'

export const Route = createFileRoute('/_authed/tasks/$taskId')({
  component: TaskDetail,
})

function TaskDetail() {
  const { taskId } = Route.useParams()
  const { t } = useTranslation('tasks')
  const { data: task, isLoading } = useTask(taskId)

  if (isLoading) return <div className="p-6 text-sm text-zinc-400">Loading...</div>
  if (!task) return <div className="p-6 text-sm text-zinc-400">Task not found</div>

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-zinc-50">{task.title}</h1>
        <TaskStatusBadge status={task.status} label={t(`status.${task.status}`)} />
      </div>
      <dl className="mb-6 grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wide text-zinc-400">ID</dt>
          <dd className="font-mono text-zinc-50">{task.id}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-zinc-400">Agent</dt>
          <dd className="font-mono text-zinc-50">{task.agent_id ?? '-'}</dd>
        </div>
      </dl>
      <h2 className="mb-2 text-lg font-semibold text-zinc-50">Trace</h2>
      <TraceTimeline root={null} />
      <div className="mt-2 text-center text-sm text-zinc-400">
        <div>{t('trace.emptyHeading')}</div>
        <div>{t('trace.emptyBody')}</div>
      </div>
    </div>
  )
}
```

Run full gate:
```bash
cd /home/omer/projects/OpenHub/web
npm run typecheck
npm run test -- --run
npm run build
```
  </action>
  <verify>
    <automated>cd /home/omer/projects/OpenHub/web &amp;&amp; npm run typecheck &amp;&amp; npm run test -- --run &amp;&amp; npm run build</automated>
  </verify>
  <acceptance_criteria>
    - File `web/src/routes/_authed/tasks/index.tsx` contains `useCancelTask`, `AlertDialog`, `t('cancelConfirmBody')`, `TaskStatusBadge` (imported from Plan 05), `ResponsiveList` (imported from Plan 05)
    - File `web/src/routes/_authed/tasks/$taskId.tsx` contains `TraceTimeline` AND `useTask(taskId)`
    - `cd web && npm run typecheck` exits 0
    - `cd web && npm run test -- --run` exits 0 (no regressions)
    - `cd web && npm run build` exits 0
  </acceptance_criteria>
  <done>
Tasks list + detail routes with create dialog, cancel AlertDialog, and TraceTimeline slot shipped. UI-03, UI-04, UI-05, UI-12 complete.
  </done>
</task>

</tasks>

<verification>
- `cd web && npm run typecheck` green
- `cd web && npm run test -- --run` green (TaskCreateForm, TraceTimeline tests pass alongside prior tests)
- `cd web && npm run build` green
- `web/src/routes/_authed/tasks/` directory contains index.tsx + $taskId.tsx
- Plan 05b did NOT touch `web/src/i18n/index.ts` or `web/src/mocks/handlers.ts`
- Plan 05b imports `TaskStatusBadge` and `ResponsiveList` from Plan 05's files (grep confirms)
</verification>

<success_criteria>
Navigating in dev to /tasks, /tasks/abc render without crashing. Task create dialog dispatches tasks. Cancel action confirms then mutates. TraceTimeline renders when span data is present. Plan 05, 05b, and 06 execute in Wave 4 without file conflicts.
</success_criteria>

<output>
Write `.planning/phases/04-command-center-ui/04-05b-SUMMARY.md` with: tasks routes shipped, trace viewer color table, TaskCreateForm test strategy, shadcn primitives added this plan (dialog/alert-dialog/select/textarea), confirmation that shared primitives (TaskStatusBadge, ResponsiveList) were imported from Plan 05 with zero duplication.
</output>
