const connectionColor = {
  connected: 'text-ok',
  disconnected: 'text-err',
  error: 'text-warn'
}

export default function StatusBar({ connection, taskState, progress }) {
  return (
    <div className="glass flex flex-wrap items-center gap-4 rounded-xl px-4 py-2 text-xs text-slate-400">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full bg-current ${connectionColor[connection] || 'text-slate-400'}`} />
        <span className="uppercase tracking-[0.2em]">{connection}</span>
      </div>
      <div className="h-4 w-px bg-edge" />
      <div className="uppercase tracking-[0.2em]">{taskState}</div>
      <div className="h-4 w-px bg-edge" />
      <div className="flex items-center gap-2">
        <div className="h-2 w-24 overflow-hidden rounded-full bg-edge">
          <div className="h-full bg-accent" style={{ width: `${progress}%` }} />
        </div>
        <span>{progress}%</span>
      </div>
    </div>
  )
}
