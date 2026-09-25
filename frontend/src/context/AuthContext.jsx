import { createContext, useContext, useState, useEffect } from 'react';
import authService from '../services/authService'; 

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true); 

  const refreshUser = async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const userData = await authService.getMe();
        setUser(userData);
        return userData;
      } catch (error) {
        localStorage.removeItem('access_token');
        setUser(null);
      }
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      await refreshUser();
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (username, password) => {
    const data = await authService.login(username, password);
    localStorage.setItem('access_token', data.token);
    setUser(data.user);
  };

  const logout = async () => {
    try {
      await authService.logout(); 
    } catch (error) {
      console.error("API logout lỗi:", error);
    } finally {
      localStorage.removeItem('access_token');
      setUser(null); 
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, refreshUser, isLoading }}>
      {!isLoading && children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);