import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import PaymentLookupPage from './pages/PaymentLookupPage'
import PaymentConfirmPage from './pages/PaymentConfirmPage'
import OtpPage from './pages/OtpPage'
import ResultPage from './pages/ResultPage'
import HistoryPage from './pages/HistoryPage'
import ProfilePage from './pages/ProfilePage'

export default function App() {
  return (
    <Routes>
      <Route path="/dang-nhap" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/thanh-toan"
        element={
          <ProtectedRoute>
            <PaymentLookupPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/thanh-toan/xac-nhan"
        element={
          <ProtectedRoute>
            <PaymentConfirmPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/thanh-toan/otp"
        element={
          <ProtectedRoute>
            <OtpPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/thanh-toan/ket-qua"
        element={
          <ProtectedRoute>
            <ResultPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/lich-su"
        element={
          <ProtectedRoute>
            <HistoryPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ho-so"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
