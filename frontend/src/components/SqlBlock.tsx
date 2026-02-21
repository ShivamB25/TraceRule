import { memo } from 'react'

interface SqlBlockProps {
  sql: string | null
}

function SqlBlock({ sql }: SqlBlockProps) {
  if (!sql) {
    return (
      <div className="rounded-lg bg-slate-950 p-4">
        <p className="font-mono text-sm italic text-slate-500">No SQL — subjective rule</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg bg-slate-950 p-4">
      <pre className="font-mono text-sm text-emerald-400 whitespace-pre-wrap">{sql}</pre>
    </div>
  )
}

export default memo(SqlBlock)
