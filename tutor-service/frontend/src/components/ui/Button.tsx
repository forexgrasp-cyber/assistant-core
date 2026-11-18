import { forwardRef, ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'accent' | 'outline' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]'

    const variantStyles = {
      primary: 'bg-primary-600 text-white hover:bg-primary-700 focus-visible:ring-primary-500 shadow-lg shadow-primary-500/25',
      secondary: 'bg-white text-gray-700 hover:bg-gray-50 focus-visible:ring-gray-500 border border-gray-200 shadow-sm',
      ghost: 'bg-transparent text-gray-600 hover:bg-gray-100 focus-visible:ring-gray-500',
      accent: 'bg-accent-600 text-white hover:bg-accent-700 focus-visible:ring-accent-500 shadow-lg shadow-accent-500/25',
      outline: 'border-2 border-primary-600 text-primary-600 hover:bg-primary-50 focus-visible:ring-primary-500',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500 shadow-lg shadow-red-500/25',
    }

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-sm gap-1.5',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
      icon: 'p-2.5',
    }

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], fullWidth && 'w-full', className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <svg className="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : (
          <>
            {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
            {children}
            {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

// Icon Button variant
export function IconButton({
  children,
  variant = 'ghost',
  size = 'md',
  className,
  ...props
}: Omit<ButtonProps, 'leftIcon' | 'rightIcon' | 'fullWidth'>) {
  return (
    <Button variant={variant} size={size} className={cn('p-0', className)} {...props}>
      {children}
    </Button>
  )
}

// Floating Action Button
export function FAB({
  children,
  className,
  ...props
}: React.ComponentPropsWithoutRef<'button'>) {
  return (
    <button
      className={cn(
        'fixed bottom-6 right-6 z-40 p-4 rounded-2xl bg-primary-600 text-white shadow-xl shadow-primary-500/30 hover:bg-primary-700 hover:shadow-2xl hover:shadow-primary-500/40 transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}