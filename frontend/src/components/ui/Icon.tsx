import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface IconProps {
  icon: LucideIcon
  size?: number
  className?: string
}

export function Icon({ icon: Icon, size = 16, className }: IconProps) {
  return <Icon size={size} className={cn(className)} />
}