import { Bell, Search, Menu, Sun, Moon, Globe, ChevronDown, LogOut, User, Settings, Award } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'

interface HeaderProps {
  onMenuClick: () => void
  user: { name: string; avatar?: string; streak: number } | null
}

export function Header({ onMenuClick, user }: HeaderProps) {
  const [isDark, setIsDark] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const notificationsRef = useRef<HTMLDivElement>(null)
  const profileRef = useRef<HTMLDivElement>(null)
  const { logout } = useAuth()

  // Toggle theme
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const shouldBeDark = savedTheme ? savedTheme === 'dark' : prefersDark
    setIsDark(shouldBeDark)
    document.documentElement.classList.toggle('dark', shouldBeDark)
  }, [])

  const toggleTheme = () => {
    const newTheme = !isDark
    setIsDark(newTheme)
    localStorage.setItem('theme', newTheme ? 'dark' : 'light')
    document.documentElement.classList.toggle('dark', newTheme)
  }

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const mockNotifications = [
    { id: 1, title: 'Lesson Complete', message: 'You completed "Spanish Basics 1"', time: '2h ago', read: false },
    { id: 2, title: 'Streak Milestone', message: '🔥 7-day streak achieved!', time: '5h ago', read: false },
    { id: 3, title: 'New Content', message: 'New pronunciation exercises added', time: '1d ago', read: true },
  ]

  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-gray-200">
      <div className="flex items-center justify-between h-16 px-4 lg:px-8">
        {/* Left: Menu button + Search */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-xl text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            aria-label="Open menu"
          >
            <Menu className="w-6 h-6" />
          </button>

          <div className="hidden sm:block relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" aria-hidden="true" />
            <input
              type="search"
              placeholder="Search lessons, vocabulary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 sm:w-80 pl-10 pr-4 py-2 rounded-xl bg-gray-50 border border-gray-200 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              aria-label="Search"
            />
          </div>
        </div>

        {/* Right: Theme, Notifications, Profile */}
        <div className="flex items-center gap-2">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={cn(
              'p-2 rounded-xl transition-colors',
              isDark ? 'bg-gray-800 text-amber-400' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>

          {/* Language Selector */}
          <div className="relative">
            <button className="flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 text-gray-700 text-sm font-medium transition-colors">
              <Globe className="w-4 h-4" />
              <span>EN → ES</span>
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>

          {/* Notifications */}
          <div className="relative" ref={notificationsRef}>
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className={cn(
                'p-2 rounded-xl relative transition-colors',
                notificationsOpen ? 'bg-primary-50 text-primary-600' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              )}
              aria-label="Notifications"
              aria-expanded={notificationsOpen}
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            </button>

            {notificationsOpen && (
              <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-xl border border-gray-200 py-2 animate-in">
                <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">Notifications</h3>
                  <button className="text-sm text-primary-600 hover:text-primary-700">Mark all read</button>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {mockNotifications.map((notif) => (
                    <button
                      key={notif.id}
                      className={cn(
                        'w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors',
                        !notif.read && 'bg-primary-50/50'
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0', !notif.read ? 'bg-primary-100' : 'bg-gray-100')}>
                          <Bell className={cn('w-4 h-4', !notif.read ? 'text-primary-600' : 'text-gray-400')} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={cn('font-medium text-gray-900', !notif.read && 'font-semibold')}>{notif.title}</p>
                          <p className="text-sm text-gray-600 truncate">{notif.message}</p>
                          <p className="text-xs text-gray-400 mt-1">{notif.time}</p>
                        </div>
                        {!notif.read && <div className="w-1.5 h-1.5 rounded-full bg-primary-500 mt-2 flex-shrink-0" />}
                      </div>
                    </button>
                  ))}
                </div>
                <div className="px-4 py-3 border-t border-gray-100">
                  <a href="#" className="text-sm text-primary-600 hover:text-primary-700 font-medium">View all notifications</a>
                </div>
              </div>
            )}
          </div>

          {/* Profile Menu */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-gray-100 transition-colors"
              aria-label="Profile menu"
              aria-expanded={profileOpen}
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-medium">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <span className="hidden md:block font-medium text-gray-700">{user?.name}</span>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>

            {profileOpen && (
              <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-2xl shadow-xl border border-gray-200 py-2 animate-in">
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="font-semibold text-gray-900">{user?.name}</p>
                  <p className="text-sm text-gray-500">🔥 {user?.streak} day streak</p>
                </div>
                <NavLink
                  to="/settings"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-gray-700 hover:bg-gray-50"
                >
                  <Settings className="w-5 h-5" />
                  Settings
                </NavLink>
                <NavLink
                  to="/progress"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-gray-700 hover:bg-gray-50"
                >
                  <Award className="w-5 h-5" />
                  Achievements
                </NavLink>
                <button
                  onClick={logout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-red-600 hover:bg-red-50"
                >
                  <LogOut className="w-5 h-5" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}