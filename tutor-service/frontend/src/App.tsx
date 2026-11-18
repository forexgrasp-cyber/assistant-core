import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { Dashboard } from '@/pages/Dashboard'
import Curriculum from '@/pages/Curriculum'
import { LessonGeneratorPage as LessonGenerator } from '@/pages/LessonGenerator'
import { LessonPlayer } from '@/pages/LessonPlayer'
import { Practice } from '@/pages/Practice'
import { Progress } from '@/pages/Progress'
import { Settings } from '@/pages/Settings'
import { AuthLayout } from '@/layouts/AuthLayout'
import { MainLayout } from '@/layouts/MainLayout'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useAuth } from '@/contexts/AuthContext'
import { OfflineProvider } from '@/contexts/OfflineContext'

// Lazy load heavy pages
const LessonPlayerLazy = lazy(() => import('@/pages/LessonPlayer').then((m) => ({ default: m.LessonPlayer })))
const PracticeLazy = lazy(() => import('@/pages/Practice').then((m) => ({ default: m.Practice })))
const LessonGeneratorLazy = lazy(() => import('@/pages/LessonGenerator').then((m) => ({ default: m.LessonGeneratorPage })))

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function AppRoutes() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <AuthLayout>
              <LoginPage />
            </AuthLayout>
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <AuthLayout>
              <RegisterPage />
            </AuthLayout>
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="curriculum" element={<Curriculum />} />
        <Route path="lesson-generator" element={<Suspense fallback={<LoadingSpinner />}><LessonGeneratorLazy /></Suspense>} />
        <Route path="lesson/:lessonId" element={<Suspense fallback={<LoadingSpinner />}><LessonPlayerLazy /></Suspense>} />
        <Route path="practice" element={<Suspense fallback={<LoadingSpinner />}><PracticeLazy /></Suspense>} />
        <Route path="progress" element={<Progress />} />
        <Route path="settings" element={<Settings />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <OfflineProvider>
      <AppRoutes />
    </OfflineProvider>
  )
}

// Login Page Component
function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
    } catch {
      setError('Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold gradient-text">Welcome Back</h1>
        <p className="text-gray-600 mt-2">Sign in to continue your language journey</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            placeholder="you@example.com"
            required
            autoComplete="email"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            placeholder="••••••••"
            required
            autoComplete="current-password"
          />
        </div>

        <button type="submit" className="btn-primary w-full" disabled={isLoading}>
          {isLoading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>

      <p className="text-center text-gray-600 mt-6">
        Don't have an account?{' '}
        <a href="/register" className="text-primary-600 hover:text-primary-700 font-medium">
          Sign up
        </a>
      </p>
    </div>
  )
}

// Register Page Component
function RegisterPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    nativeLanguage: 'en',
    targetLanguage: 'es',
    cefrLevel: 'A1',
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { register } = useAuth()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)
    try {
      await register({
        email: formData.email,
        password: formData.password,
        name: formData.name,
        nativeLanguage: formData.nativeLanguage,
        targetLanguage: formData.targetLanguage,
        cefrLevel: formData.cefrLevel,
      })
    } catch {
      setError('Registration failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const languages = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'it', name: 'Italian' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'ja', name: 'Japanese' },
    { code: 'ko', name: 'Korean' },
    { code: 'zh', name: 'Chinese' },
  ]

  const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold gradient-text">Create Account</h1>
        <p className="text-gray-600 mt-2">Start your language learning journey today</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
            Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            className="input"
            placeholder="Your name"
            required
            autoComplete="name"
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            className="input"
            placeholder="you@example.com"
            required
            autoComplete="email"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            className="input"
            placeholder="At least 8 characters"
            required
            autoComplete="new-password"
            minLength={8}
          />
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={handleChange}
            className="input"
            placeholder="Confirm your password"
            required
            autoComplete="new-password"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="nativeLanguage" className="block text-sm font-medium text-gray-700 mb-2">
              Native Language
            </label>
            <select
              id="nativeLanguage"
              name="nativeLanguage"
              value={formData.nativeLanguage}
              onChange={handleChange}
              className="input"
            >
              {languages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="targetLanguage" className="block text-sm font-medium text-gray-700 mb-2">
              Target Language
            </label>
            <select
              id="targetLanguage"
              name="targetLanguage"
              value={formData.targetLanguage}
              onChange={handleChange}
              className="input"
            >
              {languages.filter((l) => l.code !== formData.nativeLanguage).map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="cefrLevel" className="block text-sm font-medium text-gray-700 mb-2">
            Current Level
          </label>
          <select
            id="cefrLevel"
            name="cefrLevel"
            value={formData.cefrLevel}
            onChange={handleChange}
            className="input"
          >
            {levels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </div>

        <button type="submit" className="btn-primary w-full" disabled={isLoading}>
          {isLoading ? 'Creating account...' : 'Create Account'}
        </button>
      </form>

      <p className="text-center text-gray-600 mt-6">
        Already have an account?{' '}
        <a href="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          Sign in
        </a>
      </p>
    </div>
  )
}

// Import useState for the page components
import { useState } from 'react'