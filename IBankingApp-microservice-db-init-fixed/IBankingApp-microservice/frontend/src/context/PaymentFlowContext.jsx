import React, { createContext, useContext, useState, useCallback } from 'react'

const PaymentFlowContext = createContext(null)

const emptyFlow = {
  tuition: null, // mssv, studentName, amount, status 
  transactionId: null,
  otpSentTo: null,
  otpExpiresAt: null,
  devOtp: null, 
  result: null 
}

export function PaymentFlowProvider({ children }) {
  const [flow, setFlow] = useState(emptyFlow)

  const setTuition = useCallback((tuition) => {
    setFlow((prev) => ({ ...prev, tuition }))
  }, [])

  const setPaymentRequest = useCallback(({ transactionId, tuition, otpSentTo, expiresAt, otpExpiresAt, __devOtp }) => {
    setFlow((prev) => ({
      ...prev,
      transactionId,
      tuition: tuition || prev.tuition,
      otpSentTo,
      otpExpiresAt: otpExpiresAt || expiresAt || (Date.now() + 5 * 60 * 1000),
      devOtp: __devOtp ?? null
    }))
  }, [])

  const setResult = useCallback((result) => {
    setFlow((prev) => ({ ...prev, result }))
  }, [])

  const reset = useCallback(() => setFlow(emptyFlow), [])

  return (
    <PaymentFlowContext.Provider value={{ flow, setTuition, setPaymentRequest, setResult, reset }}>
      {children}
    </PaymentFlowContext.Provider>
  )
}

export function usePaymentFlow() {
  const ctx = useContext(PaymentFlowContext)
  if (!ctx) throw new Error('usePaymentFlow phải được dùng bên trong <PaymentFlowProvider>')
  return ctx
}
