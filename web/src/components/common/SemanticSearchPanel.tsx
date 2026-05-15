import { Link } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
import { Search } from 'lucide-react'
import { useSemanticSearch } from '@/hooks/queries/useSemanticSearch'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { SemanticSearchHit } from '@/types/entities'

function HitCard({ hit }: { hit: SemanticSearchHit }) {
  const distance = Number.isFinite(hit.distance) ? hit.distance.toFixed(3) : 'n/a'
  const body = (
    <div className="rounded-lg border border-zinc-800 bg-black/20 p-4 transition hover:border-emerald-500/50">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-emerald-300">{hit.entity_type}</div>
          <div className="mt-1 truncate text-sm font-medium text-zinc-100">{hit.id}</div>
        </div>
        <div className="rounded-full border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-500">d {distance}</div>
      </div>
      <p className="mt-3 line-clamp-3 text-sm text-zinc-400">{hit.content || 'No semantic preview available.'}</p>
    </div>
  )

  if (hit.entity_type === 'agent') {
    return <Link to="/agents/$agentId" params={{ agentId: hit.id }}>{body}</Link>
  }
  if (hit.entity_type === 'task') {
    return <Link to="/tasks/$taskId" params={{ taskId: hit.id }}>{body}</Link>
  }
  return body
}

export function SemanticSearchPanel() {
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const search = useSemanticSearch(query)
  const normalized = query.trim()
  const hits = search.data?.hits ?? []

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setQuery(draft)
  }

  return (
    <section className="mb-6 rounded-xl border border-zinc-800 bg-zinc-950/70 p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-1">
        <div className="flex items-center gap-2 text-zinc-50">
          <Search className="h-4 w-4 text-emerald-300" />
          <h2 className="text-lg font-semibold">Semantic memory</h2>
        </div>
        <p className="text-sm text-zinc-500">Search indexed ACN agents and tasks by meaning, not only exact text.</p>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
        <Input
          aria-label="Semantic memory query"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Find agents or tasks by capability, model, intent…"
          className="border-zinc-800 bg-zinc-900 text-zinc-100 placeholder:text-zinc-600"
        />
        <Button type="submit" disabled={draft.trim().length < 2 || search.isFetching}>
          {search.isFetching ? 'Searching…' : 'Search memory'}
        </Button>
      </form>

      {normalized.length > 0 && normalized.length < 2 && (
        <p className="mt-3 text-sm text-zinc-500">Use at least 2 characters to search semantic memory.</p>
      )}

      {search.isError && (
        <div className="mt-4 rounded-lg border border-amber-900/60 bg-amber-950/30 p-3 text-sm text-amber-200">
          Semantic search is unavailable. Vector memory may be disabled or still warming up.
        </div>
      )}

      {search.isSuccess && (
        <div className="mt-4">
          <div className="mb-3 text-sm text-zinc-500">
            {search.data.total} result{search.data.total === 1 ? '' : 's'} for “{search.data.query}”
          </div>
          {hits.length > 0 ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {hits.map((hit) => (
                <HitCard key={`${hit.entity_type}:${hit.id}`} hit={hit} />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-zinc-800 bg-black/20 p-4 text-sm text-zinc-500">No semantic matches yet.</div>
          )}
        </div>
      )}
    </section>
  )
}
