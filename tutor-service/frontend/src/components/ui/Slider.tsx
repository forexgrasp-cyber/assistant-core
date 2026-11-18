import { cn } from '@/lib/utils'

interface SliderProps extends React.InputHTMLAttributes<HTMLInputElement> {
  value: number[]
  onValueChange: (value: number[]) => void
  max?: number
  min?: number
  step?: number
}

export function Slider({ className, value, onValueChange, max = 100, min = 0, step = 1, ...props }: SliderProps) {
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value[0]}
      onChange={(e) => onValueChange([parseFloat(e.target.value)])}
      className={cn(
        'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500',
        className
      )}
      {...props}
    />
  )
}