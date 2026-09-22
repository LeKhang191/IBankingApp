import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AppLayout from '../components/AppLayout'

// Bỏ import mockApi đi và mang hàm formatVnd ra đây dùng tạm
export const formatVnd = (amount) => {
  return new Intl.NumberFormat('vi-VN').format(amount) + ' đ'
}

export default function DashboardPage() {
  const { user } = useAuth() // Bỏ biến token đi vì AuthContext không export biến này
  const [recentTransactions, setRecentTransactions] = useState([])
  const [isLoading, setIsLoading] = useState(false) // Đổi thành false vì không cần chờ tải

  useEffect(() => {
    // Tạm thời set mảng rỗng. 
    // Sau này bạn build xong payment-service thì sẽ gọi API thật ở đây!
    setRecentTransactions([])
  }, [])

  return (
    <AppLayout>
      <section className="mb-8 rounded-2xl bg-primary-dark p-8 text-white">
        <p className="text-sm text-white/70">Xin chào,</p>
        <h1 className="mt-1 text-xl font-semibold">{user?.name}</h1>
        <div className="mt-6">
          <p className="text-sm text-white/70">Số dư khả dụng</p>
          <p className="money mt-1 text-3xl font-bold">{formatVnd(user?.balance ?? 0)}</p>
        </div>
        <Link
          to="/thanh-toan"
          className="mt-6 inline-block rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-primary-dark transition-transform hover:scale-[1.02]"
        >
          Thanh toán học phí
        </Link>
      </section>

      <section className="grid gap-6 sm:grid-cols-3">
        <InfoCard label="Số điện thoại" value={user?.phone} />
        <InfoCard label="Email" value={user?.email} />
        <InfoCard label="Trạng thái tài khoản" value="Đang hoạt động" accent="success" />
      </section>

      <section className="mt-10">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Giao dịch gần đây</h2>
          <Link to="/lich-su" className="text-sm font-medium text-primary hover:underline">
            Xem tất cả
          </Link>
        </div>

        <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-card">
          {isLoading ? (
            <p className="px-5 py-6 text-sm text-ink/50">Đang tải...</p>
          ) : recentTransactions.length === 0 ? (
            <p className="px-5 py-6 text-sm text-ink/50">Bạn chưa có giao dịch nào.</p>
          ) : (
            recentTransactions.map((txn) => (
              <div
                key={txn.id}
                className="flex items-center justify-between border-b border-border px-5 py-4 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium text-ink">
                    Học phí MSSV {txn.mssv} — {txn.studentName}
                  </p>
                  <p className="text-xs text-ink/50">
                    {new Date(txn.createdAt).toLocaleString('vi-VN')}
                  </p>
                </div>
                <p className="money text-sm font-semibold text-danger">-{formatVnd(txn.amount)}</p>
              </div>
            ))
          )}
        </div>
      </section>
    </AppLayout>
  )
}

function InfoCard({ label, value, accent }) {
  return (
    <div className="rounded-2xl border border-border bg-white p-5 shadow-card">
      <p className="text-xs text-ink/50">{label}</p>
      <p className={`mt-1.5 text-sm font-medium ${accent === 'success' ? 'text-success' : 'text-ink'}`}>
        {value}
      </p>
    </div>
  )
}
