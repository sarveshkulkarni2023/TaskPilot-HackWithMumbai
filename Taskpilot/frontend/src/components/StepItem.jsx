const statusStyles = {
  pending: 'border-edge text-slate-400',
  active: 'border-accent text-accent',
  completed: 'border-ok text-ok',
  failed: 'border-err text-err'
}

const statusLabel = {
  pending: 'Pending',
  active: 'Active',
  completed: 'Done',
  failed: 'Failed'
}

export default function StepItem({ step, index, active }) {
  const status = step.status || 'pending'
  return (
    <div className={`rounded-xl border px-4 py-3 ${statusStyles[status]} ${active ? 'shadow-glow' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Step {index + 1}</p>
          <p className="mt-1 text-sm text-slate-200">{step.description}</p>
        </div>
        <span className="rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.2em]">
          {statusLabel[status]}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
        <span>{step.action}</span>
        {step.duration_ms != null && <span>{step.duration_ms} ms</span>}
        {step.error && <span className="text-err">{step.error}</span>}
      </div>
    </div>
  )
}
