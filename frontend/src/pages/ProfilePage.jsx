import React from 'react'
import { useAuth } from '../context/AuthContext'
import AppLayout from '../components/AppLayout'
import { formatVnd } from '../services/mockApi'

export default function ProfilePage() {
  const { user } = useAuth()

  return (
    <AppLayout>
      <h1 className="mb-6 text-lg font-semibold text-ink">Hồ sơ cá nhân</h1>

      <div className="max-w-md rounded-2xl border border-border bg-white p-6 shadow-card">
        <Field label="Họ và tên" value={user?.name} />
        <Field label="Số điện thoại" value={user?.phone} />
        <Field label="Email" value={user?.email} />
        <Field label="Số dư khả dụng" value={formatVnd(user?.balance ?? 0)} strong />
      </div>
    </AppLayout>
  )
}

function Field({ label, value, strong }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-3 last:border-0">
      <span className="text-sm text-ink/60">{label}</span>
      <span className={`money text-sm ${strong ? 'font-semibold text-primary-dark' : 'text-ink'}`}>
        {value}
      </span>
    </div>
  )
}
