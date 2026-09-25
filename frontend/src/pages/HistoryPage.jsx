import React, { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import tuitionService from '../services/tuitionService'

const formatVnd = (amount) => {
  return new Intl.NumberFormat('vi-VN').format(amount) + ' đ'
}

export default function HistoryPage() {
  const [transactions, setTransactions] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let ignore = false

    async function fetchHistory() {
      try {
        const data = await tuitionService.getHistory()
        if (!ignore) {
          setTransactions(data || [])
        }
      } catch (error) {
        console.error('Lỗi lấy lịch sử giao dịch:', error)
      } finally {
        if (!ignore) {
          setIsLoading(false)
        }
      }
    }

    fetchHistory()

    return () => {
      ignore = true
    }
  }, [])

  return (
    <AppLayout>
      <h1 className="mb-1 text-lg font-semibold text-ink">Lịch sử giao dịch</h1>
      <p className="mb-6 text-sm text-ink/60">Toàn bộ các giao dịch đóng học phí bạn đã thực hiện.</p>

      <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-card">
        {isLoading ? (
          <p className="px-5 py-6 text-sm text-ink/50">Đang tải...</p>
        ) : transactions.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <p className="text-sm text-ink/50">Bạn chưa thực hiện giao dịch nào.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-ink/50">
                <th className="px-5 py-3 font-medium">Mã giao dịch</th>
                <th className="px-5 py-3 font-medium">MSSV</th>
                <th className="px-5 py-3 font-medium">Sinh viên</th>
                <th className="px-5 py-3 font-medium">Thời gian</th>
                <th className="px-5 py-3 text-right font-medium">Số tiền</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((txn) => (
                <tr key={txn.id} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 font-mono text-xs text-ink/70">{txn.id}</td>
                  <td className="px-5 py-3">{txn.mssv}</td>
                  <td className="px-5 py-3">{txn.studentName}</td>
                  <td className="px-5 py-3 text-ink/60">
                    {txn.createdAt ? new Date(txn.createdAt).toLocaleString('vi-VN') : '—'}
                  </td>
                  <td className="money px-5 py-3 text-right font-medium text-danger">
                    -{formatVnd(txn.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppLayout>
  )
}