import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import * as api from '../services/mockApi'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // Khôi phục phiên đăng nhập khi tải lại trang (dữ liệu chỉ tồn tại trong
  // bộ nhớ của mockApi nên sau khi refresh trang, phiên demo sẽ mất - đây
  // là hành vi mong đợi cho một mock, không phải bug).
  useEffect(() => {
    setIsLoading(false)
  }, [])

  const login = useCallback(async (username, password) => {
    const { token: newToken, user: loggedInUser } = await api.login(username, password)
    setToken(newToken)
    setUser(loggedInUser)
    return loggedInUser
  }, [])

  const logout = useCallback(async () => {
    if (token) await api.logout(token)
    setToken(null)
    setUser(null)
  }, [token])

  const refreshUser = useCallback(async () => {
    if (!token) return
    const fresh = await api.getCurrentUser(token)
    setUser(fresh)
    return fresh
  }, [token])

  const value = {
    token,
    user,
    isAuthenticated: Boolean(token && user),
    isLoading,
    login,
    logout,
    refreshUser
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth phải được dùng bên trong <AuthProvider>')
  return ctx
}
