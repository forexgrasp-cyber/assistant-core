export interface NavigationItem {
  href: string
  label: string
  icon: string
  view: 'dashboard' | 'curriculum' | 'lesson' | 'practice' | 'progress' | 'settings' | 'generator'
}