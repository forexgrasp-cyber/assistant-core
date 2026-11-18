import { createContext, useContext, useState, useRef, useEffect, ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp, Check } from 'lucide-react'

interface SelectContextType {
  value: string
  onValueChange: (value: string) => void
  open: boolean
  setOpen: (open: boolean) => void
  triggerRef: React.RefObject<HTMLButtonElement>
  contentRef: React.RefObject<HTMLDivElement>
}

const SelectContext = createContext<SelectContextType | null>(null)

function useSelectContext() {
  const context = useContext(SelectContext)
  if (!context) {
    throw new Error('Select components must be used within Select')
  }
  return context
}

interface SelectProps {
  value: string
  onValueChange: (value: string) => void
  children: ReactNode
  className?: string
}

export function Select({ value, onValueChange, children, className }: SelectProps) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node) &&
          contentRef.current && !contentRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <SelectContext.Provider value={{ value, onValueChange, open, setOpen, triggerRef, contentRef }}>
      <div className={cn('relative w-full', className)}>{children}</div>
    </SelectContext.Provider>
  )
}

interface SelectTriggerProps {
  children?: ReactNode
  className?: string
  placeholder?: string
}

export function SelectTrigger({ children, className, placeholder }: SelectTriggerProps) {
  const { value, open, setOpen, triggerRef } = useSelectContext()

  return (
    <button
      ref={triggerRef}
      type="button"
      role="combobox"
      aria-expanded={open}
      aria-haspopup="listbox"
      onClick={() => setOpen(!open)}
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-xl border bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all disabled:opacity-50 disabled:pointer-events-none',
        'border-gray-200 dark:border-gray-600 dark:bg-gray-800',
        open && 'border-primary-500',
        className
      )}
    >
      <span className={cn('truncate', !value && 'text-gray-500')}>
        {value ? children : placeholder}
      </span>
      <ChevronDown className={cn('h-4 w-4 text-gray-500 transition-transform', open && 'rotate-180')} />
    </button>
  )
}

interface SelectValueProps {
  placeholder?: string
}

export function SelectValue({ placeholder }: SelectValueProps) {
  const { value } = useSelectContext()
  return <span className={cn('truncate', !value && 'text-gray-500')}>{value || placeholder}</span>
}

interface SelectContentProps {
  children: ReactNode
  className?: string
  position?: 'popper' | 'inline'
}

export function SelectContent({ children, className, position = 'popper' }: SelectContentProps) {
  const { open, contentRef } = useSelectContext()

  if (!open) return null

  return (
    <div
      ref={contentRef}
      role="listbox"
      className={cn(
        'relative z-50 max-h-96 w-full overflow-auto rounded-xl border bg-white py-2 text-sm shadow-xl dark:bg-gray-800',
        'border-gray-200 dark:border-gray-600',
        className
      )}
    >
      {children}
    </div>
  )
}

interface SelectItemProps {
  value: string
  children: ReactNode
  disabled?: boolean
  className?: string
}

export function SelectItem({ value, children, disabled, className }: SelectItemProps) {
  const { value: currentValue, onValueChange, setOpen } = useSelectContext()
  const isSelected = currentValue === value

  const handleClick = () => {
    if (!disabled) {
      onValueChange(value)
      setOpen(false)
    }
  }

  return (
    <div
      role="option"
      aria-selected={isSelected}
      aria-disabled={disabled}
      onClick={handleClick}
      className={cn(
        'relative flex cursor-default select-none items-center rounded-sm px-3 py-2 outline-none transition-colors',
        'focus:bg-primary-100 focus:text-primary-900 dark:focus:bg-primary-900 dark:focus:text-primary-100',
        disabled ? 'opacity-50 pointer-events-none' : '',
        isSelected && 'bg-primary-50 text-primary-900 dark:bg-primary-900/30 dark:text-primary-100',
        className
      )}
    >
      {isSelected && <Check className="absolute left-2 h-4 w-4 text-primary-500" />}
      <span className={cn('pl-8', isSelected ? 'pr-8' : '')}>{children}</span>
    </div>
  )
}

// Re-export the simple Select from Input for backward compatibility
export { Select as SimpleSelect } from './Input'