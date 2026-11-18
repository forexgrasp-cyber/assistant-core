import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  Mic,
  BarChart,
  Settings,
  ChevronLeft,
  ChevronRight,
  X,
  Target,
  Flame,
  Award,
  User,
  LogOut,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTutorStore } from '@/stores/tutorStore'
import type { NavigationItem } from './Sidebar.types'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  navigation: NavigationItem[]
  currentView: string
  onViewChange: (view: string) => void
  user: { name: string; avatar?: string; streak: number; xp: number } | null
  mobileSidebarOpen: boolean
  setMobileSidebarOpen: (open: boolean) => void
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  BookOpen,
  Mic,
  BarChart,
  Settings,
  Target,
  Flame,
  Award,
  User,
  LogOut,
  Zap,
}

export function Sidebar({
  isOpen,
  onClose,
  navigation,
  currentView,
  onViewChange,
  user,
  mobileSidebarOpen,
  setMobileSidebarOpen,
}: SidebarProps) {
  const { dailyGoalMinutes, targetLanguage, nativeLanguage, userProgress } = useTutorStore()
  const streak = userProgress?.streak ?? 0
  const xp = userProgress?.xp ?? 0

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 h-screen z-50 bg-white border-r border-gray-200 transition-all duration-300 flex flex-col',
          isOpen ? 'w-64' : 'w-20',
          mobileSidebarOpen && 'lg:hidden'
        )}
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-100">
          <NavLink to="/dashboard" className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
            </div>
            {isOpen && (
              <span className="text-xl font-bold gradient-text">LinguaFlow</span>
            )}
          </NavLink>

          {/* Collapse/Expand button (desktop only) */}
          {!mobileSidebarOpen && (
            <button
              onClick={onClose}
              className={cn(
                'p-1.5 rounded-xl text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors',
                isOpen && 'rotate-180'
              )}
              aria-label={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {isOpen ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
            </button>
          )}
        </div>

        {/* User Progress Summary (when expanded) */}
        {isOpen && user && (
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-medium">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{user.name}</p>
                <p className="text-sm text-gray-500">{nativeLanguage} → {targetLanguage}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-gray-50 rounded-xl">
                <div className="text-2xl font-bold gradient-text">{streak}</div>
                <div className="text-xs text-gray-500">Day Streak</div>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl">
                <div className="text-2xl font-bold gradient-text">{xp.toLocaleString()}</div>
                <div className="text-xs text-gray-500">XP</div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto" aria-label="Main navigation">
          {navigation.map((item) => {
            const Icon = iconMap[item.icon]
            const isActive = currentView === item.view

            return (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={() => {
                  onViewChange(item.view)
                  if (mobileSidebarOpen) setMobileSidebarOpen(false)
                }}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                  !isOpen && 'justify-center'
                )}
                aria-current={isActive ? 'page' : undefined}
                title={isOpen ? undefined : item.label}
              >
                <Icon className={cn('w-5 h-5 flex-shrink-0', isActive && 'text-primary-600')} aria-hidden="true" />
                {isOpen && <span className="font-medium">{item.label}</span>}
                {isActive && isOpen && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-500" aria-hidden="true" />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Daily Goal Progress */}
        {isOpen && (
          <div className="p-4 border-t border-gray-100">
            <div className="mb-3">
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-gray-700">Daily Goal</span>
                <span className="text-gray-500">{dailyGoalMinutes} min</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-500"
                  style={{ width: '65%' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Bottom: Settings & Logout */}
        {isOpen && (
          <div className="p-3 border-t border-gray-100 space-y-1">
            <NavLink
              to="/settings"
              onClick={() => setMobileSidebarOpen(false)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            >
              <Settings className="w-5 h-5" aria-hidden="true" />
              <span className="font-medium">Settings</span>
            </NavLink>
            <button
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            >
              <LogOut className="w-5 h-5" aria-hidden="true" />
              <span className="font-medium">Sign Out</span>
            </button>
          </div>
        )}
      </aside>

      {/* Mobile Sidebar Close Button */}
      {mobileSidebarOpen && (
        <button
          onClick={() => setMobileSidebarOpen(false)}
          className="fixed left-64 top-4 z-50 lg:hidden p-2 rounded-xl bg-white shadow-lg text-gray-500 hover:text-gray-700"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      )}
    </>
  )
}