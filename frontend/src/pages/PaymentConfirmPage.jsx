import React, { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { usePaymentFlow } from '../context/PaymentFlowContext'
import AppLayout from '../components/AppLayout'
import StepIndicator from '../components/StepIndicator'
import * as api from '../services/mockApi'
import { formatVnd } from '../services/mockApi'

export default function PaymentConfirmPage() {
  const { token, user } = useAuth()
  const { flow, setPaymentRequest } = usePaymentFlow()
  const navigate = useNavigate()

  const [agreed, setAgreed] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Nếu người dùng vào thẳng URL này mà chưa tra cứu MSSV, đưa họ về bước 1
  if (!flow.tuition) {
    return <Navigate to="/thanh-toan" replace />
  }

  const { tuition } = flow
  const balance = user?.balance ?? 0
  const hasEnoughBalance = balance >= tuition.amount
  const canConfirm = agreed && hasEnoughBalance

  async function handleConfirm() {
    setError('')
    setIsSubmitting(true)
    try {
      const res = await api.createPaymentRequest(token, { mssv: tuition.mssv })
      setPaymentRequest(res)
      navigate('/thanh-toan/otp')
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-lg">
        <StepIndicator current="confirm" />

        <section className="rounded-2xl border border-border bg-white p-6 shadow-card">
          <h1 className="text-base font-semibold text-ink">Xác nhận giao dịch</h1>

          <div className="mt-5 space-y-4">
            <Group title="Người nộp tiền">
              <Row label="Họ và tên" value={user?.name} />
              <Row label="Số điện thoại" value={user?.phone} />
              <Row label="Email" value={user?.email} />
            </Group>

            <Group title="Thông tin học phí">
              <Row label="MSSV" value={tuition.mssv} />
              <Row label="Sinh viên" value={tuition.studentName} />
              <Row label="Số tiền cần thanh toán" value={formatVnd(tuition.amount)} strong />
            </Group>

            <Group title="Thanh toán">
              <Row
                label="Số dư khả dụng"
                value={formatVnd(balance)}
                valueClassName={hasEnoughBalance ? '' : 'text-danger'}
              />
              {!hasEnoughBalance && (
                <p className="mt-2 rounded-lg bg-danger-light px-3 py-2 text-xs text-danger">
                  Số dư không đủ để thực hiện giao dịch này.
                </p>
              )}
            </Group>
          </div>

          <label className="mt-5 flex cursor-pointer items-start gap-2 text-sm text-ink/70">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary/30"
            />
            Tôi đã đọc và đồng ý với các điều khoản, điều kiện thanh toán học phí của iBanking.
          </label>

          {error && (
            <p className="mt-4 rounded-lg bg-danger-light px-3 py-2 text-sm text-danger">{error}</p>
          )}

          <div className="mt-6 flex gap-3">
            <button
              onClick={() => navigate('/thanh-toan')}
              className="flex-1 rounded-lg border border-border py-2.5 text-sm font-medium text-ink/70 hover:bg-canvas"
            >
              Quay lại
            </button>
            <button
              onClick={handleConfirm}
              disabled={!canConfirm || isSubmitting}
              className="flex-1 rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? 'Đang xử lý...' : 'Xác nhận giao dịch'}
            </button>
          </div>
        </section>
      </div>
    </AppLayout>
  )
}

function Group({ title, children }) {
  return (
    <div>
      <p className="mb-1.5 text-sm font-semibold text-ink/70">{title}</p>
      <div className="rounded-xl border border-border bg-canvas p-4">{children}</div>
    </div>
  )
}

function Row({ label, value, strong, valueClassName = '' }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-ink/60">{label}</span>
      <span className={`money text-sm ${strong ? 'font-semibold' : ''} ${valueClassName || 'text-ink'}`}>
        {value}
      </span>
    </div>
  )
}
