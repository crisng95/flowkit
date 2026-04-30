import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
    'inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold transition-colors focus:outline-none focus:ring-1 focus:ring-[hsl(var(--ring))]',
    {
        variants: {
            variant: {
                default: 'border-transparent bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]',
                secondary: 'border-transparent bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))]',
                destructive: 'border-transparent bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))]',
                outline: 'text-[hsl(var(--foreground))]',
                success: 'border-transparent bg-green-100 text-green-700',
                warning: 'border-transparent bg-amber-100 text-amber-700',
            },
        },
        defaultVariants: { variant: 'default' },
    }
)

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
