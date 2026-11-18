import { cn } from '@/lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'destructive'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
        {
          'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200': variant === 'default',
          'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200': variant === 'secondary',
          'border border-gray-300 bg-transparent dark:border-gray-600': variant === 'outline',
          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200': variant === 'destructive',
        },
        className
      )}
      {...props}
    />
  )
}