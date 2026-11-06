import React from 'react'

const STEPS = [
  { key: 'lookup', label: 'Tra cứu học phí' },
  { key: 'confirm', label: 'Xác nhận giao dịch' },
  { key: 'otp', label: 'Xác thực OTP' }
]

export default function StepIndicator({ current }) {
  const currentIndex = STEPS.findIndex((s) => s.key === current)

  return (
    <ol className="mb-8 flex items-center">
      {STEPS.map((step, index) => {
        const isDone = index < currentIndex
        const isActive = index === currentIndex
        return (
          <li key={step.key} className="flex flex-1 items-center last:flex-none">
            <div className="flex items-center gap-2">
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  isDone
                    ? 'bg-success text-white'
                    : isActive
                    ? 'bg-primary text-white'
                    : 'bg-white text-ink/40 border border-border'
                }`}
              >
                {isDone ? '✓' : index + 1}
              </span>
              <span
                className={`text-sm font-medium ${
                  isActive ? 'text-ink' : isDone ? 'text-ink/70' : 'text-ink/40'
                }`}
              >
                {step.label}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <span
                className={`mx-4 h-px flex-1 ${isDone ? 'bg-success' : 'bg-border'}`}
                aria-hidden
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
