import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import type { User } from '@/types'
import { useTutorStore } from '@/stores/tutorStore'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  updateProfile: (updates: Partial<User>) => Promise<void>
}

interface RegisterData {
  email: string
  password: string
  name: string
  nativeLanguage: string
  targetLanguage: string
  cefrLevel: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true)
  const { user, setUser, updateUser } = useTutorStore()

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // In a real app, this would validate a JWT token with the backend
        const storedUser = localStorage.getItem('tutor-user')
        if (storedUser) {
          setUser(JSON.parse(storedUser))
        }
      } catch (error) {
        console.error('Auth check failed:', error)
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [setUser])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // Mock user - in real app, this comes from backend
      const mockUser: User = {
        id: 'user-1',
        email,
        name: email.split('@')[0],
        nativeLanguage: 'en',
        targetLanguage: 'es',
        cefrLevel: 'A1',
        streak: 7,
        xp: 1250,
        createdAt: new Date().toISOString(),
      }

      localStorage.setItem('tutor-user', JSON.stringify(mockUser))
      setUser(mockUser)
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (data: RegisterData) => {
    setIsLoading(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000))

      const newUser: User = {
        id: `user-${Date.now()}`,
        email: data.email,
        name: data.name,
        nativeLanguage: data.nativeLanguage,
        targetLanguage: data.targetLanguage,
        cefrLevel: data.cefrLevel,
        streak: 0,
        xp: 0,
        createdAt: new Date().toISOString(),
      }

      localStorage.setItem('tutor-user', JSON.stringify(newUser))
      setUser(newUser)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('tutor-user')
    setUser(null)
  }

  const updateProfile = async (updates: Partial<User>) => {
    try {
      if (user) {
        const updatedUser = { ...user, ...updates }
        localStorage.setItem('tutor-user', JSON.stringify(updatedUser))
        updateUser(updates)
      }
    } catch (error) {
      console.error('Profile update failed:', error)
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}