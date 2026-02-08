export default function GoalInput({ goal, setGoal, onSubmit, loading }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Goal</h2>
        <p className="text-xs text-slate-500">Describe what you want the browser to accomplish.</p>
      </div>
      <div className="flex flex-col gap-3 lg:flex-row">
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Find the latest AI tutorials and open the top result"
          className="w-full rounded-xl border border-edge bg-ink/60 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-accent"
        />
        <button
          onClick={onSubmit}
          disabled={loading}
          className="relative inline-flex items-center justify-center rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-ink transition hover:bg-accent/90 disabled:opacity-50"
        >
          {loading ? 'Executing...' : 'Launch Task'}
        </button>
      </div>
      {loading && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-accent" />
          Task running. Live updates streaming.
        </div>
      )}
    </div>
  )
}
