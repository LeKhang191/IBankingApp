import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { usePaymentFlow } from '../context/PaymentFlowContext'
import AppLayout from '../components/AppLayout'
import StepIndicator from '../components/StepIndicator'
import * as api from '../services/mockApi'
import { formatVnd } from '../services/mockApi'

export default function PaymentLookupPage() {
  const { token } = useAuth()
  const { setTuition } = usePaymentFlow()
  const navigate = useNavigate()

  const [mssv, setMssv] = useState('')
  const [error, setError] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [result, setResult] = useState(null)

  async function handleSearch(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    if (!mssv.trim()) return
    setIsSearching(true)
    try {
      const tuition = await api.lookupTuition(token, mssv.trim())
      setResult(tuition)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSearching(false)
    }
  }

  function handleContinue() {
    setTuition(result)
    navigate('/thanh-toan/xac-nhan')
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-lg">
        <StepIndicator current="lookup" />

        <section className="rounded-2xl border border-border bg-white p-6 shadow-card">
          <h1 className="text-base font-semibold text-ink">Tra cứu học phí</h1>
          <p className="mt-1 text-sm text-ink/60">
            Nhập mã số sinh viên cần đóng học phí. Bạn có thể đóng cho chính mình hoặc cho sinh viên khác.
          </p>

          <form onSubmit={handleSearch} className="mt-5 flex gap-2">
            <input
              value={mssv}
              onChange={(e) => setMssv(e.target.value)}
              placeholder="Nhập MSSV, ví dụ: 52100001"
              className="flex-1 rounded-lg border border-border px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
            >
              {isSearching ? 'Đang tra cứu...' : 'Tra cứu'}
            </button>
          </form>

          {error && (
            <p className="mt-4 rounded-lg bg-danger-light px-3 py-2 text-sm text-danger">{error}</p>
          )}

          {result && (
            <div className="mt-5 rounded-xl border border-border bg-canvas p-4">
              <Row label="MSSV" value={result.mssv} />
              <Row label="Họ và tên sinh viên" value={result.studentName} />
              <Row label="Số tiền cần đóng" value={formatVnd(result.amount)} strong />

              <button
                onClick={handleContinue}
                className="mt-4 w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-dark"
              >
                Tiếp tục
              </button>
            </div>
          )}
        </section>

        <p className="mt-4 text-center text-xs text-ink/40">
          Demo MSSV: 52100001, 52100002, 52100003 (chưa đóng) — 52100004 (đã đóng)
        </p>
      </div>
    </AppLayout>
  )
}

function Row({ label, value, strong }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-ink/60">{label}</span>
      <span className={`money text-sm ${strong ? 'font-semibold text-ink' : 'text-ink'}`}>{value}</span>
    </div>
  )
}
