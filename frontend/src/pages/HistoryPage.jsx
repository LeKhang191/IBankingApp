import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import AppLayout from '../components/AppLayout'
import * as api from '../services/mockApi'
import { formatVnd } from '../services/mockApi'

export default function HistoryPage() {
  const { token } = useAuth()
  const [transactions, setTransactions] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    api.getHistory(token).then((data) => {
      setTransactions(data)
      setIsLoading(false)
    })
  }, [token])

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
                  <td className="px-5 py-3 text-ink/70">{txn.id.split('_')[1]}</td>
                  <td className="px-5 py-3">{txn.mssv}</td>
                  <td className="px-5 py-3">{txn.studentName}</td>
                  <td className="px-5 py-3 text-ink/60">
                    {new Date(txn.createdAt).toLocaleString('vi-VN')}
                  </td>
                  <td className="money px-5 py-3 text-right font-medium">{formatVnd(txn.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppLayout>
  )
}
