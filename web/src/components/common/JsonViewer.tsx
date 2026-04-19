// Minimal monospace JSON tree with native <details> collapse.
// UI-SPEC: monospace 12px caption, syntax-aware coloring.

interface Props {
  value: unknown
  name?: string
}

function classify(v: unknown): string {
  if (v === null) return 'text-zinc-500'
  if (typeof v === 'string') return 'text-emerald-400'
  if (typeof v === 'number') return 'text-sky-400'
  if (typeof v === 'boolean') return 'text-violet-400'
  return 'text-zinc-50'
}

export function JsonViewer({ value, name }: Props) {
  if (value === null || typeof value !== 'object') {
    return (
      <div className="font-mono text-xs">
        {name && <span className="text-zinc-400">{name}: </span>}
        <span className={classify(value)}>{JSON.stringify(value)}</span>
      </div>
    )
  }
  const isArray = Array.isArray(value)
  const entries = isArray
    ? (value as unknown[]).map((v, i) => [String(i), v] as const)
    : Object.entries(value as Record<string, unknown>)

  return (
    <details open className="font-mono text-xs">
      <summary className="cursor-pointer text-zinc-400">
        {name && <span>{name}: </span>}
        <span className="text-zinc-50">
          {isArray ? `Array(${entries.length})` : `Object(${entries.length})`}
        </span>
      </summary>
      <div className="ml-4 border-l border-zinc-800 pl-2">
        {entries.map(([k, v]) => (
          <JsonViewer key={k} value={v} name={k} />
        ))}
      </div>
    </details>
  )
}
