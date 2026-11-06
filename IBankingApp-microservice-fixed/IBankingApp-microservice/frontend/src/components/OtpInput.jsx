import React, { useRef } from 'react'

export default function OtpInput({ length = 6, value, onChange, disabled }) {
  const inputsRef = useRef([])
  const digits = value.split('').concat(Array(length).fill('')).slice(0, length)

  function updateDigit(index, digit) {
    const next = [...digits]
    next[index] = digit
    onChange(next.join('').slice(0, length))
  }

  function handleChange(e, index) {
    const raw = e.target.value.replace(/\D/g, '')
    if (!raw) {
      updateDigit(index, '')
      return
    }
    const char = raw[raw.length - 1]
    updateDigit(index, char)
    if (index < length - 1) inputsRef.current[index + 1]?.focus()
  }

  function handleKeyDown(e, index) {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus()
    }
  }

  function handlePaste(e) {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length)
    if (pasted) {
      e.preventDefault()
      onChange(pasted.padEnd(length, '').slice(0, length).replace(/\s/g, ''))
    }
  }

  return (
    <div className="flex gap-2" onPaste={handlePaste}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => (inputsRef.current[index] = el)}
          value={digit}
          onChange={(e) => handleChange(e, index)}
          onKeyDown={(e) => handleKeyDown(e, index)}
          disabled={disabled}
          inputMode="numeric"
          maxLength={1}
          className="h-12 w-11 rounded-lg border border-border bg-white text-center text-lg font-semibold text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-canvas"
        />
      ))}
    </div>
  )
}
