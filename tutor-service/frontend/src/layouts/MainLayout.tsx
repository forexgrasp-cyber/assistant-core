import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { useTutorStore } from '@/stores/tutorStore'

export function MainLayout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const { sidebarOpen, setSidebarOpen, user, view, setView } = useTutorStore()
  const location = useLocation()

  const navigation = [
    { href: '/dashboard', label: 'Dashboard', icon: 'LayoutDashboard', view: 'dashboard' as const },
    { href: '/curriculum', label: 'Curriculum', icon: 'BookOpen', view: 'curriculum' as const },
    { href: '/lesson-generator', label: 'AI Generator', icon: 'Zap', view: 'generator' as const },
    { href: '/practice', label: 'Practice', icon: 'Mic', view: 'practice' as const },
    { href: '/progress', label: 'Progress', icon: 'BarChart', view: 'progress' as const },
    { href: '/settings', label: 'Settings', icon: 'Settings', view: 'settings' as const },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        navigation={navigation}
        currentView={view}
        onViewChange={setView}
        user={user}
        mobileSidebarOpen={mobileSidebarOpen}
        setMobileSidebarOpen={setMobileSidebarOpen}
      />

      {/* Main content */}
      <div className={`lg:pl-64 transition-all duration-300 ${sidebarOpen ? 'pl-64' : 'pl-20'}`}>
        {/* Header */}
        <Header
          onMenuClick={() => setMobileSidebarOpen(true)}
          user={user}
        />

        {/* Page content */}
        <main className="p-4 lg:p-8 pb-20">
          <Outlet />
        </main>
      </div>
    </div>
  )
}