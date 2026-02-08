export default function BrowserView({ frame, frameSource, activeStep, logs }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-edge bg-black/30">
      <div className="flex items-center justify-between border-b border-edge px-4 py-2 text-xs text-slate-400">
        <span>Live Browser</span>
        <span className="uppercase tracking-[0.2em]">Playwright Stream</span>
      </div>

      <div className="relative flex min-h-[360px] items-center justify-center bg-ink/70">
        {frame ? (
          <img
            src={`data:image/png;base64,${frame}`}
            alt="Browser frame"
            className="w-full object-cover"
          />
        ) : (
          <div className="text-xs text-slate-500">Awaiting frames...</div>
        )}

        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/80 via-transparent to-transparent" />

        {frameSource && (
          <div className="absolute left-4 top-4 rounded-full border border-edge bg-panel/80 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-300">
            {frameSource}
          </div>
        )}

        {activeStep && (
          <div className="absolute bottom-4 left-4 right-4 rounded-xl border border-edge bg-panel/80 px-4 py-3 text-xs text-slate-200">
            Executing: {activeStep.description}
          </div>
        )}
      </div>

      {logs && logs.length > 0 && (
        <div className="border-t border-edge px-4 py-2 text-[11px] text-slate-500">
          <div className="flex flex-col gap-1">
            {logs.slice(-5).map((log, idx) => (
              <div key={`${log.level}-${idx}`}>
                <span className="uppercase tracking-[0.2em]">{log.level}</span> - {log.message}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
