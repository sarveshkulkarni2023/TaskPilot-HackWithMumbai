import { useEffect, useMemo, useRef, useState } from 'react'
import GoalInput from './components/GoalInput.jsx'
import Timeline from './components/Timeline.jsx'
import BrowserView from './components/BrowserView.jsx'
import StatusBar from './components/StatusBar.jsx'

const WS_URL = import.meta.env.VITE_WS_URL
  || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws`

const buildDescription = (step) => {
  if (!step) return ''
  if (step.action === 'navigate') return `Navigate to ${step.url}`
  if (step.action === 'click') return `Click ${step.selector}`
  if (step.action === 'type') return `Type "${step.text}" in ${step.selector}`
  if (step.action === 'scroll') return `Scroll ${step.amount ?? 800}px`
  if (step.action === 'wait') return `Wait ${step.ms ?? 1000}ms`
  if (step.action === 'screenshot') return 'Capture screenshot'
  return step.action
}

export default function App() {
  const [goal, setGoal] = useState('')
  const [steps, setSteps] = useState([])
  const [taskState, setTaskState] = useState('idle')
  const [connection, setConnection] = useState('disconnected')
  const [frame, setFrame] = useState(null)
  const [frameSource, setFrameSource] = useState(null)
  const [activeIndex, setActiveIndex] = useState(null)
  const [logs, setLogs] = useState([])
  const [priceResults, setPriceResults] = useState(null)
  const [credentialsRequest, setCredentialsRequest] = useState(null)
  const [credentialsData, setCredentialsData] = useState({ username: '', email: '', password: '' })
  const wsRef = useRef(null)

  const progress = useMemo(() => {
    if (!steps.length) return 0
    const completed = steps.filter((s) => s.status === 'completed').length
    return Math.round((completed / steps.length) * 100)
  }, [steps])

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnection('connected')
    ws.onclose = () => setConnection('disconnected')
    ws.onerror = () => setConnection('error')

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      const type = message.type

      if (type === 'TASK_STARTED') {
        setTaskState('running')
        if (message.steps) {
          const enriched = message.steps.map((step) => ({
            ...step,
            status: 'pending',
            description: buildDescription(step),
            duration_ms: null
          }))
          setSteps(enriched)
          setActiveIndex(null)
        }
        return
      }

      if (type === 'STEP_STARTED') {
        setSteps((prev) => prev.map((step, idx) => ({
          ...step,
          status: idx === message.index ? 'active' : step.status === 'active' ? 'pending' : step.status
        })))
        setActiveIndex(message.index)
        return
      }

      if (type === 'STEP_COMPLETED') {
        setSteps((prev) => prev.map((step, idx) => (
          idx === message.index
            ? { ...step, status: 'completed', duration_ms: message.duration_ms }
            : step
        )))
        setActiveIndex(null)
        return
      }

      if (type === 'STEP_FAILED') {
        setSteps((prev) => prev.map((step, idx) => (
          idx === message.index
            ? { ...step, status: 'failed', duration_ms: message.duration_ms, error: message.error }
            : step
        )))
        setActiveIndex(null)
        return
      }

      if (type === 'TASK_COMPLETED') {
        setTaskState('completed')
        return
      }

      if (type === 'BROWSER_FRAME') {
        setFrame(message.image)
        setFrameSource(message.source || null)
        return
      }

      if (type === 'LOG') {
        setLogs((prev) => [...prev.slice(-19), message])
      }

      if (type === 'PRICE_RESULTS') {
        setPriceResults(message)
      }

      if (type === 'CREDENTIALS_REQUIRED') {
        setCredentialsRequest(message.fields || {})
      }
    }

    return () => ws.close()
  }, [])

  const handleSubmit = () => {
    if (!goal.trim()) return
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setTaskState('running')
    wsRef.current.send(JSON.stringify({ type: 'START_TASK', goal }))
  }

  const handleCredentialsSubmit = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'CREDENTIALS_PROVIDED', data: credentialsData }))
    setCredentialsRequest(null)
    setCredentialsData({ username: '', email: '', password: '' })
  }

  return (
    <div className="min-h-screen px-6 py-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-slate-100">TaskPilot</h1>
            <p className="text-sm text-slate-400">Natural-language goals to executable browser automation.</p>
          </div>
          <StatusBar connection={connection} taskState={taskState} progress={progress} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <aside className="glass rounded-2xl p-4 shadow-glow">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Timeline</h2>
            <Timeline steps={steps} activeIndex={activeIndex} />
          </aside>

          <section className="flex flex-col gap-6">
            <div className="glass rounded-2xl p-4">
              <GoalInput
                goal={goal}
                setGoal={setGoal}
                onSubmit={handleSubmit}
                loading={taskState === 'running'}
              />
            </div>

            <div className="glass rounded-2xl p-4">
              <BrowserView frame={frame} frameSource={frameSource} activeStep={steps[activeIndex]} logs={logs} />
            </div>

            {priceResults && (
              <div className="glass rounded-2xl p-4">
                <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Price Comparison</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {priceResults.query} {priceResults.max_price ? `under ${priceResults.max_price}` : ''}
                </p>
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  {priceResults.results?.map((platform) => (
                    <div key={platform.platform} className="rounded-xl border border-edge p-3">
                      <div className="text-sm font-semibold text-slate-200">{platform.platform}</div>
                      <div className="mt-2 flex flex-col gap-2 text-xs text-slate-400">
                        {platform.items?.length ? platform.items.map((item, idx) => (
                          <div key={`${platform.platform}-${idx}`} className="flex flex-col gap-1">
                            <span className="text-slate-200">{item.title}</span>
                            <span>{item.price ? `?${item.price}` : 'Price unavailable'}</span>
                          </div>
                        )) : (
                          <div>No results</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>

      {credentialsRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur">
          <div className="glass w-full max-w-md rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-slate-100">Credentials Required</h3>
            <p className="mt-1 text-xs text-slate-400">Enter credentials to continue.</p>
            <div className="mt-4 flex flex-col gap-3">
              {credentialsRequest.username && (
                <input
                  value={credentialsData.username}
                  onChange={(e) => setCredentialsData({ ...credentialsData, username: e.target.value })}
                  placeholder="Username"
                  className="w-full rounded-xl border border-edge bg-ink/60 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-accent"
                />
              )}
              {credentialsRequest.email && (
                <input
                  value={credentialsData.email}
                  onChange={(e) => setCredentialsData({ ...credentialsData, email: e.target.value })}
                  placeholder="Email"
                  className="w-full rounded-xl border border-edge bg-ink/60 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-accent"
                />
              )}
              {credentialsRequest.password && (
                <input
                  type="password"
                  value={credentialsData.password}
                  onChange={(e) => setCredentialsData({ ...credentialsData, password: e.target.value })}
                  placeholder="Password"
                  className="w-full rounded-xl border border-edge bg-ink/60 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-accent"
                />
              )}
              <button
                onClick={handleCredentialsSubmit}
                className="mt-2 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-ink transition hover:bg-accent/90"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
