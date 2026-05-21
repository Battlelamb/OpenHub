import { useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Node,
  type Edge,
  BackgroundVariant,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useTask } from '@/hooks/queries/useTasks'
import { TaskStatusBadge } from '@/components/common/StatusBadge'
import { X, Clock, User, Zap, FileText, AlertCircle } from 'lucide-react'
import type { Task } from '@/types/entities'

interface WorkflowCanvasProps {
  task: Task
  open: boolean
  onClose: () => void
}

// --- Custom Node: Task ---
function TaskNode({ data }: { data: { task: Task } }) {
  const t = data.task
  return (
    <div className="bg-zinc-900 border-2 border-emerald-500/40 rounded-xl p-4 min-w-[220px] shadow-xl shadow-emerald-500/5">
      <div className="flex items-center gap-2 mb-2">
        <FileText className="h-4 w-4 text-emerald-400" />
        <span className="text-sm font-semibold text-zinc-100 truncate">{t.title}</span>
      </div>
      <TaskStatusBadge status={t.status} />
      {t.description && (
        <p className="text-xs text-zinc-500 mt-2 line-clamp-2">{t.description}</p>
      )}
    </div>
  )
}

// --- Custom Node: Agent ---
function AgentNode({ data }: { data: { agentId: string } }) {
  return (
    <div className="bg-zinc-900 border-2 border-violet-500/40 rounded-xl p-4 min-w-[180px] shadow-xl shadow-violet-500/5">
      <div className="flex items-center gap-2">
        <User className="h-4 w-4 text-violet-400" />
        <span className="text-sm font-medium text-zinc-200">{data.agentId}</span>
      </div>
      <span className="text-[10px] text-zinc-600 mt-1 block">Assigned Agent</span>
    </div>
  )
}

// --- Custom Node: Info Panel ---
function InfoPanelNode({ data }: { data: { task: Task } }) {
  const t = data.task
  return (
    <div className="bg-zinc-900/95 border border-zinc-700 rounded-xl p-4 min-w-[240px] max-w-[280px] shadow-xl">
      <h3 className="text-sm font-semibold text-zinc-100 mb-3">Task Details</h3>
      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2 text-zinc-400">
          <Zap className="h-3 w-3 flex-shrink-0" />
          <span>Priority: {t.priority}</span>
        </div>
        {t.agent_id && (
          <div className="flex items-center gap-2 text-zinc-400">
            <User className="h-3 w-3 flex-shrink-0" />
            <span>Agent: {t.agent_id}</span>
          </div>
        )}
        <div className="flex items-center gap-2 text-zinc-400">
          <Clock className="h-3 w-3 flex-shrink-0" />
          <span>Created: {new Date(t.created_at).toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-400">
          <Clock className="h-3 w-3 flex-shrink-0" />
          <span>Updated: {new Date(t.updated_at).toLocaleString()}</span>
        </div>
        {t.error && (
          <div className="flex items-start gap-2 text-red-400 mt-2 p-2 bg-red-500/10 rounded-lg">
            <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
            <span className="line-clamp-3">{t.error}</span>
          </div>
        )}
        {t.result && (
          <div className="mt-2 p-2 bg-zinc-800 rounded-lg">
            <span className="text-zinc-500 text-[10px] uppercase tracking-wider">Result</span>
            <pre className="text-[10px] text-zinc-400 mt-1 overflow-auto max-h-[80px]">
              {JSON.stringify(t.result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

const nodeTypes = {
  taskNode: TaskNode,
  agentNode: AgentNode,
  infoPanel: InfoPanelNode,
}

export function WorkflowCanvas({ task, open, onClose }: WorkflowCanvasProps) {
  const { data: freshTask } = useTask(open ? task.id : undefined)
  const activeTask = freshTask ?? task

  const { nodes, edges } = useMemo(() => {
    const n: Node[] = []
    const e: Edge[] = []

    // Central task node
    n.push({
      id: 'task',
      type: 'taskNode',
      position: { x: 300, y: 100 },
      data: { task: activeTask },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    })

    // Agent node (if assigned)
    if (activeTask.agent_id) {
      n.push({
        id: 'agent',
        type: 'agentNode',
        position: { x: 50, y: 50 },
        data: { agentId: activeTask.agent_id },
        sourcePosition: Position.Right,
      })
      e.push({
        id: 'agent-task',
        source: 'agent',
        target: 'task',
        animated: activeTask.status === 'running',
        style: { stroke: '#8b5cf6', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' },
      })
    }

    // Info panel
    n.push({
      id: 'info',
      type: 'infoPanel',
      position: { x: 550, y: 50 },
      data: { task: activeTask },
      targetPosition: Position.Left,
    })
    e.push({
      id: 'task-info',
      source: 'task',
      target: 'info',
      style: { stroke: '#52525b', strokeWidth: 1.5, strokeDasharray: '5 5' },
    })

    return { nodes: n, edges: e }
  }, [activeTask])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Canvas panel */}
      <div className="relative ml-auto w-full max-w-4xl bg-zinc-950 border-l border-zinc-800 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-zinc-100">{activeTask.title}</h2>
            <TaskStatusBadge status={activeTask.status} />
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* React Flow Canvas */}
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            proOptions={{ hideAttribution: true }}
            className="bg-zinc-950"
            nodesDraggable={true}
            nodesConnectable={false}
            elementsSelectable={true}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#27272a" />
            <Controls
              className="!bg-zinc-900 !border-zinc-700 !rounded-lg [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700 [&>button]:!text-zinc-300 [&>button:hover]:!bg-zinc-700"
            />
            <MiniMap
              className="!bg-zinc-900 !border-zinc-700"
              nodeColor="#3f3f46"
              maskColor="rgba(0,0,0,0.6)"
            />
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}
