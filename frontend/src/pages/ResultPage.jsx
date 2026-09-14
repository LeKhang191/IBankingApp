import React from 'react'
import { Navigate, Link, useNavigate } from 'react-router-dom'
import { usePaymentFlow } from '../context/PaymentFlowContext'
import AppLayout from '../components/AppLayout'
import { formatVnd } from '../services/mockApi'

export default function ResultPage() {
  const { flow, reset } = usePaymentFlow()
  const navigate = useNavigate()

  if (!flow.result) {
    return <Navigate to="/thanh-toan" replace />
  }

  const isSuccess = flow.result.status === 'success'

  function handleDone() {
    reset()
    navigate('/')
  }

  function handleRetry() {
    reset()
    navigate('/thanh-toan')
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-lg">
        <section className="rounded-2xl border border-border bg-white p-8 text-center shadow-card">
          <div
            className={`mx-auto flex h-14 w-14 items-center justify-center rounded-full text-2xl ${
              isSuccess ? 'bg-success-light text-success' : 'bg-danger-light text-danger'
            }`}
          >
            {isSuccess ? '✓' : '✕'}
          </div>

          <h1 className="mt-4 text-lg font-semibold text-ink">
            {isSuccess ? 'Thanh toán học phí thành công' : 'Giao dịch không thành công'}
          </h1>
          <p className="mt-1 text-sm text-ink/60">
            {isSuccess
              ? 'Biên lai đã được gửi đến email của bạn.'
              : flow.result.reason || 'Vui lòng thử lại giao dịch.'}
          </p>

          {isSuccess && (
            <div className="mt-6 rounded-xl border border-border bg-canvas p-4 text-left">
              <Row label="Mã giao dịch" value={flow.result.id} />
              <Row label="MSSV" value={flow.result.mssv} />
              <Row label="Sinh viên" value={flow.result.studentName} />
              <Row label="Số tiền" value={formatVnd(flow.result.amount)} strong />
              <Row
                label="Thời gian"
                value={new Date(flow.result.createdAt).toLocaleString('vi-VN')}
              />
            </div>
          )}

          <div className="mt-6 flex gap-3">
            {isSuccess ? (
              <>
                <Link
                  to="/lich-su"
                  onClick={reset}
                  className="flex-1 rounded-lg border border-border py-2.5 text-sm font-medium text-ink/70 hover:bg-canvas"
                >
                  Xem lịch sử
                </Link>
                <button
                  onClick={handleDone}
                  className="flex-1 rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-dark"
                >
                  Về trang chủ
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleDone}
                  className="flex-1 rounded-lg border border-border py-2.5 text-sm font-medium text-ink/70 hover:bg-canvas"
                >
                  Về trang chủ
                </button>
                <button
                  onClick={handleRetry}
                  className="flex-1 rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-dark"
                >
                  Thử lại
                </button>
              </>
            )}
          </div>
        </section>
      </div>
    </AppLayout>
  )
}

function Row({ label, value, strong }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-ink/60">{label}</span>
      <span className={`money text-sm ${strong ? 'font-semibold' : ''} text-ink`}>{value}</span>
    </div>
  )
}
