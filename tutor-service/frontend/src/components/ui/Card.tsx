import { forwardRef, HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'hover' | 'glass' | 'gradient'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ children, variant = 'default', padding = 'md', className, ...props }, ref) => {
    const variantStyles = {
      default: 'bg-white border border-gray-100 shadow-sm hover:shadow-md hover:border-gray-200',
      hover: 'bg-white border border-gray-100 shadow-sm hover:scale-[1.02] hover:shadow-xl hover:border-gray-200',
      glass: 'bg-white/80 backdrop-blur-xl border border-white/20 shadow-xl',
      gradient: 'bg-gradient-to-br from-primary-50 to-accent-50 border border-primary-100',
    }

    const paddingStyles = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    }

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-2xl transition-all duration-300 overflow-hidden',
          variantStyles[variant],
          paddingStyles[padding],
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('mb-4', className)} {...props} />
  )
)

CardHeader.displayName = 'CardHeader'

export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-xl font-bold text-gray-900', className)} {...props} />
  )
)

CardTitle.displayName = 'CardTitle'

export const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-gray-600 mt-1', className)} {...props} />
  )
)

CardDescription.displayName = 'CardDescription'

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('', className)} {...props} />
  )
)

CardContent.displayName = 'CardContent'

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('mt-4 pt-4 border-t border-gray-100 flex items-center', className)} {...props} />
  )
)

CardFooter.displayName = 'CardFooter'

// Lesson Card specific component
export function LessonCard({
  lesson,
  progress,
  onClick,
  isLocked = false,
}: {
  lesson: {
    id: string
    title: string
    description: string
    duration: number
    xpReward: number
    level: string
    focusArea: string
    tags: string[]
  }
  progress?: {
    status: 'not_started' | 'in_progress' | 'completed' | 'mastered'
    score?: number
    masteryLevel?: number
  }
  onClick?: () => void
  isLocked?: boolean
}) {
  const statusColors = {
    not_started: 'bg-gray-100 text-gray-500',
    in_progress: 'bg-primary-100 text-primary-700',
    completed: 'bg-green-100 text-green-700',
    mastered: 'bg-amber-100 text-amber-700',
  }

  const statusIcons = {
    not_started: '○',
    in_progress: '◐',
    completed: '✓',
    mastered: '★',
  }

  return (
    <Card
      variant="hover"
      onClick={onClick}
      className={cn('cursor-pointer', isLocked && 'opacity-50 cursor-not-allowed')}
    >
      <div className="flex items-start gap-4">
        {/* Status Indicator */}
        <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-2xl">
          <span className={cn(statusColors[progress?.status || 'not_started'])}>{statusIcons[progress?.status || 'not_started']}</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="badge-primary text-xs">{lesson.level}</span>
            <span className="badge text-xs bg-gray-100 text-gray-600">{lesson.focusArea}</span>
            {progress?.status === 'mastered' && <span className="badge-accent text-xs">Mastered</span>}
            {isLocked && <span className="badge-warning text-xs">Locked</span>}
          </div>

          <h3 className="font-semibold text-gray-900 mb-1">{lesson.title}</h3>
          <p className="text-gray-600 text-sm mb-3 line-clamp-2">{lesson.description}</p>

          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {lesson.duration} min
            </span>
            <span className="flex items-center gap-1 text-primary-600 font-medium">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              +{lesson.xpReward} XP
            </span>
          </div>

          {progress?.score && (
            <div className="mt-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-500">Progress</span>
                <span className="font-medium text-gray-900">{progress.masteryLevel || progress.score}%</span>
              </div>
              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                  style={{ width: `${progress.masteryLevel || progress.score}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Lock Icon */}
        {isLocked && (
          <div className="flex-shrink-0 ml-4">
            <svg className="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
        )}
      </div>
    </Card>
  )
}