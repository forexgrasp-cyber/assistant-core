import { createContext, useContext, useState, ReactNode, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

interface DialogContextType {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const DialogContext = createContext<DialogContextType | null>(null)

function useDialogContext() {
  const context = useContext(DialogContext)
  if (!context) {
    throw new Error('Dialog components must be used within Dialog')
  }
  return context
}

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  return (
    <DialogContext.Provider value={{ open, onOpenChange }}>
      {open && <DialogOverlay onClose={() => onOpenChange(false)} />}
      {open && <DialogContent>{children}</DialogContent>}
    </DialogContext.Provider>
  )
}

function DialogOverlay({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 bg-black/50 z-50"
      onClick={onClose}
      aria-hidden="true"
    />
  )
}

interface DialogContentProps {
  children: ReactNode
  className?: string
}

export function DialogContent({ children, className }: DialogContentProps) {
  const { onOpenChange } = useDialogContext()

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false)
    }
    document.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [onOpenChange])

  return (
    <div
      className={cn(
        'fixed left-1/2 top-1/2 z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800',
        className
      )}
      role="dialog"
      aria-modal="true"
    >
      {children}
    </div>
  )
}

interface DialogHeaderProps {
  children: ReactNode
  className?: string
}

export function DialogHeader({ children, className }: DialogHeaderProps) {
  return <div className={cn('mb-4', className)}>{children}</div>
}

interface DialogTitleProps {
  children: ReactNode
  className?: string
}

export function DialogTitle({ children, className }: DialogTitleProps) {
  return <h2 className={cn('text-lg font-semibold text-gray-900 dark:text-white', className)}>{children}</h2>
}

interface DialogDescriptionProps {
  children: ReactNode
  className?: string
}

export function DialogDescription({ children, className }: DialogDescriptionProps) {
  return <p className={cn('text-sm text-gray-500 dark:text-gray-400 mt-1', className)}>{children}</p>
}

interface DialogFooterProps {
  children: ReactNode
  className?: string
}

export function DialogFooter({ children, className }: DialogFooterProps) {
  return <div className={cn('flex items-center justify-end gap-2 mt-4', className)}>{children}</div>
}

interface DialogCloseProps {
  className?: string
}

export function DialogClose({ className }: DialogCloseProps) {
  const { onOpenChange } = useDialogContext()
  return (
    <button
      onClick={() => onOpenChange(false)}
      className={cn('absolute right-4 top-4 rounded-sm opacity-70 ring-offset-white transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-800', className)}
      aria-label="Close"
    >
      <X className="h-4 w-4" />
    </button>
  )
}