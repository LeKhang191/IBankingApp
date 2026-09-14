import React from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { formatVnd } from '../services/mockApi'

const NAV_ITEMS = [
  { to: '/', label: 'Trang chủ' },
  { to: '/thanh-toan', label: 'Thanh toán học phí' },
  { to: '/lich-su', label: 'Lịch sử giao dịch' },
  { to: '/ho-so', label: 'Hồ sơ' }
]

export default function AppLayout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  async function handleLogout() {
    await logout()
    navigate('/dang-nhap', { replace: true })
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-8">
            <Link to="/" className="text-lg font-semibold text-primary-dark">
              iBanking
            </Link>
            <nav className="hidden gap-6 md:flex">
              {NAV_ITEMS.map((item) => {
                const active = location.pathname === item.to
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`text-sm font-medium transition-colors ${
                      active ? 'text-primary' : 'text-ink/60 hover:text-ink'
                    }`}
                  >
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </div>

          {user && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-ink">{user.name}</p>
                <p className="money text-xs text-ink/50">{formatVnd(user.balance)}</p>
              </div>
              <button
                onClick={handleLogout}
                className="rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-ink/70 hover:bg-canvas"
              >
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
    </div>
  )
}
