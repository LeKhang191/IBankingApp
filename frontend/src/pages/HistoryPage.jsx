import React, { useCallback, useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import paymentService from '../services/paymentService'
import { formatVnd } from '../utils/format'

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('vi-VN')
}

function shortId(id) {
  const text = String(id || '')
  return text.length > 18 ? `${text.slice(0, 10)}…${text.slice(-6)}` : text || '—'
}

export default function HistoryPage() {
  const [transactions, setTransactions] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const retry = useCallback(() => setReloadKey((key) => key + 1), [])

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError('')

    paymentService.getHistory()
      .then((data) => {
        if (cancelled) return
        const list = Array.isArray(data) ? data : data?.transactions
        if (!Array.isArray(list)) {
          throw new Error('Dữ liệu lịch sử giao dịch không đúng định dạng')
        }
        setTransactions(list)
      })
      .catch((err) => {
        if (cancelled) return
        console.error('Không thể tải lịch sử thanh toán:', err)
        setTransactions([])
        setError('Không thể tải lịch sử thanh toán. Vui lòng thử lại.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => { cancelled = true }
  }, [reloadKey])

  return (
    <AppLayout>
      <h1 className="mb-1 text-lg font-semibold text-ink">Lịch sử giao dịch</h1>
      <p className="mb-6 text-sm text-ink/60">Các khoản học phí đã thanh toán thành công từ tài khoản của bạn.</p>

      <div className="min-w-0 overflow-hidden rounded-xl border border-border bg-white shadow-card">
        {isLoading ? (
          <p className="px-5 py-8 text-sm text-ink/60" role="status">Đang tải lịch sử thanh toán...</p>
        ) : error ? (
          <div className="px-5 py-8" role="alert">
            <p className="text-sm text-danger">{error}</p>
            <button type="button" onClick={retry} className="mt-3 border border-border px-4 py-2 text-sm font-medium text-primary hover:bg-canvas">
              Thử lại
            </button>
          </div>
        ) : transactions.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-ink/60">Bạn chưa có giao dịch thanh toán thành công nào.</p>
        ) : (
          <>
            {/* Mobile: cards avoid horizontal overflow from long transaction IDs. */}
            <div className="divide-y divide-border md:hidden">
              {transactions.map((txn, index) => (
                <article key={txn.id || index} className="min-w-0 space-y-3 p-4">
                  <div className="flex min-w-0 items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink" title={txn.studentName || txn.student_name || ''}>
                        {txn.studentName || txn.student_name || 'Sinh viên'}
                      </p>
                      <p className="mt-1 text-xs text-ink/60">MSSV: {txn.mssv || '—'}</p>
                    </div>
                    <p className="money shrink-0 text-right text-sm font-semibold text-danger">-{formatVnd(txn.amount)}</p>
                  </div>
                  <div className="flex items-center justify-between gap-3 text-xs text-ink/60">
                    <time>{formatDate(txn.createdAt || txn.created_at)}</time>
                    <span className="max-w-[55%] truncate font-mono" title={String(txn.id || '')}>{shortId(txn.id)}</span>
                  </div>
                </article>
              ))}
            </div>

            {/* Desktop: bounded table with shortened transaction IDs. */}
            <div className="hidden w-full overflow-x-auto md:block">
              <table className="w-full table-fixed text-left text-sm">
                <thead className="bg-canvas">
                  <tr className="border-b border-border text-xs text-ink/60">
                    <th className="w-[23%] px-4 py-3 font-medium">Mã giao dịch</th>
                    <th className="w-[14%] px-4 py-3 font-medium">MSSV</th>
                    <th className="w-[25%] px-4 py-3 font-medium">Sinh viên</th>
                    <th className="w-[20%] px-4 py-3 font-medium">Thời gian</th>
                    <th className="w-[18%] px-4 py-3 text-right font-medium">Số tiền</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn, index) => (
                    <tr key={txn.id || index} className="border-b border-border last:border-b-0 hover:bg-canvas/70">
                      <td className="min-w-0 px-4 py-4 font-mono text-xs text-ink/70" title={String(txn.id || '')}>
                        <span className="block truncate">{shortId(txn.id)}</span>
                      </td>
                      <td className="px-4 py-4 text-ink">{txn.mssv || '—'}</td>
                      <td className="min-w-0 px-4 py-4 text-ink" title={txn.studentName || txn.student_name || ''}>
                        <span className="block truncate">{txn.studentName || txn.student_name || '—'}</span>
                      </td>
                      <td className="px-4 py-4 text-xs text-ink/60">{formatDate(txn.createdAt || txn.created_at)}</td>
                      <td className="money whitespace-nowrap px-4 py-4 text-right font-semibold text-danger">-{formatVnd(txn.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  )
}
