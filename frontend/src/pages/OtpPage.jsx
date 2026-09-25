import React, { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { usePaymentFlow } from '../context/PaymentFlowContext'
import AppLayout from '../components/AppLayout'
import StepIndicator from '../components/StepIndicator'
import OtpInput from '../components/OtpInput'
import * as api from '../services/mockApi'

export default function OtpPage() {
  const { token, refreshUser } = useAuth()
  const { flow, setPaymentRequest, setResult } = usePaymentFlow()
  const navigate = useNavigate()

  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [isVerifying, setIsVerifying] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(0)

  useEffect(() => {
    if (!flow.otpExpiresAt) return
    const tick = () => {
      const remaining = Math.max(0, Math.round((flow.otpExpiresAt - Date.now()) / 1000))
      setSecondsLeft(remaining)
    }
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [flow.otpExpiresAt])

  if (!flow.tuition || !flow.transactionId) {
    return <Navigate to="/thanh-toan" replace />
  }

  const isExpired = secondsLeft === 0
  const minutes = String(Math.floor(secondsLeft / 60)).padStart(2, '0')
  const seconds = String(secondsLeft % 60).padStart(2, '0')

async function handleVerify(e) {
    e.preventDefault()
    setError('')
    setIsVerifying(true)
    try {
      const result = await api.verifyOtp(token, flow.transactionId, otp)
      
      await tuitionService.payTuition(flow.tuition.mssv)

      setResult(result)
      await refreshUser()
      navigate('/thanh-toan/ket-qua')
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || "Xác thực thất bại."
      setError(errorMsg)
      
      if (err.code === 'OTP_EXPIRED' || err.code === 'OTP_MAX_ATTEMPTS') {
        setResult({ status: 'failed', reason: errorMsg })
        navigate('/thanh-toan/ket-qua')
      }
    } finally {
      setIsVerifying(false)
    }
  }

  async function handleResend() {
    setError('')
    setIsResending(true)
    try {
      const res = await api.resendOtp(token, flow.transactionId)
      setPaymentRequest({ ...res, otpSentTo: flow.otpSentTo })
      setOtp('')
    } catch (err) {
      setError(err.message)
    } finally {
      setIsResending(false)
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-lg">
        <StepIndicator current="otp" />

        <section className="rounded-2xl border border-border bg-white p-6 shadow-card">
          <h1 className="text-base font-semibold text-ink">Xác thực OTP</h1>
          <p className="mt-1 text-sm text-ink/60">
            Mã xác thực đã được gửi đến email <strong>{flow.otpSentTo}</strong>.
          </p>

          {flow.devOtp && (
            <p className="mt-3 rounded-lg bg-primary-light px-3 py-2 text-xs text-primary-dark">
              DEMO — mã OTP của bạn là <strong>{flow.devOtp}</strong>
            </p>
          )}

          <form onSubmit={handleVerify} className="mt-5">
            <OtpInput value={otp} onChange={setOtp} disabled={isExpired || isVerifying} />

            <div className="mt-4 flex items-center justify-between text-sm">
              <span className={isExpired ? 'text-danger' : 'text-ink/60'}>
                {isExpired ? 'Mã OTP đã hết hạn' : `Mã có hiệu lực trong ${minutes}:${seconds}`}
              </span>
              <button
                type="button"
                onClick={handleResend}
                disabled={isResending}
                className="font-medium text-primary hover:underline disabled:opacity-50"
              >
                {isResending ? 'Đang gửi lại...' : 'Gửi lại mã'}
              </button>
            </div>

            {error && (
              <p className="mt-4 rounded-lg bg-danger-light px-3 py-2 text-sm text-danger">{error}</p>
            )}

            <button
              type="submit"
              disabled={otp.length !== 6 || isExpired || isVerifying}
              className="mt-5 w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isVerifying ? 'Đang xác thực...' : 'Xác nhận'}
            </button>
          </form>
        </section>
      </div>
    </AppLayout>
  )
}
