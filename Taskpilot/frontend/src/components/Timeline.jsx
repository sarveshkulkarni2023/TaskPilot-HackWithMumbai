import StepItem from './StepItem.jsx'

export default function Timeline({ steps, activeIndex }) {
  if (!steps.length) {
    return (
      <div className="rounded-xl border border-dashed border-edge p-6 text-center text-xs text-slate-500">
        Awaiting task steps.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {steps.map((step, index) => (
        <StepItem
          key={`${step.action}-${index}`}
          step={step}
          index={index}
          active={index === activeIndex}
        />
      ))}
    </div>
  )
}
