import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 0) {
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  return `${secs}s`
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

export function formatXP(xp: number): string {
  if (xp >= 1000000) {
    return `${(xp / 1000000).toFixed(1)}M`
  }
  if (xp >= 1000) {
    return `${(xp / 1000).toFixed(1)}K`
  }
  return xp.toString()
}

export function getLevelFromXP(xp: number): { level: number; progress: number; nextLevelXP: number } {
  // Exponential XP curve: level n requires n^2 * 100 XP
  let level = 1
  let totalXP = 0
  let nextLevelXP = 100

  while (totalXP + nextLevelXP <= xp) {
    totalXP += nextLevelXP
    level++
    nextLevelXP = level * level * 100
  }

  const progress = ((xp - totalXP) / nextLevelXP) * 100
  return { level, progress: Math.min(100, Math.max(0, progress)), nextLevelXP }
}

export function getCEFRColor(level: string): string {
  const colors: Record<string, string> = {
    A1: 'bg-green-500',
    A2: 'bg-lime-500',
    B1: 'bg-yellow-500',
    B2: 'bg-amber-500',
    C1: 'bg-orange-500',
    C2: 'bg-red-500',
  }
  return colors[level] || 'bg-gray-500'
}

export function getCEFRGradient(level: string): string {
  const gradients: Record<string, string> = {
    A1: 'from-green-500 to-emerald-500',
    A2: 'from-lime-500 to-green-500',
    B1: 'from-yellow-500 to-lime-500',
    B2: 'from-amber-500 to-yellow-500',
    C1: 'from-orange-500 to-amber-500',
    C2: 'from-red-500 to-orange-500',
  }
  return gradients[level] || 'from-gray-500 to-gray-400'
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function getLanguageFlag(code: string): string {
  const flags: Record<string, string> = {
    en: '🇺🇸',
    es: '🇪🇸',
    fr: '🇫🇷',
    de: '🇩🇪',
    it: '🇮🇹',
    pt: '🇵🇹',
    ja: '🇯🇵',
    ko: '🇰🇷',
    zh: '🇨🇳',
    ru: '🇷🇺',
    ar: '🇸🇦',
    hi: '🇮🇳',
    nl: '🇳🇱',
    pl: '🇵🇱',
    tr: '🇹🇷',
    sv: '🇸🇪',
    da: '🇩🇰',
    no: '🇳🇴',
    fi: '🇫🇮',
    cs: '🇨🇿',
    hu: '🇭🇺',
    ro: '🇷🇴',
    uk: '🇺🇦',
    el: '🇬🇷',
    he: '🇮🇱',
    th: '🇹🇭',
    vi: '🇻🇳',
    id: '🇮🇩',
    ms: '🇲🇾',
    tl: '🇵🇭',
    sw: '🇰🇪',
    fa: '🇮🇷',
  }
  return flags[code] || '🌐'
}

export function getRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export function truncate(text: string, length: number): string {
  if (text.length <= length) return text
  return text.slice(0, length - 3) + '...'
}

export function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const groupKey = String(item[key])
    if (!groups[groupKey]) {
      groups[groupKey] = []
    }
    groups[groupKey].push(item)
    return groups
  }, {} as Record<string, T[]>)
}