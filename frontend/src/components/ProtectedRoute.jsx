import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user } = useAuth()
  
  const token = localStorage.getItem('access_token')

  if (!user && !token) {
    return <Navigate to="/dang-nhap" replace />
  }

  return children
}